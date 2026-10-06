# Campus Customs: Usability Improvements (Problem 9)

Four improvements: two on the front end, and two in the agent and backend. For each one:
what I added, why it helps a Campus Customs shopper or the business, and **where a grader
can see it** in the running app.

Run the app: `cd backend && uvicorn main:app --reload --port 8000`, then
`cd frontend && npm run dev`, and open http://localhost:5173.

---

## Front end 1: Suggested-question chips in the chat

**What I added**

- A row of one-tap question chips above the chat input (`frontend/src/components/ChatWidget.tsx`).
- The chips **change with the page the shopper is on**:
  - **Product page:** "Is this in stock in M?", "What colors does this come in?", "Show me
    something similar".
  - **Products page, or with a category filter:** "What hoodies do you have?", "Gray
    crewnecks under $60", "What's in stock in XL?".
  - **Home, About, and other pages:** "What's new for game day?", "How do returns work?",
    "How long does shipping take?".
- Tapping a chip sends it immediately. Chips appear when the chat opens and again after
  every reply.

**Why it helps**

- **Shoppers:** many don't know what a shop chatbot can do, or don't want to type on a
  phone. Chips show what it's good at (stock by size, colors, comparisons, policies) and
  get an answer in one tap.
- **The business:** product-page chips ask exactly the questions that turn browsing into
  buying ("is it in my size?"), so the conversation leads to a sale instead of a blank
  text box.

**See it:** open the chat on Home, then open it on any product page. The chips are
different. Tap "Is this in stock in M?" on a product page.

---

## Front end 2: Sorting, an "in stock in my size" filter, and stock badges

**What I added**

- **Sort** on the Products page: Featured (A–Z), Price low → high, Price high → low.
- **"In stock in size"** filter (XS–XXL). It hides any product that's sold out in that
  size. The backend does the filtering, using `GET /api/products?size=M`.
- **Stock badges** on product cards, from live inventory (the API now returns stock per
  size on each card). They're shown **only when they matter**, so they stay a real signal
  (21 of 102 cards):
  - **"Only S, M, XL left"** when 3 or fewer sizes are still in stock
  - **"Low stock"** when there are 20 or fewer units in total
  - **"Sold out"** when nothing is left
  - With a size filter on, the badge is about **your** size: **"Only 2 left in XL"**.
  - My first version badged 100 of 102 cards. I tightened the rules after seeing that,
    because a badge on everything means nothing.
- The sort and size are kept in the URL (`/products?size=M&sort=price-asc`), so a shopper
  can share or bookmark the view, and the chat sees it as page context.

**Why it helps**

- **Shoppers:** the most common frustration in apparel shopping is falling for an item and
  then finding your size is gone. The size filter shows only what can actually be bought,
  and sorting by price helps students on a budget.
- **The business:** "Low stock" badges create honest urgency on items that are about to
  sell out. Showing only buyable items means fewer dead ends and fewer abandoned visits.

**See it:** Products → pick **XL** in "In stock in size", and the count drops. Choose
"Price: low → high". Low-stock and sold-out badges appear on the cards.

---

## Agent/backend 1: The `find_similar_products` tool

**What I added**

- A new agent tool in `backend/tools.py`, returning a new `SimilarProducts` model in
  `backend/models.py`.
- Given a `product_id` (and optionally a size, a maximum price, or a color to avoid), it
  scores every other catalogue item by:
  - the same garment category (hoodie, crewneck, tee, quarter-zip, jacket)
  - shared search tags (e.g. residential college, sport, "Harvard Yale")
  - shared colors
  - a similar price
- It returns the best in-stock matches, with a short `reason` for each.
- The prompt (`prompts/prompt.md`) tells the agent to call it when a size is sold out, when
  a color isn't offered, or when the shopper asks for "something like this".

**Why it helps**

- **More accurate answers:** before, the agent had to improvise alternatives with a
  keyword search, and sometimes suggested items that were also sold out or a different
  kind of garment. Now the alternatives are ranked by code from the database, and every
  one is guaranteed to be **in stock in the requested size**.
