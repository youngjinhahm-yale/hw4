// Typed helpers for the Campus Customs FastAPI backend (proxied by Vite).

export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  price: number
  image_url: string
  total_stock: number
  /** Units per size, e.g. { XS: 0, S: 15, ... } */
  stock: Record<string, number>
}

export const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL'] as const
export const LOW_STOCK = 5 // same threshold as the backend's LOW_STOCK_THRESHOLD

export interface SizeStock {
  size: string
  quantity: number
}

export interface ProductDetail extends Product {
  search_tags: string[]
  sizes: SizeStock[]
}

/** Product matches the agent found; the page renders these as product cards. */
export interface ChatResults {
  title: string
  products: Product[]
}

/** API contract for POST /api/chat (mirrors ChatResponse in backend/models.py). */
export interface ChatReply {
  reply: string
  results: ChatResults | null
}

export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
  created_at: string
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** Turn FastAPI's {detail: ...} error bodies into a readable message. */
function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0] as { loc?: string[]; msg?: string }
    const field = first.loc?.[first.loc.length - 1]?.replace('_', ' ')
    return field ? `${field}: ${first.msg}` : (first.msg ?? fallback)
  }
  return fallback
}

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { credentials: 'same-origin', ...init })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(res.status, errorMessage(body, `${res.status} ${res.statusText}`))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

const postJson = <T>(url: string, data?: unknown) =>
  getJson<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: data === undefined ? undefined : JSON.stringify(data),
  })

export const fetchMe = () => getJson<User>('/api/auth/me')
export const login = (email: string, password: string) =>
  postJson<User>('/api/auth/login', { email, password })
export const signup = (data: {
  first_name: string
  last_name: string
  email: string
  password: string
}) => postJson<User>('/api/auth/signup', data)
export const logout = () => postJson<void>('/api/auth/logout')

/** All products; `q` filters by keyword, `size` keeps only items in stock in that size. */
export function fetchProducts(q?: string, size?: string): Promise<Product[]> {
  const params = new URLSearchParams()
  if (q) params.set('q', q)
  if (size) params.set('size', size)
  const qs = params.toString()
  return getJson<Product[]>(`/api/products${qs ? `?${qs}` : ''}`)
}

export function fetchProduct(id: string): Promise<ProductDetail> {
  return getJson<ProductDetail>(`/api/products/${encodeURIComponent(id)}`)
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

/** Where the shopper is; the server turns this into page context for the agent. */
export interface PageInfo {
  path: string
  search: string
}

/**
 * Send a message, the page the shopper is on, and (for guests) recent turns.
 * Logged-in shoppers' history comes from the server, so `history` is ignored for them.
 */
export const sendChat = (message: string, history: ChatTurn[], page: PageInfo) =>
  postJson<ChatReply>('/api/chat', { message, history: history.slice(-20), page })

/**
 * Streaming version of sendChat (POST /api/chat/stream, newline-delimited JSON).
 * Calls onStatus for each tool step ("📦 Checking stock for size M…"), then resolves
 * with the same ChatReply as /api/chat.
 */
export async function sendChatStream(
  message: string,
  history: ChatTurn[],
  page: PageInfo,
  onStatus: (text: string) => void,
): Promise<ChatReply> {
  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history: history.slice(-20), page }),
  })
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => null)
    throw new ApiError(res.status, errorMessage(body, `${res.status} ${res.statusText}`))
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (value) buffer += decoder.decode(value, { stream: true })
    let newline: number
    while ((newline = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, newline).trim()
      buffer = buffer.slice(newline + 1)
      if (!line) continue
      const event = JSON.parse(line)
      if (event.type === 'status') onStatus(event.text)
      else if (event.type === 'done') return event.response as ChatReply
      else if (event.type === 'error') throw new ApiError(event.status ?? 500, event.detail)
    }
    if (done) throw new ApiError(500, 'The chat stream ended unexpectedly. Please try again.')
  }
}

export interface HistoryMessage extends ChatTurn {
  results: ChatResults | null
  created_at: string
}

export const fetchChatHistory = () => getJson<HistoryMessage[]>('/api/chat/history')
export const clearChatHistory = () => getJson<void>('/api/chat/history', { method: 'DELETE' })

export const formatPrice = (price: number) => `$${price.toFixed(2)}`

/** First sentence of a description, for product cards. */
export function shortDescription(text: string, max = 110): string {
  const first = text.split(/(?<=\.)\s/)[0]
  return first.length <= max ? first : first.slice(0, max).trimEnd() + '…'
}

/** Group the 22 raw garment_type values into a few shopper-friendly categories. */
export const CATEGORIES = [
  { key: 'hoodies', label: 'Hoodies', match: (t: string) => /hood/i.test(t) },
  { key: 'crewnecks', label: 'Crewnecks', match: (t: string) => /crew/i.test(t) && !/t-shirt/i.test(t) },
  { key: 'tees', label: 'T-Shirts', match: (t: string) => /t-shirt|performance shirt/i.test(t) },
  { key: 'quarter-zips', label: 'Quarter-Zips', match: (t: string) => /quarter-zip/i.test(t) },
  { key: 'jackets', label: 'Jackets & Fleece', match: (t: string) => /jacket/i.test(t) },
  { key: 'other', label: 'More', match: (t: string) => /mockneck/i.test(t) },
] as const
