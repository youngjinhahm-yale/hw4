"""Campus Customs API (run from this folder: uvicorn main:app --reload --port 8000).

- Products: catalogue, per-size stock, and product images from data/campus_customs.db
- Auth: create account / log in / log out (auth.py)
- Chat: the PydanticAI shop agent (agent.py + tools.py + models.py + prompts/prompt.md)
- Memory: saved chat history, customer and page context for the agent (memory.py)
- Audit: every agent run is appended to output/audit_trail.json (audit.py)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import Cookie, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import auth
from audit import RunRecorder, append_entry
from agent import AgentUnavailable, StatusCallback, run_chat
from db import IMAGES_DIR, connect, init_db
from memory import (
    clear_history,
    customer_from_user,
    history_for_agent,
    load_history,
    page_context,
    save_turn,
)
from models import (
    ChatRequest,
    ChatResponse,
    ChatResults,
    HistoryMessage,
    ProductCard,
    ProductDetail,
    ShopDeps,
)
from tools import PRODUCT_SELECT, SIZE_ORDER, _card, _stock_by_product, cards_for_ids, get_product_details

log = logging.getLogger("campus_customs")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Campus Customs API", lifespan=lifespan)
app.include_router(auth.router)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI's default 422 echoes the submitted values back, which would
    # include a plain-text password. Return only the field and the reason.
    detail = [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": detail})


# Only the image folder is public; the database file itself is never served.
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/products")
def list_products(q: str | None = None, size: str | None = None) -> list[ProductCard]:
    """All products, optionally filtered by keyword and by "in stock in this size"."""
    sql = PRODUCT_SELECT
    params: list[str] = []
    if q:
        sql += """
            WHERE c.name LIKE ? OR c.garment_type LIKE ?
               OR c.description LIKE ? OR c.search_tags LIKE ? OR c.colors LIKE ?
        """
        params = [f"%{q}%"] * 5
    sql += " GROUP BY c.product_id ORDER BY c.name"
    size = size.upper() if size and size.upper() in SIZE_ORDER else None
    with connect() as conn:
        stock = _stock_by_product(conn)
        cards = [_card(r, stock.get(r["product_id"])) for r in conn.execute(sql, params)]
    return [c for c in cards if not size or c.stock.get(size, 0) > 0]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> ProductDetail:
    """One product with its full text and stock for every size."""
    detail = get_product_details(product_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return detail


# Chat rate limit: protects cost and blocks scripted abuse of the agent.
CHAT_LIMIT = 20  # messages
CHAT_WINDOW_SECONDS = 60
_chat_hits: dict[str, deque[float]] = defaultdict(deque)


def _rate_limited(key: str) -> bool:
    hits, now = _chat_hits[key], time.monotonic()
    while hits and hits[0] < now - CHAT_WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= CHAT_LIMIT:
        return True
    hits.append(now)
    return False


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def answer_chat(
    req: ChatRequest,
    cc_session: str | None,
    client_ip: str,
    on_status: StatusCallback | None = None,
) -> ChatResponse:
    """One chat turn, shared by /api/chat and /api/chat/stream.

    Logged in: identity comes from the session cookie, earlier turns come from
    chat_messages, and the new turn is saved. Guest: the widget's in-memory history
    is used and nothing is stored.
    """
    customer = customer_from_user(auth.user_from_token(cc_session))
    key = f"user:{customer.user_id}" if customer else f"ip:{client_ip}"
    if _rate_limited(key):
        rec = RunRecorder(message=req.message, user_id=customer.user_id if customer else None,
                          page=req.page.path if req.page else None, model="-")
        await asyncio.to_thread(append_entry, rec.finish("rate_limited"))
        raise HTTPException(
            status_code=429,
            detail="Whoa, that's a lot of questions at once! Please wait a minute and try again. 🐾",
        )
    deps = ShopDeps(customer=customer, page=page_context(req.page))
    history = history_for_agent(customer.user_id) if customer else req.history
    try:
        output = await run_chat(req.message, history, deps, on_status)
    except AgentUnavailable as exc:
        log.error("Chat agent failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Our chat assistant is taking a quick break. Please try again in a moment.",
        )
    # API contract: the agent returns product ids; the cards the page renders are
    # rebuilt from the database here, so a card can't show a made-up product,
    # price, or stock number. Unknown ids are dropped.
    results = None
    if output.matches:
        cards = cards_for_ids(output.matches.product_ids)
        if cards:
            results = ChatResults(title=output.matches.title, products=cards)
    if customer:
        save_turn(customer.user_id, req.message, output.reply, output.matches if results else None)
    return ChatResponse(reply=output.reply, results=results, saved=customer is not None)


@app.post("/api/chat")
async def chat(
    req: ChatRequest, request: Request, cc_session: str | None = Cookie(default=None)
) -> ChatResponse:
    """Send one shopper message to the agent and return its reply (single JSON response)."""
    return await answer_chat(req, cc_session, _client_ip(request))


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, request: Request, cc_session: str | None = Cookie(default=None)):
    """Same as /api/chat, but streams progress as newline-delimited JSON:

    {"type": "status", "text": "📦 Checking stock for size M…"}   (0+ times, one per tool call)
    {"type": "done", "response": <ChatResponse>}                 (or {"type": "error", "detail": ...})
    """
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def on_status(text: str) -> None:
        await queue.put({"type": "status", "text": text})

    async def worker() -> None:
        try:
            response = await answer_chat(req, cc_session, _client_ip(request), on_status)
            await queue.put({"type": "done", "response": response.model_dump()})
        except HTTPException as exc:
            await queue.put({"type": "error", "status": exc.status_code, "detail": exc.detail})
        except Exception:  # never leak internals to the browser
            log.exception("Streaming chat failed")
            await queue.put({"type": "error", "status": 500, "detail": "Something went wrong. Please try again."})
        finally:
            await queue.put(None)

    async def events():
        task = asyncio.create_task(worker())
        try:
            while (item := await queue.get()) is not None:
                yield json.dumps(item, ensure_ascii=False) + "\n"
        finally:
            await task

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _require_customer(cc_session: str | None):
    customer = customer_from_user(auth.user_from_token(cc_session))
    if customer is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Log in to see saved chat history.")
    return customer


@app.get("/api/chat/history")
def chat_history(cc_session: str | None = Cookie(default=None)) -> list[HistoryMessage]:
    """The logged-in shopper's saved conversation (most recent 50 messages, oldest first)."""
    return load_history(_require_customer(cc_session).user_id)


@app.delete("/api/chat/history", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_history(cc_session: str | None = Cookie(default=None)) -> None:
    """Let a shopper wipe their own saved chat."""
    clear_history(_require_customer(cc_session).user_id)
