import { createContext, useContext, useState, type ReactNode } from 'react'
import type { ChatResults } from './api'

/** Latest product matches from the chat agent, shared by the chat widget and the page. */
export interface PageResults extends ChatResults {
  id: number // bumps on every new result set so the panel re-opens and scrolls into view
}

interface ChatResultsState {
  results: PageResults | null
  show: (results: ChatResults) => void
  clear: () => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<PageResults | null>(null)

  const value: ChatResultsState = {
    results,
    show: (r) => setResults({ ...r, id: Date.now() }),
    clear: () => setResults(null),
  }

  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}

export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
