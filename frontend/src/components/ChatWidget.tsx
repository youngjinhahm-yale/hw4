import { Fragment, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  clearChatHistory,
  fetchChatHistory,
  formatPrice,
  sendChatStream,
  type ChatResults,
  type ChatTurn,
} from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'

/** One-tap starter questions that match the page the shopper is on. */
function suggestionsFor(pathname: string, search: string): string[] {
  if (/^\/products\/[^/]+/.test(pathname))
    return ['Is this in stock in M?', 'What colors does this come in?', 'Show me something similar']
  if (pathname.startsWith('/products')) {
    const category = new URLSearchParams(search).get('category')
    const first = category && category !== 'other' ? `What ${category} do you have?` : 'What hoodies do you have?'
    return [first, 'Gray crewnecks under $60', "What's in stock in XL?"]
  }
  return ["What's good for game day?", 'How do returns work?', 'How long does shipping take?']
}

interface Message extends ChatTurn {
  results?: ChatResults
  error?: boolean
  greeting?: boolean // local only: never sent to the agent or saved
}

const PREVIEW_CARDS = 3

const greeting = (name?: string, returning = false): Message => ({
  role: 'assistant',
  greeting: true,
  content: returning
    ? `Welcome back, ${name}! Your earlier chat is above. What can I sniff out for you today? 💙`
    : `Woof${name ? `, ${name}` : ''}! I'm Dan, the Campus Customs bulldog. Ask me about hoodies, sizes, prices, or stock. 💙`,
})

/** Tiny formatter for the agent's replies: **bold** and "- " bullet lists only. */
function renderText(text: string): ReactNode {
  const bold = (line: string) =>
    line.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
      part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
    )
  const blocks: ReactNode[] = []
  let bullets: string[] = []
  const flush = () => {
    if (bullets.length)
      blocks.push(
        <ul key={blocks.length}>
          {bullets.map((b, i) => (
            <li key={i}>{bold(b)}</li>
          ))}
        </ul>,
      )
    bullets = []
  }
  for (const line of text.split('\n')) {
    const m = line.match(/^\s*[-*•]\s+(.*)$/)
    if (m) bullets.push(m[1])
    else {
      flush()
      if (line.trim()) blocks.push(<p key={blocks.length}>{bold(line)}</p>)
    }
  }
  flush()
  return blocks.map((b, i) => <Fragment key={i}>{b}</Fragment>)
}

