import { useEffect, useRef, useState } from 'react'
import * as api from '../api'

/** Poll an AI job by task_id; returns { status, logs, result, error }. */
export default function AiJobToast({ taskId, label, onDone, onDismiss }) {
  const [job, setJob] = useState({ status: 'running', logs: [] })
  const intervalRef = useRef(null)

  useEffect(() => {
    if (!taskId) return
    let alive = true
    const tick = async () => {
      try {
        const j = await api.getAiJob(taskId)
        if (!alive) return
        setJob(j)
        if (j.status === 'done' && onDone) onDone(j)
        if (j.status === 'done' || j.status === 'error') {
          clearInterval(intervalRef.current)
        }
      } catch (e) {
        if (!alive) return
        setJob(prev => ({ ...prev, status: 'error', error: e.message }))
        clearInterval(intervalRef.current)
      }
    }
    tick()
    intervalRef.current = setInterval(tick, 800)
    return () => {
      alive = false
      clearInterval(intervalRef.current)
    }
  }, [taskId])

  const bg =
    job.status === 'error' ? 'bg-[rgba(239,68,68,0.18)] border-red-700'
    : job.status === 'done' ? 'bg-[rgba(16,185,129,0.18)] border-semantic-success'
    : 'bg-brand-cobalt-600 border-brand-orange'

  return (
    <div className={`fixed bottom-4 right-4 w-80 max-w-[90vw] rounded-2xl border ${bg} text-white shadow-xl overflow-hidden animate-slide-up`}>
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/10">
        <span className="text-sm font-medium flex items-center gap-2">
          {job.status === 'running' && <span className="animate-spin">✨</span>}
          {job.status === 'done' && <span>✅</span>}
          {job.status === 'error' && <span>⚠️</span>}
          {label || 'AI job'}
        </span>
        <button onClick={onDismiss} className="text-white/60 hover:text-white text-sm">✕</button>
      </div>
      {job.logs?.length > 0 && (
        <div className="px-3 py-2 max-h-32 overflow-y-auto text-xs font-mono text-white/80">
          {job.logs.map((l, i) => <div key={i}>{l}</div>)}
        </div>
      )}
      {job.status === 'error' && job.error && (
        <div className="px-3 py-2 text-xs text-semantic-danger">{job.error}</div>
      )}
    </div>
  )
}
