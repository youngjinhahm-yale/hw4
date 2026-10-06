# Campus Customs: Yale shop with an AI chat assistant (HW4)

A customer website for **Yale Bulldog Blue by Campus Customs**. Shoppers can browse
products, create an account, and chat with **Dan**, a PydanticAI shop agent. Dan answers
honestly about price and stock from a local SQLite database, and puts matching product
cards right on the page.

- **Front end:** React + Vite + TypeScript (`frontend/`)
- **Back end:** Python FastAPI (`backend/main.py`)
- **Agent:** PydanticAI through Portkey (`gpt-5.6-luna`), in four files:
  - `backend/prompts/prompt.md`: the system prompt (voice, tool rules, safety rules)
  - `backend/agent.py`: agent wiring, the output validator, and the run loop and audit
  - `backend/tools.py`: read-only database tools (`search_products`,
    `get_product_info`, `check_stock`, `find_similar_products`)
  - `backend/models.py`: Pydantic types for tool results, agent output, and the API
- **Supporting backend modules:**
  - `auth.py`: accounts and sessions
  - `db.py`: SQLite connections
  - `memory.py`: chat history and page context
  - `audit.py`: the append-only audit trail

How it all fits together is explained in [`output/harness.md`](output/harness.md).

## 1. Place the data pack (not in git)

The database and product images are **not** in this repository. Unzip the course data
pack so you have:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/          # images referenced by the catalogue
```

## 2. Add your API key

```bash
cp .env.example .env
```

Edit `.env` and set `PORTKEY_API_KEY`. (A `.env` in the folder above `hw4/` also works.)

## 3. Run the back end (FastAPI, port 8000)

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

Check it at http://127.0.0.1:8000/api/health → `{"status":"ok"}`.

## 4. Run the front end (Vite, port 5173)

Requires Node 20+. In a second terminal, from `hw4/`:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` and `/images` to the backend on port
8000.

Test login: `test@campuscustoms.yale.edu` / `password`. You can also create your own
account.

## Things to try

- **Products** → filter "In stock in size: XL", then sort by price.
- On any product page, open **Ask Dan** and tap "Is this in stock in M?". The chat checks
  live inventory, and you can watch the tool steps as it works.
- Ask "What hoodies do you have?". All matching hoodies appear as cards on the page, and
  each card opens its detail page.
- Log in, chat, then reload: your chat history comes back.

## Repository layout

```
hw4/
├── AI_prompts.md          # log of prompts typed to the vibe coder
├── README.md
├── requirements.txt
├── .env.example           # placeholders only
├── .gitignore             # keeps .env, data/, .venv/, node_modules/ out of git
├── frontend/              # Vite React TypeScript app
├── backend/
│   ├── main.py            # FastAPI app: uvicorn main:app --reload --port 8000
│   ├── agent.py
│   ├── models.py
│   ├── tools.py
│   ├── prompts/
│   │   └── prompt.md
│   └── auth.py, db.py, memory.py, audit.py
└── output/
    ├── harness.md         # how the system works: data, models, tools, safety, specs
    ├── design.md          # visual design choices
    ├── usability.md       # Problem 9 improvements
    ├── app_check.html     # live-site test report (open in a browser)
    ├── app_check_images/  # screenshots used by app_check.html
    └── audit_trail.json   # append-only log of agent runs
```
