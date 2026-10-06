"""Append-only audit trail of agent-loop activity: output/audit_trail.json.

One entry per chat turn: when it ran, who (user id or guest, never an email),
which page, every tool call with short args/results, validator retries, token
usage, and why the loop stopped. Existing entries are never removed or edited;
new entries are appended and the file is replaced atomically.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_core import to_json

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
PREVIEW_CHARS = 200  # cap for args/results/replies in the log
MESSAGE_CHARS = 160

_lock = threading.Lock()

# Privacy: never write emails, card-like numbers, or phone numbers to the log.
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONG_NUMBER = re.compile(r"\b\d(?:[ -]?\d){11,18}\b")
_PHONE = re.compile(r"\(?\b\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}\b")


def redact(text: str) -> str:
    text = _EMAIL.sub("[email]", text)
    text = _LONG_NUMBER.sub("[number]", text)
    return _PHONE.sub("[phone]", text)


def short(value: Any, limit: int = PREVIEW_CHARS) -> str:
    """Compact, redacted, length-capped preview of any value."""
    text = value if isinstance(value, str) else to_json(value).decode("utf-8", "replace")
    text = redact(" ".join(text.split()))
    return text if len(text) <= limit else text[: limit - 1] + "…"


class RunRecorder:
    """Collects one agent run's activity, then appends it to the audit trail."""

    def __init__(self, *, message: str, user_id: int | None, page: str | None, model: str):
        self.started = time.monotonic()
        self.entry: dict[str, Any] = {
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "run_id": uuid.uuid4().hex[:12],
            "model": model,
            "user": f"user:{user_id}" if user_id else "guest",
            "page": page,
            "message": short(message, MESSAGE_CHARS),
            "steps": [],
        }

    def _ms(self) -> int:
        return int((time.monotonic() - self.started) * 1000)

    def tool_call(self, tool: str, args: dict) -> None:
        self.entry["steps"].append({"t_ms": self._ms(), "tool": tool, "args": short(args), "result": None})

    def tool_result(self, tool: str, content: Any, retry: bool = False) -> None:
        # Attach to the most recent call of this tool that has no result yet.
        for step in reversed(self.entry["steps"]):
            if step["tool"] == tool and step["result"] is None:
                step["result"] = ("RETRY: " if retry else "") + short(content)
                return
        self.entry["steps"].append({"t_ms": self._ms(), "tool": tool, "args": None, "result": short(content)})

    def finish(
        self,
        stop_reason: str,
        *,
        reply: str | None = None,
        matches: Any = None,
        usage: Any = None,
        output_retries: int = 0,
        error: str | None = None,
    ) -> dict:
        self.entry.update(
            {
                "stop_reason": stop_reason,
                "duration_ms": self._ms(),
                "tool_calls": len([s for s in self.entry["steps"] if s["args"] is not None]),
                "output_retries": output_retries,
                "reply": short(reply) if reply else None,
                "matches": (
                    {"title": matches.title, "count": len(matches.product_ids)} if matches else None
                ),
            }
        )
        if usage is not None:
            self.entry["usage"] = {
                "requests": usage.requests,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
            }
        if error:
            self.entry["error"] = short(error)
        return self.entry


def append_entry(entry: dict) -> None:
    """Append one entry. Never truncates: a corrupt file is moved aside, not overwritten."""
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        entries: list = []
        if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size > 0:
            try:
                entries = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
                if not isinstance(entries, list):
                    raise ValueError("audit trail is not a JSON list")
            except ValueError:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                AUDIT_PATH.replace(AUDIT_PATH.with_name(f"audit_trail.corrupt-{stamp}.json"))
                entries = []
        entries.append(entry)
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, AUDIT_PATH)  # atomic: readers never see a half-written file
