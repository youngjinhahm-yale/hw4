# AI Prompts

Log of what I typed to my vibe coder (Claude Code) for HW4, Campus Customs.
One section per problem.

## Problem 1: Vibe coder prompts

### Prompt typed

Create AI_prompts.md at the start of the assignment and keep it updated as you
work. This file is the log of what you typed to your vibe coder. Describe each
problem to your vibe coder in your own words. Do not paste this who page or the
assignment URL and ask it to do everything for you. Put one section for each
problem. Each section must include: the problem number and title, at least one
prompt you typed, in your own words as much as possible, one follow-up prompt if
you needed it (and one sentence on what was lacking after the first). Your
running site, database writes, and screentshots are the evidence - you do not
need an extra prffo essay beyond these prompts

### Follow-up prompt typed

None needed. The first prompt was enough to create this log file.

## Problem 2: Analyze the database

### Prompt typed

Look at the database data/campus_customs.db and understand the field of each
table. At a minimun you should understand catalogue, inventory, and users.
Start the file output/harness.md. Write down each table and its fields, and one
short line on why eac hfield matters for the shop or the chatbot. You will keep
growing this harness file in later problem (models, tools, safety, specs).

### Follow-up prompt typed

None needed. The first prompt was enough to document every table and field.

## Problem 3: Build the Campus Customs website

### Prompt typed

Scaffold a React + vite + TypeScript front end for Campus Custom. Put a nav bar
at the top that links to the main pages: Home, Products, About us, Log in,
Create Account. Pull Campus Customs-style wording from yalebulldogblue.com for
Home and About Us, but write these apges in your own voice (do not copy the
original site text). On the Products page, show product images from the
catalogue (use the image paths in the database) with basic product info (name,
price, short description). Make each product open a single-itme page (large
image on one side, full product text on the other - description, price,
sizes/stock when you have them). Clicking a card on Products should take the
shopper there. Add a chat interface in the bottom right of the site (a floating
chat panel is fine). It does not need to talk to an agent yet - a stub that
will call your backend later is enough for this problem. You will need a small
API soon to read the database. It is fine to start a simple FastAPI app in
backend/main.py just to serve products and images, then grow it into the agent
backend in Problem 5.

### Follow-up prompt typed

None needed. The first prompt was enough to build the site, product pages, chat
stub, and product API.

## Problem 4: Create account and login

### Prompt typed

Build a normal create-account / login flow. Create account: first name, last
name, email, password (confirm password is a nice touch). Log in: email and
password. New accounts go into the users table. Make sure to store passwords
securely so harckers (human or AI) cannot access them. The seed databased
already has a test user you can use while building: email:
test@campustcustoms.yale.edu, Password: password. Confirm you can log in as that
user, and that a brand-new account you create also works. Update
output/harness.md with how auth works (what you store for a user and how
passwords are protected)

### Follow-up prompt typed

None needed. The first prompt was enough to build sign-up, login, and logout,
and to test both the seed user and a new account.

## Problem 5: Pydantic AI agent backend

### Prompt typed

Build the shop chatbot as a PydanticAI agent behind FastAPI, plugged into your
front-end chat widget. Put the API app in backend/main.py - that is the file you
run with Uvicorn. Keep the agent as these four files next to it:
backend/prompt/prompt.md - system prompt (grow this same file later),
backend/agent.py - agent entry / wiring, backend/tools.py - tools the agent can
call, backend/models.py - pydantic / pydanticAI structured types. In main.py,
expose a chat route so a message from the website returns a reply from the agent
(and whatever else you need for products/auth). You will need your AI mode API
key for the agent. Put Campus Customs voice and safety basics into
prompts/prompt.md (you will expand tools and safety later). Start or update types
in models.py for chat replies / product cards as needed. In output/harness.md,
note how the front end talks to FastAPI and how the agent is loaded (prompt file
+ model). Make sure the backend runs from the backend/ folder like this: uvicorn
main:app --reload --port 8000

### Follow-up prompt typed

None needed. The first prompt was enough to build the agent backend and connect
it to the chat widget.

## Problem 6: Tools: product info and stock

### Prompt typed