- **The business:** a "sold out" answer becomes a sale ("…but the Lacrosse crewneck is in
  stock in XL"), which keeps revenue that would otherwise be lost.

**See it:** on `/products/baseball-left-chest-crewneck` (sold out in XL), tap or ask "Show
me something similar" or "is this in XL?". The alternatives appear as cards on the page.

---

## Agent/backend 2: Live progress while the agent works

**What I added**

- A streaming endpoint, `POST /api/chat/stream` (`backend/main.py`), that sends
  newline-delimited JSON events while the agent runs.
- It uses PydanticAI's `event_stream_handler`. Each tool call is turned into a
  shopper-friendly status line: "Searching the catalogue for hoodies…", "Checking stock
  for size M…", "Finding similar items…".
- The last event carries the same `ChatResponse` as `/api/chat`, so history saving, page
  cards, and every validator work unchanged.
- The chat widget reads the stream and shows the live steps under the typing indicator.

**Why it helps**

- **Shoppers:** a reply that checks the database can take 5–10 seconds, and a silent
  spinner feels broken. Seeing "Checking stock for size M…" makes the wait feel shorter,
  shows the assistant is checking real inventory, and builds trust in the answer.
- **The business:** shoppers are less likely to give up during the wait. Showing the
  tool steps also makes it clear the answer comes from real inventory, not a guess. The
  old `/api/chat` route still works, which keeps things simple to test and debug.

**See it:** ask any product question in the chat. While it works, the bubble shows lines
like "🔎 Searching the catalogue…" and then "📦 Checking stock for size XL…".

---

## Verification (tested in the running app)

All checks were run against the live site (Vite + `uvicorn main:app` from `backend/`), and
the numbers were compared with `campus_customs.db`.

| # | Improvement | What I did | What happened |
|---|---|---|---|
| F1 | Suggested chips | Opened the chat on `/`, `/products?category=jackets`, and `/products/baseball-left-chest-crewneck` | **Home:** "What's good for game day?", "How do returns work?", "How long does shipping take?". **Jackets:** "What jackets do you have?", … **Product page:** "Is this in stock in M?", "What colors does this come in?", "Show me something similar". Tapping a chip sent it, and the chips came back after the reply. |
| F2 | Sort, size filter, badges | Products page: picked **XL**, then "Price: low → high" | "102 items" became "**77 items in stock in size XL**" (the DB has 77 product×XL rows with stock > 0). The URL became `?size=XL&sort=price-asc`. Prices ran in ascending order, $32 → $98. Badges: 21/102 cards with no filter (e.g. "Champion Reverse Weave Crewneck → Only M, XL left", which matches the DB: M 12, XL 12, the rest 0). With XL on: "Only 2 left in XL". |
| B1 | `find_similar_products` | On the Baseball crewneck page (sold out in XL): asked "is this available in XL?", then tapped "Show me something similar" | **XL question:** the agent called `check_stock` → `find_similar_products(size="XL")` and said "**sold out in XL**… similar options include Hype And Vice… Offside Crewneck, Davenport College Crewneck… each **$58**". **Similar:** 6 crewnecks shown as page cards, all in stock (DB checked), each with a reason such as "also a crewneck; shares left chest logo, navy sweatshirt". `avoid_color="navy"` on the navy Basic Hoodie returned only hoodies whose main color is gray or charcoal. |
| B2 | Live progress | curl to `/api/chat/stream`, and the chat widget | The stream sent `📦 Checking stock for size XL…` at **2.7 s**, `🧭 Finding similar items in stock in XL…` at **4.1 s**, and the final answer at **6.8 s**, so the steps really arrive before the reply. In the widget: "Thinking…" became "🧭 Finding similar items in stock…" at 3.0 s. A two-part question showed two live steps ("🔎 Searching the catalogue for … Basic Hoodie Big Yale in size XL…" and "🔎 Searching the catalogue for navy crewneck in size XL…"). |

**Data note found while testing B2:** for "navy crewnecks in XL" the agent reported 20
items, including the **School Of Architecture Crewneck at $72**. That product's name says
"Crewneck", but its `garment_type` in the seed data is "quarter-zip pullover sweatshirt".
The agent was faithful to the catalogue; the catalogue is inconsistent. The price checker
passed because $72 really is that item's price.

### Files changed

- **Front end:**
  - `src/components/ChatWidget.tsx` (chips, live steps, streaming)
  - `src/api.ts` (`sendChatStream`, `fetchProducts(q, size)`, `Product.stock`)
  - `src/pages/Products.tsx` (sort and size filter)
  - `src/components/ProductCard.tsx` (badges)
  - `src/index.css`
- **Backend:**
  - `tools.py` (`find_similar_products`, per-size `stock` on cards)
  - `models.py` (`SimilarProducts`, `SimilarItem`, `ProductCard.stock`, `PageContext.size_filter`)
  - `agent.py` (`tool_status`, `event_stream_handler`, size-filter page context)
  - `main.py` (`/api/chat/stream`, the shared `answer_chat`, `?size=` on `/api/products`)
  - `memory.py` (passes `?size=` to page context)
  - `prompts/prompt.md` (when to call `find_similar_products`)
