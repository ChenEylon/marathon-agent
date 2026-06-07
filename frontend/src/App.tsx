import { useState, useEffect, useRef } from 'react'
import {
  Zap, Layers, MessageCircle, ArrowUp, Bot, Inbox,
} from 'lucide-react'
import './App.css'

interface Msg {
  id: number
  role: string
  content: string
  created_at: string
}

function urlBase64ToUint8Array(b64: string) {
  const padding = '='.repeat((4 - (b64.length % 4)) % 4)
  const base64 = (b64 + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)))
}

async function registerPush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return
  const reg = await navigator.serviceWorker.register('/sw.js')
  const res = await fetch('/api/vapid-public-key')
  const { key } = await res.json()
  if (!key) return
  const existing = await reg.pushManager.getSubscription()
  const sub = existing ?? await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(key),
  })
  await fetch('/api/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subscription: sub }),
  })
}

function fmtTime(iso: string) {
  return new Date(iso.endsWith('Z') ? iso : iso + 'Z')
    .toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function fmtDate(iso: string) {
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z')
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)
  if (d.toDateString() === today.toDateString()) return 'Today'
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday'
  return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })
}

function MessageFeed() {
  const [messages, setMessages] = useState<Msg[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const load = () =>
      fetch('/api/messages').then(r => r.json()).then(setMessages).catch(() => {})
    load()
    const id = setInterval(load, 10_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView()
  }, [messages])

  let lastDate = ''

  return (
    <div className="feed">
      {messages.length === 0 ? (
        <div className="empty-state">
          <Inbox size={40} strokeWidth={1.25} className="empty-icon" />
          <p>Your coach will check in here each morning.</p>
        </div>
      ) : (
        messages.map(m => {
          const date = fmtDate(m.created_at)
          const showDate = date !== lastDate
          lastDate = date
          return (
            <div key={m.id} className="bubble-group">
              {showDate && <div className="date-sep"><span>{date}</span></div>}
              <div className={`bubble-row ${m.role === 'user' ? 'row-user' : 'row-agent'}`}>
                {m.role !== 'user' && (
                  <div className="avatar"><Bot size={13} strokeWidth={2} /></div>
                )}
                <div className={`bubble ${m.role === 'user' ? 'bubble-user' : 'bubble-agent'}`}>
                  <p>{m.content}</p>
                  <span className="ts">{fmtTime(m.created_at)}</span>
                </div>
              </div>
            </div>
          )
        })
      )}
      <div ref={bottomRef} />
    </div>
  )
}

function ChatView() {
  const [history, setHistory] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetch('/api/chat/history').then(r => r.json()).then(setHistory).catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, loading])

  const send = async () => {
    const msg = input.trim()
    if (!msg || loading) return
    setInput('')
    inputRef.current?.focus()
    const userMsg: Msg = { id: Date.now(), role: 'user', content: msg, created_at: new Date().toISOString() }
    setHistory(h => [...h, userMsg])
    setLoading(true)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      })
      const { reply } = await res.json()
      setHistory(h => [...h, {
        id: Date.now() + 1,
        role: 'assistant',
        content: reply,
        created_at: new Date().toISOString(),
      }])
    } catch {
      setHistory(h => [...h, {
        id: Date.now() + 1,
        role: 'assistant',
        content: "Couldn't reach the coach right now. Try again in a moment.",
        created_at: new Date().toISOString(),
      }])
    }
    setLoading(false)
  }

  return (
    <div className="chat-wrap">
      <div className="chat-history">
        {history.length === 0 && !loading ? (
          <div className="empty-state">
            <MessageCircle size={40} strokeWidth={1.25} className="empty-icon" />
            <p>Ask your coach anything about training, recovery, or your plan.</p>
          </div>
        ) : (
          history.map(m => (
            <div key={m.id} className={`bubble-row ${m.role === 'user' ? 'row-user' : 'row-agent'}`}>
              {m.role !== 'user' && (
                <div className="avatar"><Bot size={13} strokeWidth={2} /></div>
              )}
              <div className={`bubble ${m.role === 'user' ? 'bubble-user' : 'bubble-agent'}`}>
                <p>{m.content}</p>
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="bubble-row row-agent">
            <div className="avatar"><Bot size={13} strokeWidth={2} /></div>
            <div className="bubble bubble-agent typing-bubble">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="input-row">
        <input
          ref={inputRef}
          className="chat-input"
          placeholder="Ask your coach..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          disabled={loading}
        />
        <button
          className="send-btn"
          onClick={send}
          disabled={loading || !input.trim()}
          aria-label="Send"
        >
          <ArrowUp size={18} strokeWidth={2.5} />
        </button>
      </div>
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState<'messages' | 'chat'>('messages')

  useEffect(() => {
    Notification.requestPermission().then(() => registerPush()).catch(() => {})
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-logo">
          <Zap size={20} strokeWidth={2.5} className="header-icon" />
          <span className="header-title">MARATHON</span>
        </div>
        <span className="header-sub">Coach</span>
      </header>

      <nav className="tabs">
        <button
          className={`tab ${tab === 'messages' ? 'tab-active' : ''}`}
          onClick={() => setTab('messages')}
        >
          <Layers size={15} strokeWidth={2} />
          Messages
        </button>
        <button
          className={`tab ${tab === 'chat' ? 'tab-active' : ''}`}
          onClick={() => setTab('chat')}
        >
          <MessageCircle size={15} strokeWidth={2} />
          Chat
        </button>
      </nav>

      <main className="main">
        {tab === 'messages' ? <MessageFeed /> : <ChatView />}
      </main>
    </div>
  )
}
