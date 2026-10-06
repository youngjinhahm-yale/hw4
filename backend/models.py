"""Pydantic / PydanticAI types shared by the API, the tools, and the agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

Size = Literal["XS", "S", "M", "L", "XL", "XXL"]


# ---------- Catalogue ----------


class ProductCard(BaseModel):
    """What a product card needs. Prices and stock always come from the database."""

    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    price: float = Field(description="Price in USD from the catalogue table")
    image_url: str
    total_stock: int = Field(description="Units in stock across all sizes")
    stock: dict[str, int] = Field(
        default_factory=dict, description="Units per size, XS-XXL order (for stock badges)"
    )


StockStatus = Literal["in stock", "low stock", "sold out"]
LOW_STOCK_THRESHOLD = 5  # 1-5 units left -> "low stock" ("only N left")


def stock_status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "sold out"
    return "low stock" if quantity <= LOW_STOCK_THRESHOLD else "in stock"


class SizeStock(BaseModel):
    size: Size
    quantity: int = Field(ge=0, description="Units on hand from the inventory table")
    status: StockStatus = Field(description="Derived from quantity: 0 = sold out, 1-5 = low stock")


class ProductDetail(ProductCard):
    """Everything the product page shows (API only; the agent uses the leaner types below)."""

    search_tags: list[str]
    sizes: list[SizeStock]


# ---------- Agent tool results ----------


class ProductMatch(BaseModel):
    """One search hit: enough to pick a product, without the long description."""

    product_id: str = Field(description="Exact id to pass to the other tools and to product_ids")
    name: str
    garment_type: str
    colors: list[str]
    price_usd: float
    in_stock: bool = Field(description="True if at least one size has units")
    sizes_in_stock: list[Size]


class SearchResults(BaseModel):
    query_summary: str = Field(description="The filters that were applied, for transparency")
    match_count: int
    matches: list[ProductMatch]


class ProductInfo(BaseModel):
    """get_product_info: what the item is and what it costs (catalogue table)."""

    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    price_usd: float = Field(description="Exact catalogue price; quote this, never estimate")
    sizes_offered: list[Size]


class StockReport(BaseModel):
    """check_stock: units per size (inventory table), plus the requested size if any."""

    product_id: str
    name: str
    price_usd: float
    requested_size: Size | None = Field(description="The size the shopper asked about, if any")
    requested_quantity: int | None = Field(description="Units in requested_size (0 = sold out)")
    requested_status: StockStatus | None
    sizes: list[SizeStock] = Field(description="Every size, in XS-XXL order")
    sold_out_sizes: list[Size]
    in_stock_sizes: list[Size]
    total_units: int


class SimilarItem(BaseModel):
    product_id: str
    name: str
    garment_type: str
    colors: list[str]
    price_usd: float
    sizes_in_stock: list[Size]
    reason: str = Field(description="Why it was picked, e.g. 'same category, shares tags: Branford'")


class SimilarProducts(BaseModel):
    """find_similar_products: in-stock alternatives ranked by code, not guessed by the model."""

    based_on: str = Field(description="Name of the product the suggestions are similar to")
    size_filter: Size | None = Field(description="Every result is in stock in this size, if set")
    items: list[SimilarItem]


class ToolError(BaseModel):
    """Returned instead of raising, so the agent can recover (e.g. search again)."""

    error: str
    did_you_mean: list[ProductMatch] = Field(default_factory=list)


# ---------- Agent ----------


class CustomerInfo(BaseModel):
    """Who is chatting. Built server-side from the session cookie, never from the request body."""

    user_id: int
    first_name: str
    last_name: str
    email: str
    member_since: str = Field(description="users.created_at (UTC)")


class PageProduct(BaseModel):
    product_id: str
    name: str


class PageContext(BaseModel):
    """Where the shopper is on the site when they send a message."""

    path: str = Field(description='Current URL path, e.g. "/products/basic-hoodie-big-yale"')
    page_type: Literal["home", "products", "product", "about", "login", "signup", "other"]
    product: PageProduct | None = Field(
        default=None, description="The product being viewed (verified against the catalogue)"
    )
    search_query: str | None = Field(default=None, description="?q= on the Products page")
    category: str | None = Field(default=None, description="?category= on the Products page")
    size_filter: Size | None = Field(default=None, description='?size= ("in stock in size") on the Products page')


@dataclass
class ShopDeps:
    """Per-request context handed to the agent: who is chatting and where they are.

    Never contains secrets (no password hash, no session token).
    """

    customer: CustomerInfo | None = None  # None = guest
    page: PageContext | None = None


MAX_PAGE_RESULTS = 30


class ProductMatches(BaseModel):
    """The products the website should show as cards on the page for this turn."""

    title: str = Field(
        max_length=60,
        description='Short heading for the results, e.g. "Hoodies", "Navy crewnecks in M".',
    )
    product_ids: list[str] = Field(
        min_length=1,
        max_length=MAX_PAGE_RESULTS,
        description=(
            "product_id values copied exactly from this turn's tool results, most "
            "relevant first. Include every match you'd want the shopper to browse."
        ),
    )


class ShopReply(BaseModel):
    """Structured output the agent must return for every chat turn."""

    reply: str = Field(
        description=(
            "Friendly answer for the shopper in Campus Customs voice. Every price, "
            "size, and stock number must come from a tool result in this turn."
        )
    )
    matches: ProductMatches | None = Field(
        default=None,
        description=(
            "Products to show on the website as cards. Set whenever the reply is about "
            "specific products; null for small talk, policies, or when nothing matched."
        ),
    )


# ---------- Chat API ----------


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class PageInfo(BaseModel):
    """Raw page info the browser sends; the server checks it before the agent sees it."""

    path: str = Field(default="/", max_length=300)
    search: str = Field(default="", max_length=300, description="location.search, e.g. ?q=navy")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    # Only used for guests; logged-in history is loaded from chat_messages instead.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    page: PageInfo | None = None


class ChatResults(BaseModel):
    """What the front end renders on the page: rebuilt from the database, not the model."""

    title: str
    products: list[ProductCard]


class ChatResponse(BaseModel):
    """API contract for POST /api/chat."""

    reply: str
    results: ChatResults | None = None
    saved: bool = Field(default=False, description="True if this turn was saved to chat history")


class HistoryMessage(BaseModel):
    """One saved message, as GET /api/chat/history returns it."""

    role: Literal["user", "assistant"]
    content: str
    results: ChatResults | None = None
    created_at: str