Give the agent tools that look up real information from campus_customs.db:
product description, price, how many are in stock (by size when the customer
asks). The agent must use the database - it should not invent prices or
quantities. If a size is out of stock, say so clearly. Expand prompts/prompt.md
so the agent knows to call these tools for price and stock questions. Add or
update return types in models.py. In output/harness.md, list each tools and
explain which model fields you chose for lookup results and why.

### Follow-up prompt typed

None needed. The first prompt was enough to add the tools, the return types, and
the prompt rules.

## Problem 7: Chat search that updates the page

### Prompt typed

Now we will add a neat feature to the site. When a customer asks about a type of
item - for example "what hoodies do you have? - the agent should search the
catalogue and the webstie should dynamically show those matching items as
product card (image, name, price, short info). This is an API contract: the
agent returns structured product matches and then the fron end renders them on
the website. It looks really cool. After the dyanamic product cards ard loaded
by your new feature, make sure the same single-itme page behavior you built in
Problem 3 still words: each product card - including the ones the chat just put
on the page - should still open that detail view (large image + full info) when
clicked. Update prompts/prompt.md and output/harness.md so it is clear how
search results reach the page

### Follow-up prompt typed

None needed. The first prompt was enough to build the results panel and keep the
detail page working.

## Problem 8: Customer memory

### Prompt typed

When a shopper is logged in, save their chat history in the database in an
appropriate table and reload it when they return. The agent should know who is
chatting (name, email) - put that in agent deps (or an equivalent clear pattern)
and/or tools the agent can call. Also pass enough page context that if someone
is on a product page and asks "do you have this in pink?", the agent knows which
item they mean. Hint: you can put code into the agent context. Guest can still
chat, but history only needs to persist for logged-in users. Document in
output/harness.md: how user chat history is stored, what customer fields the
agent sees, and how page context is passed

### Follow-up prompt typed

None needed. The first prompt was enough to add saved history, customer deps,
and page context.

## Problem 9: Usability improvements

### Prompt typed

Now that the core shop wors, improve it. Choose and implement: 2 front-end
usability improvments, 2 agent/backend usability improvement. Front-end
improvements are things that make the site look better and make it easier to
use. Agent / backend improvements are things that make the agent output better,
more accurate, or safer. These could be new agent tools or things that make the
agent run faster or cheaper. write output/usability.md before or as you build.
for each of the improvments, say: what you added, why it helps a Campus Customs
shopper or the buisness. Then make sure all improvement actually show up in the
running app. Graders will read the write-up and look for the features.

### Follow-up prompt typed

None needed. The first prompt was enough to choose, build, document, and test
all four improvements.

## Problem 10: Style the website

### Prompt typed

Add creative design so the site feels like a real Campus Customs storefront -
fonts, color, hierarchy, motion, product presentation, chat feel. You will get
more points for imaginative and innovative design. Write output/design.md: what
you changed and why it should help customers stick around and buy. Keep it
concrete and short.

### Follow-up prompt typed

Design based on Yale vs Harvard. But we're dealing with Yale Campus Customs, so
emphasis should be put on Yale

The first prompt set the goals but not a theme; this follow-up gave the creative
direction (the Yale–Harvard rivalry, with Yale as the clear focus).

## Problem 11: Site testing (app check)

### Prompt typed

Test the live site and document it in output/app_check.html (a page you can
double-click open). Include clear screenshots and short captions for: 1. Chat
checking the inventory level of an item (honest stock/price from the DB) 2. The
dynamic search-result cards appearing after a category question (e.g. hoodies)
3. One of the usability features you added in Problem 9. Make the HTML easy to
grade: heading for each check, screenshot, one or two sentences on what the
screenshot proves. Put the screenshot image files in output/app_check_images/
and link t hem from app_check.html with relative paths (for example
app_check_images/inventory.png).

### Follow-up prompt typed

None needed. The first prompt was enough to run the checks, capture the
screenshots, and build the report.

## Problem 12: Audit trail, safety, finish harness

### Prompt typed

Kepp an append-only output/audit_Trail.json of agent-loop activity (time, tool
name, short args/result, stop reason). Do not wipe it between runs. Also think
of some safety rules to give the agent and put them in prompts/prompt.md. Finish
output/harness.md so it is clear how the system works: model fields in
models.py and why you chose them, tools and abilities, safety rules, specs (loop
limits, result caps, models, how to run front + back)

### Follow-up prompt typed

None needed. The first prompt was enough to build the audit trail, add the
safety rules, and finish the harness.
