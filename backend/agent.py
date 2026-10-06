"""Campus Customs shop agent: PydanticAI + an OpenAI model through Portkey.

The system prompt lives in prompts/prompt.md and is re-read on every run, so
prompt edits take effect without restarting the server. Tools come from
tools.py; the structured reply type (ShopReply) comes from models.py. An output
validator rejects replies that quote a price or stock count no tool returned.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from collections.abc import AsyncIterable, Awaitable, Callable
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai import Agent, ModelRetry, RunContext  # noqa: E402
from pydantic_ai.exceptions import (  # noqa: E402
    ContentFilterError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.messages import (  # noqa: E402
    AgentStreamEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_core import to_json  # noqa: E402
from pydantic_ai.models.openai import OpenAIResponsesModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402

from audit import RunRecorder, append_entry  # noqa: E402
from models import ChatTurn, ShopDeps, ShopReply  # noqa: E402
from tools import AGENT_TOOLS  # noqa: E402

HERE = Path(__file__).resolve().parent
HW4_DIR = HERE.parent
# The key can live in hw4/.env or the course folder's .env (never committed).
load_dotenv(HW4_DIR / ".env")
load_dotenv(HW4_DIR.parent / ".env")

PROMPT_PATH = HERE / "prompts" / "prompt.md"
# OpenAI 5.6-series model via Portkey; override with MODEL_NAME (e.g. gpt-6-astra).
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")
# A normal turn is search -> details/stock -> answer; this caps runaway tool loops.
USAGE_LIMITS = UsageLimits(request_limit=8)


class AgentUnavailable(RuntimeError):
    """The model can't be reached (missing key, network, provider error)."""


@lru_cache(maxsize=1)
def get_agent() -> Agent[ShopDeps, ShopReply]:
    """Build the agent once, on the first chat request."""
    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise AgentUnavailable("PORTKEY_API_KEY is not set (put it in a .env file).")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={
            "x-portkey-api-key": api_key,
            # Never answer from Portkey's cache: stock is live, and cached responses carry
            # "portkey_cache_*" item ids that Azure rejects on the next step of a tool loop.
            "x-portkey-cache-force-refresh": "true",
        },
    )
    model = OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
    agent = Agent(
        model,
        deps_type=ShopDeps,
        output_type=ShopReply,
        tools=AGENT_TOOLS,
        retries=2,
    )

    @agent.instructions
    def system_prompt(ctx: RunContext[ShopDeps]) -> str:
        return "\n\n".join(
            [
                PROMPT_PATH.read_text(encoding="utf-8"),
                shopper_context(ctx.deps),
                page_context_text(ctx.deps),
            ]
        )

    @agent.output_validator
    def facts_come_from_database(ctx: RunContext[ShopDeps], output: ShopReply) -> ShopReply:
        """Reject a reply whose prices, stock counts, or product ids no tool returned,
        or that leaks internal plumbing (JSON/validation/tool errors) to the shopper."""
        if INTERNAL_LEAK_RE.search(output.reply):
            raise ModelRetry(
                "Your reply talks about internal errors or data formats. The shopper never "
                "sees those. Reply only to the shopper's original message: "
                f"{str(ctx.prompt)[:300]!r}"
            )
        unverified = unverified_numbers(output.reply, ctx.messages)
        if unverified:
            raise ModelRetry(
                f"Your reply mentions {', '.join(unverified)}, but no tool result in this "
                "turn contains that number. Call get_product_info / check_stock and use the "
                "exact price_usd and quantity values, or remove the number."
            )
        if output.matches:
            unseen = unseen_product_ids(output.matches.product_ids, ctx.messages)
            if unseen:
                raise ModelRetry(
                    f"matches.product_ids contains ids no tool returned this turn: {unseen}. "
                    "Call search_products this turn and copy product_id values exactly."
                )
        return output

    return agent


