import { useState, useEffect, useRef } from 'react'
import {
  Zap, Layers, MessageCircle, ArrowUp, Bot, Inbox,
  CalendarDays, Wind, Navigation, BarChart2, Trophy, Dumbbell,
  CheckCircle, Circle,
} from 'lucide-react'
import './App.css'

// ── Types ─────────────────────────────────────────────────────────────────────
interface Msg        { id: number; role: string; content: string; created_at: string }
interface Workout    { day_of_week: string; workout_type: string; distance_km: number; pace_target: string; description: string; phase: number }
interface Week       { week_number: number; is_current: boolean; phase: number; phase_name: string; workouts: Workout[] }
interface PlanData   { current_week: number; total_weeks: number; plan_start: string; weeks: Week[] }
interface Activity   { strava_id: number; date: string; distance_km: number; pace_sec_km: number; avg_hr: number | null }
interface WeekStat   { week: number; planned_km: number; actual_km: number }
interface FeedbackMap{ [date: string]: number }

// ── Push registration ─────────────────────────────────────────────────────────
function urlBase64ToUint8Array(b64: string) {
  const padding = '='.repeat((4 - (b64.length % 4)) % 4)
  const base64  = (b64 + padding).replace(/-/g, '+').replace(/_/g, '/')
  return Uint8Array.from([...atob(base64)].map(c => c.charCodeAt(0)))
}
async function registerPush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return
  const reg = await navigator.serviceWorker.register('/sw.js')
  const { key } = await fetch('/api/vapid-public-key').then(r => r.json())
  if (!key) return
  const sub = (await reg.pushManager.getSubscription()) ??
    await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(key) })
  await fetch('/api/subscribe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ subscription: sub }) })
}

