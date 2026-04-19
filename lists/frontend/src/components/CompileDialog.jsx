import { useState } from 'react'
import * as api from '../api'
import AiJobToast from './AiJobToast'

export default function CompileDialog({ listId, listName, onClose, onRefresh }) {
  const [text, setText] = useState('')
  const [taskId, setTaskId] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function submit(e) {
    e.preventDefault()
    if (!text.trim() || busy) return
    setBusy(true)
    setError(null)
    try {
      const { task_id } = await api.aiCompile(listId, text.trim())
      setTaskId(task_id)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
      setBusy(false)
    }
  }

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/60 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <div
          className="w-full max-w-lg bg-gray-900 border border-gray-700 rounded-xl shadow-2xl"
          onClick={e => e.stopPropagation()}
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
            <h2 className="text-base font-semibold flex items-center gap-2">
              ✨ Compile brain-dump → {listName || 'list'}
            </h2>
            <button onClick={onClose} className="text-gray-500 hover:text-white">✕</button>
          </div>

          <form onSubmit={submit} className="p-4 space-y-3">
            <textarea
              autoFocus
              value={text}
              onChange={e => setText(e.target.value)}
              placeholder="Dump everything on your mind — the AI will turn it into a clean list of items."
              rows={8}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm resize-y"
              disabled={busy}
            />
            {error && <div className="text-sm text-red-400">{error}</div>}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 text-sm bg-gray-700 rounded hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!text.trim() || busy}
                className="px-3 py-1.5 text-sm bg-purple-700 rounded hover:bg-purple-600 disabled:opacity-50"
              >
                {busy ? 'Compiling…' : 'Compile'}
              </button>
            </div>
          </form>
        </div>
      </div>

      {taskId && (
        <AiJobToast
          taskId={taskId}
          label="Compiling brain-dump"
          onDone={() => { onRefresh?.(); onClose() }}
          onDismiss={() => setTaskId(null)}
        />
      )}
    </>
  )
}