export default function ChatWidget() {
  const { user } = useAuth()
  const { show: showOnPage } = useChatResults()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  // One-time nudge bubble next to the launcher (dismissed for the session once seen).
  const [teaser, setTeaser] = useState(false)
  useEffect(() => {
    if (sessionStorage.getItem('cc-teaser-seen')) return
    const id = setTimeout(() => setTeaser(true), 4000)
    return () => clearTimeout(id)
  }, [])
  function dismissTeaser() {
    setTeaser(false)
    sessionStorage.setItem('cc-teaser-seen', '1')
  }
  const [messages, setMessages] = useState<Message[]>([greeting()])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [steps, setSteps] = useState<string[]>([]) // live tool progress while sending
  const listRef = useRef<HTMLDivElement>(null)
  const suggestions = suggestionsFor(location.pathname, location.search)

  // On log in (or page load while logged in), reload the saved conversation from the
  // server. Guests and logged-out shoppers start fresh; their chat is never stored.
  useEffect(() => {
    if (!user) {
      setMessages([greeting()])
      return
    }
    let cancelled = false
    setMessages([greeting(user.first_name)])
    fetchChatHistory()
      .then((saved) => {
        if (cancelled || saved.length === 0) return
        const restored: Message[] = saved.map((m) => ({
          role: m.role,
          content: m.content,
          results: m.results ?? undefined,
        }))
        setMessages([...restored, greeting(user.first_name, true)])
      })
      .catch(() => {}) // keep the plain greeting if history can't load
    return () => {
      cancelled = true
    }
  }, [user])

  async function handleClearHistory() {
    if (!user || !confirm('Delete your saved chat history?')) return
    await clearChatHistory().catch(() => {})
    setMessages([greeting(user.first_name)])
  }

  useEffect(() => {
    // Scroll only the message list; scrollIntoView would also scroll the page and
    // fight the results panel scrolling into view.
    const list = listRef.current
    list?.scrollTo({ top: list.scrollHeight, behavior: 'smooth' })
  }, [messages, open, sending, steps])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    void send(input)
  }

  async function send(raw: string) {
    const text = raw.trim()
    if (!text || sending) return
    // Guests: earlier turns (minus greetings and failed replies) give the agent context.
    // Logged in: the server loads history from the database instead.
    const history: ChatTurn[] = messages
      .filter((m) => !m.error && !m.greeting)
      .map(({ role, content }) => ({ role, content }))
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: text }])
    setSending(true)
    setSteps([])
    try {
      // Page context: on /products/<id> the agent knows which item "this" means.
      // Streaming: each tool call shows up live ("📦 Checking stock for size M…").
      const res = await sendChatStream(
        text,
        history,
        { path: location.pathname, search: location.search },
        (step) => setSteps((s) => [...s, step]),
      )
      const results = res.results ?? undefined
      setMessages((m) => [...m, { role: 'assistant', content: res.reply, results }])
      // The agent's structured matches become product cards on the page itself.
      if (results) showOnPage(results)
    } catch (err) {
      const content =
        err instanceof Error && err.message && !/^\d{3} /.test(err.message)
          ? err.message
          : "Sorry, I can't reach the shop right now. Please try again in a moment."
      setMessages((m) => [...m, { role: 'assistant', content, error: true }])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label="Campus Customs chat">
          <header className="chat-header">
            <div className="chat-title">
              <span className="dan-avatar dan-avatar-lg" aria-hidden="true">🐶</span>
              <div>
                <strong>Ask Dan</strong>
                <small>
                  <span className="online-dot" aria-hidden="true" />
                  {user ? 'Live stock · history saved to your account' : 'Live stock · guest chat'}
                </small>
              </div>
            </div>
            <div className="chat-header-actions">
              {user && (
                <button className="chat-clear" onClick={handleClearHistory} title="Delete saved chat history">
                  Clear
                </button>
              )}
              <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
                ×
              </button>
            </div>
          </header>
          <div className="chat-messages" ref={listRef}>
            {messages.map((m, i) => (
              <div key={i} className={`chat-turn chat-turn-${m.role}`}>
                <div className="chat-row">
                  {m.role === 'assistant' && (
                    <span className="dan-avatar" aria-hidden="true">🐶</span>
                  )}
                  <div className={`chat-msg chat-msg-${m.role} ${m.error ? 'chat-msg-error' : ''}`}>
                    {m.role === 'assistant' ? renderText(m.content) : m.content}
                  </div>
                </div>
                {m.results && (
                  <>
                    <div className="chat-products">
                      {m.results.products.slice(0, PREVIEW_CARDS).map((p) => (
                        <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-product">
                          <img src={p.image_url} alt="" />
                          <span className="chat-product-name">{p.name}</span>
                          <span className="chat-product-price">{formatPrice(p.price)}</span>
                        </Link>
                      ))}
                    </div>
                    <button className="chat-see-all" onClick={() => m.results && showOnPage(m.results)}>
                      {m.results.products.length > PREVIEW_CARDS
                        ? `See all ${m.results.products.length} on the page ↑`
                        : 'Show on the page ↑'}
                    </button>
                  </>
                )}
              </div>
            ))}
            {sending && (
              <div className="chat-msg chat-msg-assistant chat-typing" aria-live="polite">
                {steps.length === 0 ? (
                  <span className="paws" aria-label="Dan is thinking">
                    <span>🐾</span>
                    <span>🐾</span>
                    <span>🐾</span>
                  </span>
                ) : (
                  <ul className="chat-steps">
                    {steps.map((s, i) => (
                      <li key={i} className={i === steps.length - 1 ? 'chat-step-current' : 'chat-step-done'}>
                        {s}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
          {!sending && (
            <div className="chat-suggestions" aria-label="Suggested questions">
              {suggestions.map((s) => (
                <button key={s} className="chat-suggestion" onClick={() => void send(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}
          <form className="chat-form" onSubmit={handleSubmit}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Do you have navy hoodies in M?"
              aria-label="Chat message"
              maxLength={1000}
            />
            <button type="submit" className="btn" disabled={sending || !input.trim()}>
              Send
            </button>
          </form>
        </section>
      )}
      {teaser && !open && (
        <div className="chat-teaser" role="status">
          <button className="chat-teaser-close" onClick={dismissTeaser} aria-label="Dismiss">
            ×
          </button>
          <strong>Need a size?</strong> I can check live stock for any item. 🐾
        </div>
      )}
      <button
        className={`chat-toggle ${open ? 'chat-toggle-open' : ''}`}
        onClick={() => {
          setOpen((o) => !o)
          dismissTeaser()
        }}
        aria-label={open ? 'Close chat' : 'Open chat with Dan'}
      >
        {open ? (
          '×'
        ) : (
          <>
            <span className="dan-avatar" aria-hidden="true">🐶</span>
            <span className="chat-toggle-label">Ask Dan</span>
          </>
        )}
      </button>
    </div>
  )
}