def shopper_context(deps: ShopDeps) -> str:
    """Who is chatting, appended to the system prompt on every run (from ShopDeps)."""
    c = deps.customer
    if c is None:
        return (
            "## This shopper\n\nA guest (not logged in). You don't know their name or email. "
            "Their chat is not saved; mention that logging in saves chat history only if "
            "they ask about it."
        )
    return (
        "## This shopper (logged in)\n\n"
        f"- Name: {c.first_name} {c.last_name}\n"
        f"- Email: {c.email}\n"
        f"- Member since: {c.member_since[:10]}\n"
        "- Their chat history is saved, and earlier messages from past visits may appear "
        "above. Welcome them back by first name when it fits.\n"
        "Only share these details with this shopper. You have no access to other "
        "customers, to orders, or to passwords."
    )


def page_context_text(deps: ShopDeps) -> str:
    """Where the shopper is on the site right now (from ShopDeps.page)."""
    p = deps.page
    if p is None:
        return "## Current page\n\nUnknown."
    lines = [f"## Current page\n\n- Path: {p.path} ({p.page_type} page)"]
    if p.product:
        lines.append(
            f'- The shopper is viewing **{p.product.name}** (product_id "{p.product.product_id}").'
            ' When they say "this", "it", or "this one" without naming another product, they '
            "mean this item. Call get_product_info / check_stock with this product_id. Don't "
            "search for it by name."
        )
    elif p.page_type == "product":
        lines.append("- A product page for an id that isn't in the catalogue.")
    if p.search_query:
        lines.append(f'- Products page search box: "{p.search_query}"')
    if p.category:
        lines.append(f"- Products page category filter: {p.category}")
    if p.size_filter:
        lines.append(
            f"- Products page 'in stock in size' filter: {p.size_filter} (the shopper likely "
            f"wears {p.size_filter}; use it as size_in_stock unless they say otherwise)"
        )
    return "\n".join(lines)


# Words a shop reply should never contain: they mean the model is answering an internal
# retry/validation message instead of the shopper.
INTERNAL_LEAK_RE = re.compile(
    r"\b(json|payload|schema|validation error|tool call|property names|markdown fences|"
    r"final_result|ModelRetry)\b",
    re.I,
)

# "$68", "$58.00"
PRICE_RE = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")
# "only 2 left", "25 in stock", "(15 left)", "8 available", "3 units"
QTY_RE = re.compile(r"\b(\d+)\s+(?:left|in stock|available|remaining|units?)\b", re.I)
NUMBER_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)")


def _tool_results_text(messages: list[ModelMessage]) -> str:
    return " ".join(
        to_json(part.content).decode()
        for msg in messages
        for part in msg.parts
        if isinstance(part, ToolReturnPart)
    )


def unseen_product_ids(product_ids: list[str], messages: list[ModelMessage]) -> list[str]:
    """Ids the model put in matches that didn't appear in any tool result this turn."""
    seen = _tool_results_text(messages)
    return [pid for pid in product_ids if f'"product_id":"{pid}"' not in seen]


def unverified_numbers(reply: str, messages: list[ModelMessage]) -> list[str]:
    """Prices/quantities in the reply that don't appear in a tool result or the shopper's words.

    Numbers from earlier assistant replies don't count, so follow-up questions
    ("how much is it?") force a fresh database lookup instead of trusting old text.
    """
    known: set[float] = set()
    for msg in messages:
        for part in msg.parts:
            if isinstance(part, ToolReturnPart):
                text = to_json(part.content).decode()
            elif isinstance(part, UserPromptPart) and isinstance(part.content, str):
                text = part.content
            else:
                continue
            known.update(float(n) for n in NUMBER_RE.findall(text))
    claims = [f"${p}" for p in PRICE_RE.findall(reply) if float(p) not in known]
    claims += [f"'{q} …'" for q in QTY_RE.findall(reply) if float(q) not in known]
    return claims


def to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    """Turn the widget's recent turns into PydanticAI messages (text only)."""
    messages: list[ModelMessage] = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


BLOCKED_REPLY = ShopReply(
    reply=(
        "Sorry, I can't help with that one. I'm here for Campus Customs gear: "
        "sizes, prices, stock, and store policies. What can I help you find? 💙"
    )
)


def _is_content_filter(exc: ModelHTTPError) -> bool:
    """Azure/OpenAI safety filters reject jailbreak-style prompts with code content_filter."""
    return "content_filter" in str(exc.body) or "content management policy" in str(exc.body)


StatusCallback = Callable[[str], Awaitable[None]]


