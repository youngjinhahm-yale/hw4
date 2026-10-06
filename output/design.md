# Campus Customs: Design (Problem 10)

**Concept: "The Game, Yale-first."** The site borrows the energy of the Yale–Harvard
rivalry (scoreboards, varsity lettering, pennants, a stadium ticker), but **Yale blue owns
the page**. Harvard crimson is only the rival accent: a thin sideline in the hero, the
ticker's top stripe, "The Game" badges, and the underline under "Harvard." It's never
used as a background.

## What changed and why it helps shoppers stay and buy

| Area | What I changed | Why it helps |
|---|---|---|
| **Type** | **Graduate** (varsity block letters) for big headlines, labels, and sizes. **Libre Caslon Text** (a classic Yale-heritage serif) for headings, prices, and descriptions. **Inter** for body text and buttons. | Reads like real collegiate apparel, not a template. A clear hierarchy (shout → name → detail) makes pages faster to scan. |
| **Color** | Yale Blue `#00356b` everywhere that matters, Yale secondary blue `#286dc0` for accents, ivory "pennant felt" backgrounds, and crimson `#a51c30` only for rival details. | Strong brand recognition. Crimson used sparingly makes the rivalry pop without diluting Yale. |
| **Logo** | An inline-SVG shield with a serif **Y** and a crimson top band (also the favicon). It tilts on hover. | A real storefront mark instead of a text box. Recognizable in a browser tab. |
| **Hero** | "**BEAT HARVARD.**" in varsity letters with a crimson underline that draws itself in. Football-field yard lines and a crimson sideline. A live **scoreboard countdown** (YALE vs HARVARD: days/hrs/min to The Game, computed as the Saturday before Thanksgiving). A tilted "jersey card" of the 2025 Game tee. | Creates a seasonal reason to buy *now*. The countdown is urgency without fake discounts, and it puts the hero product one click away. |
| **Ticker** | A scrolling stadium ticker under the nav ("Beat Harvard · Bulldogs! Bulldogs! Bow wow wow! · Made to order in New Haven · Returns within 30 days"). It pauses on hover. | Game-day atmosphere, and it repeats trust messages (licensed, returns) on every page. |
| **Home merchandising** | A **Game Day Kit** (rivalry tee, Gameday hood, vintage bulldog pieces), **"Rep your college"** felt pennants for the 11 residential colleges we carry (live item counts → filtered shop), category tiles with banner tags, and **Ask Dan** among the perk cards. | Curated entry points beat a raw grid. College pennants speak to students' strongest identity after Yale itself. |
| **Product cards** | A Yale stripe sweeps across the top on hover. The image zooms and a "View details →" pill slides up. A **size-availability strip** (XS–XXL: blue = in stock, amber = low, struck = sold out). A crimson "The Game" tag on rivalry items. Serif price. | Shoppers see whether their size exists *before* clicking, so there are fewer dead ends and more confident clicks. |
| **Product page** | **Hover-to-zoom** follows the cursor (inspect prints and stitching). Size buttons styled as **jersey numbers**. Heritage-serif description. Sticky image. | Online apparel lacks touch; zoom and clear size choices reduce hesitation and returns. |
| **Chat** | The bot is now **"Dan"**, a bulldog helper and a nod to Handsome Dan, Yale's mascot (`🐶` avatar, "Ask Dan" pill launcher that wags now and then). A one-time "Need a size?" bubble. A gradient header with a green "live stock" dot and a crimson stripe. Dotted ivory chat background. **Paw-print typing dots** 🐾. Live tool steps with ✓. The prompt tells the agent it's Dan. | A friendly, on-brand helper gets far more use than a generic 💬. More chats mean more size and stock questions answered, which means more sales. |
| **Motion** | Hero lines rise in, the underline draws, sections fade up on scroll, cards lift, the scoreboard colon blinks, and the chat panel pops. Everything is turned off under `prefers-reduced-motion`. Reveal is **fail-safe**: on-screen content shows at once, and everything shows within 2.5 s even if the observer never fires. | Feels alive and premium without blocking content or hurting accessibility. |
| **Footer** | A row of pennant flags, a varsity "BULLDOGS! BULLDOGS! BOW WOW WOW!" chant, and Shop/Help columns including **The Game** and order contact. | Ends every page on school spirit and gives a clear next step. |

## Checked in the running app

- **Fonts:** Graduate, Libre Caslon, and Inter all load (`document.fonts.check` is true),
  and the hero is set in Graduate.
- **Scoreboard:** the countdown shows "46 days : 14 hrs : 15 min · until The Game · Sat,
  Nov 21" (as of Oct 5, 2026).
- **Home page:** the Game Day Kit shows the 4 rivalry items, there are 11 college pennants
  with counts, and all 5 reveal sections become visible.
- **Product page:** the 2025 Game tee shows "The Game" badges, hover zoom updates the zoom
  origin, and the size buttons use Graduate.
- **Chat:** Dan answered "what's your name? and is this in stock in M?" with "I'm Dan…
  in stock in M, with 20 left". The DB has M = 20. The paw-print typing indicator showed
  while it worked.
- **Mobile (375 px):** no horizontal scroll, the hero stacks, and the chat-results header
  stacks. The production build passes.

Files: `index.html` (fonts), `public/favicon.svg`, `src/index.css` (full redesign),
`components/{YaleMark,Ticker,GameCountdown}.tsx` (new), `src/useReveal.ts` (new), and
updates to `NavBar`, `Footer`, `ProductCard`, `ChatWidget`, `pages/Home`,
`pages/ProductPage`, and `backend/prompts/prompt.md` (the Dan persona).
