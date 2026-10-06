"""Create-account / log-in / log-out for Campus Customs shoppers.

Passwords are never stored. Each user row keeps only a salted PBKDF2-HMAC-SHA256
hash. A login creates a random session token; the browser gets it in an
HttpOnly cookie and the database keeps only the token's SHA-256 hash.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from db import connect

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------- Password hashing ----------

# New hashes: pbkdf2_sha256$<iterations>$<salt>$<hex digest> (OWASP 2023 guidance).
PBKDF2_ITERATIONS = 600_000
# The seed users use the older pbkdf2_sha256$<salt>$<hex digest> form, which
# was made with 120,000 iterations; verify_password still accepts it.
LEGACY_ITERATIONS = 120_000


def _pbkdf2(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    ).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)  # unique random salt per user
    digest = _pbkdf2(password, salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if parts[0] != "pbkdf2_sha256":
        return False
    if len(parts) == 4:
        _, iterations, salt, digest = parts
        iterations = int(iterations)
    elif len(parts) == 3:
        _, salt, digest = parts
        iterations = LEGACY_ITERATIONS
    else:
        return False
    # Constant-time compare so response timing doesn't leak how close a guess was.
    return hmac.compare_digest(_pbkdf2(password, salt, iterations), digest)


# Checked when an email is unknown so "no such user" takes as long as "wrong password".
_DUMMY_HASH = hash_password(secrets.token_hex(16))

# ---------- Brute-force throttle ----------

MAX_FAILURES = 5
FAILURE_WINDOW_SECONDS = 15 * 60
_failures: dict[str, deque[float]] = defaultdict(deque)


def _recent_failures(email: str) -> deque[float]:
    q = _failures[email]
    cutoff = time.monotonic() - FAILURE_WINDOW_SECONDS
    while q and q[0] < cutoff:
        q.popleft()
    return q


# ---------- Sessions ----------

SESSION_COOKIE = "cc_session"
SESSION_DAYS = 7
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _start_session(conn: sqlite3.Connection, user_id: int, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) "
        "VALUES (?, ?, datetime('now', ?))",
        [_token_hash(token), user_id, f"+{SESSION_DAYS} days"],
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,  # page JavaScript (and injected scripts) can't read it
        samesite="lax",
        secure=COOKIE_SECURE,  # set COOKIE_SECURE=true when served over HTTPS
        path="/",
    )


def user_from_token(token: str | None) -> dict | None:
    """The logged-in user for a session cookie, or None. Never includes the hash."""
    if not token:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.first_name, u.last_name, u.name, u.email, u.created_at
            FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > datetime('now')
            """,
            [_token_hash(token)],
        ).fetchone()
    return public_user(row) if row else None


def public_user(row: sqlite3.Row) -> dict:
    first = row["first_name"] or row["name"].split(" ")[0]
    last = row["last_name"] or " ".join(row["name"].split(" ")[1:])
    return {
        "id": row["id"],
        "first_name": first,
        "last_name": last,
        "email": row["email"],
        "created_at": row["created_at"],
    }


# ---------- Request models ----------


class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


# ---------- Routes ----------


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, response: Response) -> dict:
    email = req.email.strip().lower()
    with connect(readonly=False) as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (name, first_name, last_name, email, password_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    f"{req.first_name} {req.last_name}",
                    req.first_name,
                    req.last_name,
                    email,
                    hash_password(req.password),
                ],
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "An account with that email already exists."
            )
        _start_session(conn, cur.lastrowid, response)
        row = conn.execute("SELECT * FROM users WHERE id = ?", [cur.lastrowid]).fetchone()
    return public_user(row)


@router.post("/login")
def login(req: LoginRequest, response: Response) -> dict:
    email = req.email.strip().lower()
    failures = _recent_failures(email)
    if len(failures) >= MAX_FAILURES:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many failed attempts. Please wait 15 minutes and try again.",
        )
    with connect(readonly=False) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE lower(email) = ?", [email]
        ).fetchone()
        ok = verify_password(req.password, row["password_hash"] if row else _DUMMY_HASH)
        if not (row and ok):
            failures.append(time.monotonic())
            # Same message either way, so attackers can't probe which emails exist.
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
        failures.clear()
        _start_session(conn, row["id"], response)
    return public_user(row)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, cc_session: str | None = Cookie(default=None)) -> None:
    if cc_session:
        with connect(readonly=False) as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", [_token_hash(cc_session)])
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me")
def me(cc_session: str | None = Cookie(default=None)) -> dict:
    user = user_from_token(cc_session)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in.")
    return user