def _pretty_id(product_id: str) -> str:
    return product_id.replace("-", " ").title()


def tool_status(tool_name: str, args: dict) -> str | None:
    """Shopper-friendly progress line for a tool call (None = don't show anything)."""
    if tool_name == "search_products":
        what = " ".join(
            str(args[k]) for k in ("color", "garment_type", "query") if args.get(k)
        )
        extra = f" in size {args['size_in_stock']}" if args.get("size_in_stock") else ""
        return f"🔎 Searching the catalogue{f' for {what}' if what else ''}{extra}…"
    if tool_name == "get_product_info":
        return f"📖 Reading details for {_pretty_id(args.get('product_id', 'the item'))}…"
    if tool_name == "check_stock":
        size = args.get("size")
        return f"📦 Checking stock for size {size}…" if size else "📦 Checking stock in every size…"
    if tool_name == "find_similar_products":
        size = args.get("size")
        return f"🧭 Finding similar items in stock{f' in {size}' if size else ''}…"
    return None  # e.g. the final_result output tool


async def run_chat(
    message: str,
    history: list[ChatTurn],
    deps: ShopDeps,
    on_status: StatusCallback | None = None,
) -> ShopReply:
    """Run one chat turn.

    Every tool call/result is recorded and the run is appended to
    output/audit_trail.json with its stop reason, whether it succeeds or fails.
    If on_status is given, each tool call is also reported live (streaming chat).
    """
    agent = get_agent()
    recorder = RunRecorder(
        message=message,
        user_id=deps.customer.user_id if deps.customer else None,
        page=deps.page.path if deps.page else None,
        model=MODEL_NAME,
    )

    async def watch_loop(_ctx: RunContext[ShopDeps], events: AsyncIterable[AgentStreamEvent]):
        async for event in events:
            if isinstance(event, FunctionToolCallEvent):
                args = event.part.args_as_dict()
                recorder.tool_call(event.part.tool_name, args)
                if on_status and (text := tool_status(event.part.tool_name, args)):
                    await on_status(text)
            elif isinstance(event, FunctionToolResultEvent):
                part = event.part
                recorder.tool_result(part.tool_name, part.content, retry=isinstance(part, RetryPromptPart))

    async def log(stop_reason: str, **kw) -> None:
        # Auditing must never break a shopper's chat: log the failure and move on.
        try:
            await asyncio.to_thread(append_entry, recorder.finish(stop_reason, **kw))
        except Exception:
            logging.getLogger("campus_customs").exception("Could not write audit entry")

    try:
        result = await agent.run(
            message,
            deps=deps,
            message_history=to_message_history(history),
            usage_limits=USAGE_LIMITS,
            event_stream_handler=watch_loop,
        )
    except ModelHTTPError as exc:
        if _is_content_filter(exc):
            await log("content_filter", reply=BLOCKED_REPLY.reply)
            return BLOCKED_REPLY  # a refusal, not an outage
        await log("provider_error", error=str(exc))
        raise AgentUnavailable(str(exc)) from exc
    except ContentFilterError:  # the provider's safety filter blocked the prompt/response
        await log("content_filter", reply=BLOCKED_REPLY.reply)
        return BLOCKED_REPLY
    except UsageLimitExceeded as exc:
        await log("usage_limit_exceeded", error=str(exc))
        raise AgentUnavailable(str(exc)) from exc
    except UnexpectedModelBehavior as exc:  # e.g. output validator retries exhausted
        await log("output_validation_failed", error=str(exc))
        raise AgentUnavailable(str(exc)) from exc
    except Exception as exc:  # network and anything else
        await log("error", error=f"{type(exc).__name__}: {exc}")
        raise AgentUnavailable(str(exc)) from exc

    # Validator/format retries the model needed before a valid final answer.
    output_retries = sum(
        isinstance(part, RetryPromptPart) and part.tool_name not in {s["tool"] for s in recorder.entry["steps"]}
        for msg in result.new_messages()
        for part in msg.parts
    )
    await log(
        "final_result",
        reply=result.output.reply,
        matches=result.output.matches,
        usage=result.usage() if callable(result.usage) else result.usage,
        output_retries=output_retries,
    )
    return result.output
