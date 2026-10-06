"""Tools the Campus Customs agent can call (also used by the product API routes).

Agent tools (AGENT_TOOLS):
  search_products   -> SearchResults  find candidate products
  get_product_info  -> ProductInfo    description, colors, price
  check_stock       -> StockReport    units per size, sold-out sizes

Every tool reads data/campus_customs.db through a read-only connection, so the
agent can look things up but can never change prices, stock, or accounts.
Lookups that fail return a ToolError (with suggestions) instead of raising, so
the agent can recover instead of guessing.
"""

from __future__ import annotations

import difflib
import json
import re
import sqlite3
from pathlib import Path

from db import connect
from models import (
    ProductCard,
    ProductDetail,
    ProductInfo,
    ProductMatch,
    SearchResults,
    SimilarItem,
    SimilarProducts,
    Size,
    SizeStock,
    StockReport,
    ToolError,
    stock_status,
)

SIZE_ORDER: list[Size] = ["XS", "S", "M", "L", "XL", "XXL"]

PRODUCT_SELECT = """
    SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock
    FROM catalogue c
    LEFT JOIN inventory i ON i.product_id = c.product_id
"""

# Shopper words -> words the catalogue actually uses.
SYNONYMS = {
    "hoodie": "hood",
    "hoody": "hood",
    "hooded": "hood",
    "sweater": "sweat",
    "sweatshirt": "sweat",
    "tee": "t-shirt",
    "tshirt": "t-shirt",
    "quarterzip": "quarter-zip",
    "1/4": "quarter-zip",
    "grey": "gray",
}
STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "of", "to", "do", "you",
    "have", "any", "some", "i", "me", "my", "want", "need", "looking", "show",
    "is", "are", "it", "this", "that", "yale", "merch", "something", "please",
}


# ---------- Shared helpers ----------


def image_url(image_file_path: str) -> str:
    # catalogue stores paths like "products/foo.jpg", relative to data/.
    return "/images/" + Path(image_file_path).name


def _card(row: sqlite3.Row, stock: dict[str, int] | None = None) -> ProductCard:
    stock = stock or {}
    return ProductCard(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        price=row["price"],
        image_url=image_url(row["image_file_path"]),
        total_stock=row["total_stock"],
        stock={s: stock[s] for s in SIZE_ORDER if s in stock},
    )


def _terms(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9/\-]+", text.lower())
    terms = []
    for w in words:
        if w in STOPWORDS:
            continue
        w = SYNONYMS.get(w, w)
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = SYNONYMS.get(w[:-1], w[:-1])  # hoodies -> hoodie -> hood
        terms.append(w)
    return terms


def _stock_by_product(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    stock: dict[str, dict[str, int]] = {}
    for r in conn.execute("SELECT product_id, size, quantity FROM inventory"):
        stock.setdefault(r["product_id"], {})[r["size"]] = r["quantity"]
    return stock


def _match(row: sqlite3.Row, stock: dict[str, int]) -> ProductMatch:
    return ProductMatch(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        colors=json.loads(row["colors"]),
        price_usd=row["price"],
        in_stock=any(q > 0 for q in stock.values()),
        sizes_in_stock=[s for s in SIZE_ORDER if stock.get(s, 0) > 0],
    )


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _resolve(conn: sqlite3.Connection, product_id: str) -> sqlite3.Row | ToolError:
    """Find a catalogue row by exact id, or by product name; else suggest close names."""
    row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", [product_id]).fetchone()
    if row is None:  # the model sometimes passes the display name instead of the id
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ? OR lower(name) = lower(?)",
            [_slug(product_id), product_id.strip()],
        ).fetchone()
    if row is not None:
        return row
    rows = {r["name"]: r for r in conn.execute("SELECT * FROM catalogue")}
    close = difflib.get_close_matches(product_id, list(rows), n=3, cutoff=0.4)
    stock = _stock_by_product(conn)
    return ToolError(
        error=f"No product with product_id '{product_id}'. Use search_products to find the exact id.",
        did_you_mean=[_match(rows[n], stock.get(rows[n]["product_id"], {})) for n in close],
    )


# ---------- Agent tools ----------