// ── Utils ─────────────────────────────────────────────────────────────────────
function fmtTime(iso: string) {
  return new Date(iso.endsWith('Z') ? iso : iso + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
function fmtDate(iso: string) {
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z')
  const today = new Date(); const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1)
  if (d.toDateString() === today.toDateString()) return 'Today'
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday'
  return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })
}
function fmtPace(secPerKm: number): string {
  const m = Math.floor(secPerKm / 60)
  const s = Math.round(secPerKm % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}
function daysToRace(): number {
  return Math.ceil((new Date('2027-02-27').getTime() - Date.now()) / 86_400_000)
}
function workoutDate(planStart: string, weekNum: number, dayOfWeek: string): string {
  const offsets: Record<string, number> = { monday:0,tuesday:1,wednesday:2,thursday:3,friday:4,saturday:5,sunday:6 }
  const d = new Date(planStart + 'T12:00:00')
  d.setDate(d.getDate() + (weekNum - 1) * 7 + (offsets[dayOfWeek] ?? 0))
  return d.toISOString().slice(0, 10)
}

// ── Icon / label maps ─────────────────────────────────────────────────────────
type IconFC = React.FC<{ size: number; strokeWidth: number }>
const WORKOUT_META: Record<string, { label: string; Icon: IconFC }> = {
  easy:      { label: 'Easy Run',  Icon: p => <Wind      {...p} /> },
  long:      { label: 'Long Run',  Icon: p => <Navigation {...p} /> },
  tempo:     { label: 'Tempo',     Icon: p => <Zap       {...p} /> },
  intervals: { label: 'Intervals', Icon: p => <BarChart2  {...p} /> },
  race:      { label: 'Race',      Icon: p => <Trophy     {...p} /> },
  strength:  { label: 'Strength',  Icon: p => <Dumbbell   {...p} /> },
}
const DAY_SHORT: Record<string, string> = {
  monday:'Mon',tuesday:'Tue',wednesday:'Wed',thursday:'Thu',friday:'Fri',saturday:'Sat',sunday:'Sun',
}
const FEELING_COLORS = ['','#EF4444','#F97316','#EAB308','#84CC16','#22C55E']

// ── Message Feed ──────────────────────────────────────────────────────────────
function MessageFeed() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput]       = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const load = () => fetch('/api/messages').then(r => r.json()).then(setMessages).catch(() => {})
    load(); const id = setInterval(load, 10_000); return () => clearInterval(id)
  }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView() }, [messages])

  const sendReply = async () => {
    const body = input.trim(); if (!body) return
    setInput('')
    await fetch('/api/reply', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ body }) }).catch(() => {})
  }

  let lastDate = ''
  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex-1 overflow-y-auto px-4 py-5 flex flex-col gap-1" style={{ background: 'var(--bg)' }}>
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 py-20 text-center">
            <Inbox size={40} strokeWidth={1.25} style={{ color: 'var(--border)' }} />
            <p className="text-sm max-w-[200px] leading-relaxed" style={{ color: 'var(--muted)' }}>Your coach will check in here each morning.</p>
          </div>
        ) : messages.map(m => {
          const date = fmtDate(m.created_at); const showDate = date !== lastDate; lastDate = date
          const isUser = m.role === 'user'
          return (
            <div key={m.id} className="flex flex-col gap-1">
              {showDate && (
                <div className="flex items-center gap-2 my-3">
                  <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
                  <span className="text-[11px] font-medium tracking-wide" style={{ color: 'var(--muted)' }}>{date}</span>
                  <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
                </div>
              )}
              <div className={`bubble-row flex items-end gap-2 ${isUser ? 'flex-row-reverse self-end max-w-[82%]' : 'self-start max-w-[88%]'}`}>
                {!isUser && (
                  <div className="w-[26px] h-[26px] rounded-full flex items-center justify-center flex-shrink-0 border"
                    style={{ background: 'var(--bg)', borderColor: 'var(--border)', color: 'var(--muted)' }}>
                    <Bot size={13} strokeWidth={2} />
                  </div>
                )}
                <div className={`flex flex-col px-[14px] py-[10px] rounded-[18px] text-[14.5px] leading-[1.55] shadow-sm
                  ${isUser ? 'rounded-br-[5px] text-white' : 'rounded-bl-[5px] border'}`}
                  style={isUser ? { background: 'var(--user-bg)' } : { background: 'var(--surface)', borderColor: 'var(--border)', color: 'var(--text)' }}>
                  <p className="m-0 whitespace-pre-wrap break-words">{m.content}</p>
                  <span className="text-[10.5px] mt-1 self-end"
                    style={{ color: isUser ? 'rgba(255,255,255,0.45)' : 'var(--muted)' }}>{fmtTime(m.created_at)}</span>
                </div>
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>

      {/* Reply bar */}
      <div className="flex items-center gap-2 px-4 py-3 border-t flex-shrink-0"
        style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
        <input
          className="flex-1 px-4 py-[10px] rounded-full text-[14.5px] border outline-none"
          style={{ background: 'var(--bg)', borderColor: 'var(--border)', color: 'var(--text)', fontFamily: 'inherit' }}
          placeholder="Reply to coach..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendReply()}
          onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
          onBlur={e  => (e.target.style.borderColor = 'var(--border)')}
        />
        <button
          className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 text-white transition-transform active:scale-90 disabled:opacity-30"
          style={{ background: 'var(--accent)' }}
          onClick={sendReply}
          disabled={!input.trim()}
          aria-label="Send"
        >
          <ArrowUp size={18} strokeWidth={2.5} />
        </button>
      </div>
    </div>
  )
}

// ── Chat ──────────────────────────────────────────────────────────────────────
function ChatView() {
  const [history, setHistory] = useState<Msg[]>([])
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef  = useRef<HTMLInputElement>(null)

  useEffect(() => { fetch('/api/chat/history').then(r => r.json()).then(setHistory).catch(() => {}) }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [history, loading])

  const send = async () => {
    const msg = input.trim(); if (!msg || loading) return
    setInput(''); inputRef.current?.focus()
    setHistory(h => [...h, { id: Date.now(), role: 'user', content: msg, created_at: new Date().toISOString() }])
    setLoading(true)
    try {
      const { reply } = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: msg }) }).then(r => r.json())
      setHistory(h => [...h, { id: Date.now() + 1, role: 'assistant', content: reply, created_at: new Date().toISOString() }])
    } catch {
      setHistory(h => [...h, { id: Date.now() + 1, role: 'assistant', content: "Couldn't reach the coach right now.", created_at: new Date().toISOString() }])
    }
    setLoading(false)
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex-1 overflow-y-auto px-4 py-5 flex flex-col gap-1" style={{ background: 'var(--bg)' }}>
        {history.length === 0 && !loading ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 py-20 text-center">
            <MessageCircle size={40} strokeWidth={1.25} style={{ color: 'var(--border)' }} />
            <p className="text-sm max-w-[200px] leading-relaxed" style={{ color: 'var(--muted)' }}>Ask your coach anything about training, recovery, or your plan.</p>
          </div>
        ) : history.map(m => {
          const isUser = m.role === 'user'
          return (
            <div key={m.id} className={`bubble-row flex items-end gap-2 ${isUser ? 'flex-row-reverse self-end max-w-[82%]' : 'self-start max-w-[88%]'}`}>
              {!isUser && (
                <div className="w-[26px] h-[26px] rounded-full flex items-center justify-center flex-shrink-0 border"
                  style={{ background: 'var(--bg)', borderColor: 'var(--border)', color: 'var(--muted)' }}>
                  <Bot size={13} strokeWidth={2} />
                </div>
              )}
              <div className={`px-[14px] py-[10px] rounded-[18px] text-[14.5px] leading-[1.55]
                ${isUser ? 'rounded-br-[5px] text-white' : 'rounded-bl-[5px] border shadow-sm'}`}
                style={isUser ? { background: 'var(--user-bg)' } : { background: 'var(--surface)', borderColor: 'var(--border)', color: 'var(--text)' }}>
                <p className="m-0 whitespace-pre-wrap break-words">{m.content}</p>
              </div>
            </div>
          )
        })}
        {loading && (
          <div className="bubble-row flex items-end gap-2 self-start">
            <div className="w-[26px] h-[26px] rounded-full flex items-center justify-center border"
              style={{ background: 'var(--bg)', borderColor: 'var(--border)', color: 'var(--muted)' }}>
              <Bot size={13} strokeWidth={2} />
            </div>
            <div className="border rounded-[18px] rounded-bl-[5px] shadow-sm typing-bubble"
              style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex items-center gap-2 px-4 py-3 border-t flex-shrink-0"
        style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
        <input
          ref={inputRef}
          className="flex-1 px-4 py-[10px] rounded-full text-[14.5px] border outline-none transition-colors"
          style={{ background: 'var(--bg)', borderColor: 'var(--border)', color: 'var(--text)', fontFamily: 'inherit' }}
          placeholder="Ask your coach..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          disabled={loading}
          onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
          onBlur={e  => (e.target.style.borderColor = 'var(--border)')}
        />
        <button
          className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 text-white transition-transform active:scale-90 disabled:opacity-30 disabled:cursor-not-allowed"
          style={{ background: 'var(--accent)' }}
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

// ── Weekly Mileage Chart ──────────────────────────────────────────────────────
function WeeklyChart({ stats }: { stats: WeekStat[] }) {
  if (!stats.length) return null
  const maxKm = Math.max(...stats.map(s => s.planned_km), 1)
  return (
    <div className="rounded-xl border p-4 flex-shrink-0" style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
      <div className="flex justify-between items-baseline mb-3">
        <span className="text-xs font-semibold tracking-wide uppercase" style={{ color: 'var(--muted)' }}>Weekly km</span>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2 rounded-sm opacity-25" style={{ background: 'var(--accent)' }} />
            <span className="text-[10px]" style={{ color: 'var(--muted)' }}>Plan</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2 rounded-sm" style={{ background: 'var(--accent)' }} />
            <span className="text-[10px]" style={{ color: 'var(--muted)' }}>Done</span>
          </span>
        </div>
      </div>
      <div className="flex items-end gap-1.5" style={{ height: '72px' }}>
        {stats.map(s => (
          <div key={s.week} className="flex-1 flex flex-col items-center gap-1 h-full">
            <div className="flex-1 w-full relative">
              <div className="absolute bottom-0 left-0 right-0 rounded-t-sm opacity-25"
                style={{ height: `${(s.planned_km / maxKm) * 100}%`, background: 'var(--accent)' }} />
              {s.actual_km > 0 && (
                <div className="absolute bottom-0 left-0 right-0 rounded-t-sm"
                  style={{ height: `${Math.min(s.actual_km / maxKm, 1) * 100}%`, background: 'var(--accent)' }} />
              )}
            </div>
            <span className="text-[9px] leading-none" style={{ color: 'var(--muted)' }}>W{s.week}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Recent Runs ───────────────────────────────────────────────────────────────
function RecentRuns({ activities }: { activities: Activity[] }) {
  if (!activities.length) return null
  return (
    <div className="rounded-xl border overflow-hidden flex-shrink-0" style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
      <div className="px-4 py-3 border-b flex items-center gap-2" style={{ borderColor: 'var(--border)' }}>
        <Navigation size={13} strokeWidth={2} style={{ color: 'var(--muted)' }} />
        <span className="text-xs font-semibold tracking-wide uppercase" style={{ color: 'var(--muted)' }}>Recent Runs</span>
      </div>
      <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
        {activities.map(a => (
          <div key={a.strava_id} className="flex items-center gap-3 px-4 py-3">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 workout-easy">
              <Navigation size={15} strokeWidth={2} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline justify-between">
                <span className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{a.distance_km.toFixed(1)} km</span>
                <span className="text-xs" style={{ color: 'var(--muted)' }}>{fmtDate(a.date)}</span>
              </div>
              <span className="text-xs" style={{ color: 'var(--muted)' }}>
                {fmtPace(a.pace_sec_km)} /km{a.avg_hr ? ` · ${Math.round(a.avg_hr)} bpm` : ''}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Plan ──────────────────────────────────────────────────────────────────────
function PlanView() {
  const [plan, setPlan]         = useState<PlanData | null>(null)
  const [activities, setActs]   = useState<Activity[]>([])
  const [weekStats, setStats]   = useState<WeekStat[]>([])
  const [feedback, setFeedback] = useState<FeedbackMap>({})
  const [rating, setRating]     = useState<string | null>(null) // workout date being rated

  useEffect(() => {
    fetch('/api/plan').then(r => r.json()).then(setPlan).catch(() => {})
    fetch('/api/activities').then(r => r.json()).then(setActs).catch(() => {})
    fetch('/api/weekly-stats').then(r => r.json()).then((d: { weeks: WeekStat[] }) => setStats(d.weeks)).catch(() => {})
  }, [])

  useEffect(() => {
    if (!plan) return
    fetch(`/api/feedback?week=${plan.current_week}`)
      .then(r => r.json())
      .then((items: { date: string; feeling: number }[]) => {
        const m: FeedbackMap = {}
        items.forEach(i => { m[i.date] = i.feeling })
        setFeedback(m)
      }).catch(() => {})
  }, [plan])

  const saveFeedback = async (date: string, feeling: number) => {
    setFeedback(f => ({ ...f, [date]: feeling }))
    setRating(null)
    await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date, feeling }),
    }).catch(() => {})
  }

  if (!plan) return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3 py-20 text-center" style={{ background: 'var(--bg)' }}>
      <CalendarDays size={40} strokeWidth={1.25} style={{ color: 'var(--border)' }} />
      <p className="text-sm" style={{ color: 'var(--muted)' }}>Loading your plan...</p>
    </div>
  )

  const pct  = Math.round((plan.current_week / plan.total_weeks) * 100)
  const days = daysToRace()

  return (
    <div className="flex-1 overflow-y-auto px-4 py-5 flex flex-col gap-4" style={{ background: 'var(--bg)' }}>

      {/* Race countdown */}
      <div className="rounded-xl border flex-shrink-0 flex items-center gap-4 px-4 py-3"
        style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
        <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'rgba(240,90,40,0.10)' }}>
          <Trophy size={20} strokeWidth={1.75} style={{ color: 'var(--accent)' }} />
        </div>
        <div>
          <p className="text-[22px] font-bold leading-none" style={{ color: 'var(--text)' }}>{days} days</p>
          <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>to race day · Feb 27, 2027</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="rounded-xl p-4 border flex-shrink-0" style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
        <div className="flex justify-between items-baseline mb-2">
          <span className="text-xs font-semibold tracking-wide uppercase" style={{ color: 'var(--muted)' }}>Marathon Progress</span>
          <span className="text-xs font-medium" style={{ color: 'var(--muted)' }}>Week {plan.current_week} of {plan.total_weeks}</span>
        </div>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
          <div className="h-full rounded-full plan-progress-fill" style={{ width: `${pct}%`, background: 'var(--accent)' }} />
        </div>
        <p className="text-xs mt-1.5" style={{ color: 'var(--muted)' }}>{pct}% complete · {plan.total_weeks - plan.current_week} weeks to race day</p>
      </div>

      {/* Weekly mileage chart */}
      <WeeklyChart stats={weekStats} />

      {/* Recent runs */}
      <RecentRuns activities={activities} />

      {/* Week cards */}
      {plan.weeks.map(week => (
        <div key={week.week_number}
          className={`rounded-xl border overflow-hidden flex-shrink-0 ${week.is_current ? 'ring-2' : ''}`}
          style={{ background: 'var(--surface)', borderColor: week.is_current ? 'var(--accent)' : 'var(--border)' }}>

          <div className="flex items-center justify-between px-4 py-3 border-b"
            style={{ borderColor: 'var(--border)', background: week.is_current ? 'rgba(240,90,40,0.06)' : 'transparent' }}>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm" style={{ color: 'var(--text)' }}>Week {week.week_number}</span>
              {week.is_current && (
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full text-white" style={{ background: 'var(--accent)' }}>
                  Now
                </span>
              )}
            </div>
            <span className="text-xs font-medium" style={{ color: 'var(--muted)' }}>{week.phase_name}</span>
          </div>

          <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
            {week.workouts.map(wo => {
              const { label, Icon } = WORKOUT_META[wo.workout_type] ?? { label: wo.workout_type, Icon: (p: { size: number; strokeWidth: number }) => <Wind {...p} /> }
              const wDate          = plan.plan_start ? workoutDate(plan.plan_start, week.week_number, wo.day_of_week) : null
              const existingRating = wDate ? feedback[wDate] : null
              const isRating       = rating === wDate
              const isPastOrToday  = wDate ? wDate <= new Date().toISOString().slice(0, 10) : false

              return (
                <div key={wo.day_of_week}>
                  <div className="flex items-start gap-3 px-4 py-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 workout-${wo.workout_type}`}>
                      <Icon size={14} strokeWidth={2} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>{DAY_SHORT[wo.day_of_week] ?? wo.day_of_week}</span>
                        <span className="text-sm font-medium" style={{ color: 'var(--text)' }}>{label}</span>
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{wo.distance_km} km</span>
                        <span className="text-xs" style={{ color: 'var(--border)' }}>·</span>
                        <span className="text-xs" style={{ color: 'var(--muted)' }}>{wo.pace_target} /km</span>
                      </div>
                      {week.is_current && (
                        <p className="text-xs mt-1 leading-relaxed" style={{ color: 'var(--muted)' }}>{wo.description}</p>
                      )}
                    </div>

                    {/* Check-off button (current week, past or today) */}
                    {week.is_current && isPastOrToday && wDate && (
                      existingRating ? (
                        <div className="flex items-center gap-1 flex-shrink-0 mt-1">
                          <CheckCircle size={15} strokeWidth={2} style={{ color: FEELING_COLORS[existingRating] }} />
                          <span className="text-[11px] font-semibold" style={{ color: FEELING_COLORS[existingRating] }}>{existingRating}</span>
                        </div>
                      ) : (
                        <button
                          className="flex-shrink-0 mt-1 transition-opacity active:opacity-50"
                          onClick={() => setRating(isRating ? null : wDate)}
                          title="Rate this workout"
                        >
                          <Circle size={15} strokeWidth={1.5} style={{ color: 'var(--border)' }} />
                        </button>
                      )
                    )}
                  </div>

                  {/* Feeling picker */}
                  {isRating && wDate && (
                    <div className="px-4 pb-3 flex items-center gap-2">
                      <span className="text-xs flex-shrink-0" style={{ color: 'var(--muted)' }}>How was it?</span>
                      <div className="flex gap-1.5 ml-1">
                        {[1, 2, 3, 4, 5].map(n => (
                          <button key={n}
                            className="w-8 h-8 rounded-lg text-[13px] font-bold text-white transition-transform active:scale-90"
                            style={{ background: FEELING_COLORS[n] }}
                            onClick={() => saveFeedback(wDate, n)}>
                            {n}
                          </button>
                        ))}
                      </div>
                      <button className="text-xs ml-1 flex-shrink-0" style={{ color: 'var(--muted)' }}
                        onClick={() => setRating(null)}>cancel</button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── App shell ─────────────────────────────────────────────────────────────────
type Tab = 'messages' | 'plan' | 'chat'

export default function App() {
  const [tab, setTab] = useState<Tab>('messages')

  useEffect(() => {
    try {
      if (typeof Notification !== 'undefined') {
        Notification.requestPermission().then(() => registerPush()).catch(() => {})
      }
    } catch { /* push not supported on this browser */ }
  }, [])

  const days = daysToRace()

  return (
    <div className="flex flex-col h-screen max-w-[480px] mx-auto sm:my-8 sm:h-[calc(100vh-64px)] sm:rounded-2xl sm:overflow-hidden sm:shadow-xl">

      {/* Header */}
      <header className="app-header flex items-center justify-between px-5 py-4 flex-shrink-0"
        style={{ background: 'var(--header-bg)' }}>
        <div className="flex items-center gap-2">
          <Zap size={20} strokeWidth={2.5} style={{ color: 'var(--accent)' }} />
          <span className="text-[15px] font-bold tracking-[0.12em] text-white">MARATHON</span>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-[11px] font-medium tracking-[0.06em] uppercase" style={{ color: '#6B6460' }}>Coach</span>
          <span className="text-[11px] font-semibold" style={{ color: 'var(--accent)' }}>{days}d to race</span>
        </div>
      </header>

      {/* Tabs */}
      <nav className="tabs flex border-b flex-shrink-0" style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
        {([
          ['messages', 'Messages', <Layers size={15} strokeWidth={2} />],
          ['plan',     'Plan',     <CalendarDays size={15} strokeWidth={2} />],
          ['chat',     'Chat',     <MessageCircle size={15} strokeWidth={2} />],
        ] as const).map(([id, label, icon]) => (
          <button
            key={id}
            className={`flex flex-1 items-center justify-center gap-1.5 py-[13px] text-[13px] font-medium border-b-2 -mb-px transition-colors`}
            style={{
              color:        tab === id ? 'var(--accent)' : 'var(--muted)',
              borderColor:  tab === id ? 'var(--accent)' : 'transparent',
              background:   'none',
              fontFamily:   'inherit',
              cursor:       'pointer',
            }}
            onClick={() => setTab(id)}
          >
            {icon}{label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="main flex-1 overflow-hidden flex flex-col min-h-0">
        {tab === 'messages' && <MessageFeed />}
        {tab === 'plan'     && <PlanView />}
        {tab === 'chat'     && <ChatView />}
      </main>
    </div>
  )
}
