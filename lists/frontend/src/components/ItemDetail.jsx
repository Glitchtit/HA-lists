import { useEffect, useState } from 'react'
import * as api from '../api'

export default function ItemDetail({ itemId, persons, onChange, onClose }) {
  const [item, setItem] = useState(null)
  const [subtasks, setSubtasks] = useState([])
  const [newSub, setNewSub] = useState('')
  const [newTag, setNewTag] = useState('')

  useEffect(() => {
    if (!itemId) { setItem(null); setSubtasks([]); return }
    let active = true
    Promise.all([api.getItem(itemId), api.getSubtasks(itemId)]).then(([i, s]) => {
      if (!active) return
      setItem(i)
      setSubtasks(s)
    })
    return () => { active = false }
  }, [itemId])

  if (!itemId || !item) {
    return (
      <aside className="hidden lg:flex w-96 border-l border-gray-700 items-center justify-center text-gray-500">
        Select an item to see details.
      </aside>
    )
  }

  async function patch(fields) {
    const next = await api.updateItem(item.id, fields)
    setItem({ ...item, ...next })
    onChange?.()
  }

  async function addSubtask(e) {
    e.preventDefault()
    if (!newSub.trim()) return
    await api.createSubtask({ item_id: item.id, title: newSub.trim() })
    setNewSub('')
    setSubtasks(await api.getSubtasks(item.id))
  }

  async function toggleSub(st) {
    await api.toggleSubtask(st.id)
    setSubtasks(await api.getSubtasks(item.id))
  }

  async function addTag(e) {
    e.preventDefault()
    if (!newTag.trim()) return
    const next = await api.attachTag(item.id, newTag.trim())
    setItem({ ...item, tags: next.tags })
    setNewTag('')
    onChange?.()
  }

  async function removeTag(name) {
    const next = await api.detachTag(item.id, name)
    setItem({ ...item, tags: next.tags })
    onChange?.()
  }

  return (
    <aside className="w-full lg:w-96 bg-gray-900 border-l border-gray-700 overflow-y-auto">
      <div className="p-4 border-b border-gray-700 flex items-start gap-2">
        <input
          value={item.title}
          onChange={e => setItem({ ...item, title: e.target.value })}
          onBlur={() => patch({ title: item.title })}
          className="flex-1 bg-transparent text-lg font-semibold outline-none"
        />
        {onClose && (
          <button onClick={onClose} className="text-gray-500 hover:text-white lg:hidden">✕</button>
        )}
      </div>

      <div className="p-4 space-y-4">
        <label className="block">
          <span className="text-xs uppercase text-gray-400">Notes</span>
          <textarea
            value={item.notes || ''}
            onChange={e => setItem({ ...item, notes: e.target.value })}
            onBlur={() => patch({ notes: item.notes })}
            rows={4}
            className="mt-1 w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-sm"
          />
        </label>

        <label className="block">
          <span className="text-xs uppercase text-gray-400">
            Spiciness {'🌶️'.repeat(item.spiciness)}
          </span>
          <input
            type="range"
            min={1}
            max={5}
            value={item.spiciness}
            onChange={e => setItem({ ...item, spiciness: Number(e.target.value) })}
            onMouseUp={() => patch({ spiciness: item.spiciness })}
            onTouchEnd={() => patch({ spiciness: item.spiciness })}
            className="w-full"
          />
        </label>

        <label className="block">
          <span className="text-xs uppercase text-gray-400">Assigned to</span>
          <select
            value={item.assigned_to || ''}
            onChange={e => patch({ assigned_to: e.target.value || null })}
            className="mt-1 w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-sm"
          >
            <option value="">— Anyone —</option>
            {persons.map(p => (
              <option key={p.entity_id} value={p.entity_id}>{p.name}</option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-xs uppercase text-gray-400">Due</span>
          <input
            type="datetime-local"
            value={item.due_at ? item.due_at.slice(0, 16) : ''}
            onChange={e => patch({ due_at: e.target.value || null })}
            className="mt-1 w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-sm"
          />
        </label>

        <div>
          <span className="text-xs uppercase text-gray-400">Tags</span>
          <div className="flex flex-wrap gap-1 mt-1 mb-2">
            {(item.tags || []).map(t => (
              <span
                key={t}
                className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-800 border border-gray-700 rounded text-xs"
              >
                #{t}
                <button onClick={() => removeTag(t)} className="text-gray-500 hover:text-white">×</button>
              </span>
            ))}
          </div>
          <form onSubmit={addTag} className="flex gap-1">
            <input
              value={newTag}
              onChange={e => setNewTag(e.target.value)}
              placeholder="new tag"
              className="flex-1 px-2 py-1 text-sm bg-gray-800 border border-gray-700 rounded"
            />
            <button className="px-2 text-sm bg-gray-700 rounded hover:bg-gray-600">Add</button>
          </form>
        </div>

        <div>
          <span className="text-xs uppercase text-gray-400">Subtasks</span>
          <ul className="mt-1 space-y-1">
            {subtasks.map(st => (
              <li key={st.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={st.status === 'completed'}
                  onChange={() => toggleSub(st)}
                />
                <span className={st.status === 'completed' ? 'line-through text-gray-500' : ''}>
                  {st.title}
                </span>
                {st.ai_generated && <span title="AI-generated" className="text-xs text-purple-400">✨</span>}
              </li>
            ))}
          </ul>
          <form onSubmit={addSubtask} className="flex gap-1 mt-2">
            <input
              value={newSub}
              onChange={e => setNewSub(e.target.value)}
              placeholder="Add subtask…"
              className="flex-1 px-2 py-1 text-sm bg-gray-800 border border-gray-700 rounded"
            />
            <button className="px-2 text-sm bg-gray-700 rounded hover:bg-gray-600">Add</button>
          </form>
        </div>
      </div>
    </aside>
  )
}