def search_products(
    query: str | None = None,
    garment_type: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size_in_stock: Size | None = None,
    limit: int = 8,
) -> SearchResults:
    """Search the Campus Customs catalogue. Use this first to find products and their ids.

    Args:
        query: Free-text keywords, e.g. "Harvard Yale game tee", "Branford", "baseball".
        garment_type: Kind of garment, e.g. "hoodie", "crewneck", "t-shirt", "quarter-zip", "jacket".
        color: A color the product must come in, e.g. "navy", "gray", "white".
        max_price: Only products at or below this price in USD.
        size_in_stock: Only products with at least one unit left in this size.
        limit: Maximum number of results (1-30). Use 30 for browse questions like
            "what hoodies do you have?" so every match can be shown on the page.

    Returns matches with id, name, colors, exact price, and which sizes are in stock.
    match_count 0 means nothing in the catalogue matched these filters.
    """
    limit = max(1, min(limit, 30))
    size = size_in_stock.upper() if size_in_stock else None
    with connect() as conn:
        rows = conn.execute("SELECT * FROM catalogue").fetchall()
        stock = _stock_by_product(conn)

    terms, type_terms, color_terms = _terms(query or ""), _terms(garment_type or ""), _terms(color or "")
    scored: list[tuple[int, ProductMatch]] = []
    for row in rows:
        match = _match(row, stock.get(row["product_id"], {}))
        if max_price is not None and match.price_usd > max_price:
            continue
        if size and size not in match.sizes_in_stock:
            continue
        gtype = match.garment_type.lower()
        if type_terms and not all(t in gtype or t in match.name.lower() for t in type_terms):
            continue
        colors = " ".join(match.colors).lower()
        if color_terms and not all(t in colors for t in color_terms):
            continue
        score = 1
        if terms:
            strong = f"{match.name} {gtype} {row['search_tags']}".lower()
            weak = f"{row['description']} {colors}".lower()
            score = sum(3 if t in strong else 1 if t in weak else 0 for t in terms)
            if score == 0:
                continue
        scored.append((score, match))
    scored.sort(key=lambda sm: (-sm[0], sm[1].name))

    filters = {
        "query": query, "garment_type": garment_type, "color": color,
        "max_price": max_price, "size_in_stock": size,
    }
    summary = ", ".join(f"{k}={v}" for k, v in filters.items() if v is not None) or "no filters"
    return SearchResults(
        query_summary=summary,
        match_count=len(scored),
        matches=[m for _, m in scored[:limit]],
    )


def get_product_info(product_id: str) -> ProductInfo | ToolError:
    """Description, colors, garment type, and exact price of one product.

    Call this before describing a product or quoting its price.

    Args:
        product_id: The exact product_id from search_products, e.g. "basic-hoodie-big-yale".
    """
    with connect() as conn:
        row = _resolve(conn, product_id)
        if isinstance(row, ToolError):
            return row
        sizes = {r["size"] for r in conn.execute(
            "SELECT size FROM inventory WHERE product_id = ?", [row["product_id"]]
        )}
    return ProductInfo(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        price_usd=row["price"],
        sizes_offered=[s for s in SIZE_ORDER if s in sizes],
    )


def check_stock(product_id: str, size: Size | None = None) -> StockReport | ToolError:
    """How many units are in stock, for one size or for every size.

    Call this for any availability or "how many left" question, and always before
    saying a size is available or sold out.

    Args:
        product_id: The exact product_id from search_products.
        size: Optional size the shopper asked about: XS, S, M, L, XL, or XXL.
            Leave empty to get every size.
    """
    with connect() as conn:
        row = _resolve(conn, product_id)
        if isinstance(row, ToolError):
            return row
        qty = {r["size"]: r["quantity"] for r in conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", [row["product_id"]]
        )}
    sizes = [SizeStock(size=s, quantity=qty[s], status=stock_status(qty[s])) for s in SIZE_ORDER if s in qty]
    requested = size.upper() if size else None
    if requested and requested not in qty:
        return ToolError(
            error=f"Size '{size}' is not offered for {row['name']}. Sizes: {', '.join(s.size for s in sizes)}."
        )
    return StockReport(
        product_id=row["product_id"],
        name=row["name"],
        price_usd=row["price"],
        requested_size=requested,
        requested_quantity=qty[requested] if requested else None,
        requested_status=stock_status(qty[requested]) if requested else None,
        sizes=sizes,
        sold_out_sizes=[s.size for s in sizes if s.quantity == 0],
        in_stock_sizes=[s.size for s in sizes if s.quantity > 0],
        total_units=sum(qty.values()),
    )


# Shopper-facing garment families, used to judge "similar".
CATEGORY_PATTERNS = [
    ("hoodie", re.compile(r"hood", re.I)),
    ("quarter-zip", re.compile(r"quarter-zip", re.I)),
    ("jacket", re.compile(r"jacket", re.I)),
    ("t-shirt", re.compile(r"t-shirt|performance shirt", re.I)),
    ("crewneck", re.compile(r"crew|mockneck", re.I)),
]
GENERIC_TAGS = {"yale", "campus customs", "college merch", "long sleeve", "short sleeve"}


