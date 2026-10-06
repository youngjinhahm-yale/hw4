"""Customer memory: who is chatting, where they are, and what they said before.

- Chat history for logged-in shoppers lives in the chat_messages table.
- CustomerInfo comes from the session cookie (auth.user_from_token), never the request.
- PageContext is built from the browser's current URL and checked against the catalogue.
"""

from __future__ import annotations

import json
import re
from urllib.parse import parse_qs

from db import connect
from models import (
    ChatResults,
    ChatTurn,
    CustomerInfo,
    HistoryMessage,
    PageContext,
    PageInfo,
    PageProduct,
    ProductMatches,
)
from tools import SIZE_ORDER, cards_for_ids

HISTORY_FOR_AGENT = 20  # most recent messages sent to the model as context
HISTORY_FOR_WIDGET = 50  # most recent messages shown when the shopper returns


# ---------- Who is chatting ----------


def customer_from_user(user: dict | None) -> CustomerInfo | None:
    """auth.public_user() dict -> the fields the agent may see (no hash, no token)."""
    if not user:
        return None
    return CustomerInfo(
        user_id=user["id"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        email=user["email"],
        member_since=user["created_at"],
    )


# ---------- Where they are ----------

PRODUCT_PATH = re.compile(r"^/products/([^/?#]+)/?$")
PAGE_TYPES = {"/": "home", "/products": "products", "/about": "about", "/login": "login", "/signup": "signup"}


def page_context(page: PageInfo | None) -> PageContext | None:
    """Turn the browser's URL into trusted page context for the agent."""
    if page is None:
        return None
    path = page.path.split("?")[0] or "/"
    params = parse_qs(page.search.lstrip("?"))
    m = PRODUCT_PATH.match(path)
    if m:
        # Only a real catalogue id becomes "the product they're looking at".
        with connect() as conn:
            row = conn.execute(
                "SELECT product_id, name FROM catalogue WHERE product_id = ?", [m.group(1)]
            ).fetchone()
        product = PageProduct(product_id=row["product_id"], name=row["name"]) if row else None
        return PageContext(path=path, page_type="product", product=product)
    page_type = PAGE_TYPES.get(path.rstrip("/") or "/", "other")
    on_products = page_type == "products"
    size = ((params.get("size") or [""])[0] or "").upper()
    return PageContext(
        path=path,
        page_type=page_type,  # type: ignore[arg-type]
        search_query=(params.get("q") or [None])[0] if on_products else None,
        category=(params.get("category") or [None])[0] if on_products else None,
        size_filter=size if on_products and size in SIZE_ORDER else None,  # type: ignore[arg-type]
    )


# ---------- What they said before (chat_messages) ----------


def _results_from_json(products_json: str | None) -> ChatResults | None:
    """Rebuild saved cards from the live catalogue (fresh prices/stock).

    Accepts our format {"title", "product_ids"} and the seed data's list of product dicts.
    """
    if not products_json:
        return None
    try:
        data = json.loads(products_json)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        title, ids = data.get("title") or "Products from chat", data.get("product_ids") or []
    elif isinstance(data, list):
        title, ids = "Products from chat", [d.get("product_id") for d in data if isinstance(d, dict)]
    else:
        return None
    cards = cards_for_ids([i for i in ids if isinstance(i, str)])
    return ChatResults(title=title, products=cards) if cards else None


def load_history(user_id: int, limit: int = HISTORY_FOR_WIDGET) -> list[HistoryMessage]:
    """The shopper's most recent messages, oldest first."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content, products_json, created_at FROM (
                SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?
            ) ORDER BY id
            """,
            [user_id, limit],
        ).fetchall()
    return [
        HistoryMessage(
            role=r["role"],
            content=r["content"],
            results=_results_from_json(r["products_json"]) if r["role"] == "assistant" else None,
            created_at=r["created_at"],
        )
        for r in rows
        if r["role"] in ("user", "assistant")
    ]


def history_for_agent(user_id: int) -> list[ChatTurn]:
    """Recent turns as plain text for the model (cards are not replayed)."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM (
                SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?
            ) ORDER BY id
            """,
            [user_id, HISTORY_FOR_AGENT],
        ).fetchall()
    return [
        ChatTurn(role=r["role"], content=r["content"][:4000])
        for r in rows
        if r["role"] in ("user", "assistant")
    ]


def save_turn(user_id: int, message: str, reply: str, matches: ProductMatches | None) -> None:
    """Store the shopper's message and the assistant's reply together (one transaction)."""
    products_json = (
        json.dumps({"title": matches.title, "product_ids": matches.product_ids})
        if matches
        else None
    )
    with connect(readonly=False) as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)",
            [user_id, message],
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) "
            "VALUES (?, 'assistant', ?, ?)",
            [user_id, reply, products_json],
        )


def clear_history(user_id: int) -> int:
    with connect(readonly=False) as conn:
        return conn.execute("DELETE FROM chat_messages WHERE user_id = ?", [user_id]).rowcount