def _category(garment_type: str) -> str:
    return next((name for name, rx in CATEGORY_PATTERNS if rx.search(garment_type)), "other")


def find_similar_products(
    product_id: str,
    size: Size | None = None,
    max_price: float | None = None,
    avoid_color: str | None = None,
    limit: int = 6,
) -> SimilarProducts | ToolError:
    """In-stock alternatives to one product, ranked by similarity.

    Use when a size is sold out, a color isn't offered, or the shopper asks for
    "something like this". Every result has stock (in `size`, if given).

    Args:
        product_id: The product to find alternatives for.
        size: Only suggest items with units left in this size (XS-XXL).
        max_price: Only suggest items at or below this USD price.
        avoid_color: Skip items whose main color matches this, e.g. "navy" for "a different color".
        limit: Number of suggestions (1-10).
    """
    limit = max(1, min(limit, 10))
    want = size.upper() if size else None
    with connect() as conn:
        base = _resolve(conn, product_id)
        if isinstance(base, ToolError):
            return base
        rows = conn.execute("SELECT * FROM catalogue WHERE product_id != ?", [base["product_id"]]).fetchall()
        stock = _stock_by_product(conn)

    base_cat = _category(base["garment_type"])
    base_tags = {t.lower() for t in json.loads(base["search_tags"])} - GENERIC_TAGS
    base_colors = {c.lower() for c in json.loads(base["colors"])}
    scored: list[tuple[float, SimilarItem]] = []
    for row in rows:
        match = _match(row, stock.get(row["product_id"], {}))
        if not match.in_stock or (want and want not in match.sizes_in_stock):
            continue
        if max_price is not None and match.price_usd > max_price:
            continue
        colors = [c.lower() for c in match.colors]
        if avoid_color and colors and avoid_color.lower() in colors[0]:
            continue
        reasons, score = [], 0.0
        if _category(row["garment_type"]) == base_cat:
            score += 5
            reasons.append(f"also a {base_cat}")
        shared_tags = base_tags & ({t.lower() for t in json.loads(row["search_tags"])} - GENERIC_TAGS)
        if shared_tags:
            score += 2 * min(len(shared_tags), 3)
            reasons.append("shares " + ", ".join(sorted(shared_tags)[:3]))
        shared_colors = base_colors & set(colors) if not avoid_color else set()
        if shared_colors:
            score += min(len(shared_colors), 2)
            reasons.append("same color " + "/".join(sorted(shared_colors)[:2]))
        score -= abs(match.price_usd - base["price"]) / 20  # prefer a similar price
        if score <= 0:
            continue
        scored.append((score, SimilarItem(**match.model_dump(exclude={"in_stock"}), reason="; ".join(reasons))))
    scored.sort(key=lambda si: -si[0])
    return SimilarProducts(based_on=base["name"], size_filter=want, items=[i for _, i in scored[:limit]])


AGENT_TOOLS = [search_products, get_product_info, check_stock, find_similar_products]


# ---------- API helpers (not given to the agent) ----------


def get_product_details(product_id: str) -> ProductDetail | None:
    """Everything the product page shows, or None if the id doesn't exist."""
    with connect() as conn:
        row = conn.execute(
            PRODUCT_SELECT + " WHERE c.product_id = ? GROUP BY c.product_id", [product_id]
        ).fetchone()
        if row is None:
            return None
        qty = {r["size"]: r["quantity"] for r in conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", [product_id]
        )}
    return ProductDetail(
        **_card(row, qty).model_dump(),
        search_tags=json.loads(row["search_tags"]),
        sizes=[SizeStock(size=s, quantity=qty[s], status=stock_status(qty[s])) for s in SIZE_ORDER if s in qty],
    )


def all_products() -> list[ProductCard]:
    with connect() as conn:
        stock = _stock_by_product(conn)
        rows = conn.execute(PRODUCT_SELECT + " GROUP BY c.product_id ORDER BY c.name")
        return [_card(r, stock.get(r["product_id"])) for r in rows]


def cards_for_ids(product_ids: list[str]) -> list[ProductCard]:
    """Resolve ids to cards in the given order, silently dropping unknown ids."""
    if not product_ids:
        return []
    by_id = {p.product_id: p for p in all_products()}
    seen: set[str] = set()
    cards = []
    for pid in product_ids:
        if pid in by_id and pid not in seen:
            seen.add(pid)
            cards.append(by_id[pid])
    return cards
