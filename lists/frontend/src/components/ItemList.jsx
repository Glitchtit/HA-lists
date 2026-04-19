import { useState } from 'react'
import * as api from '../api'

export default function ItemList({ list, items, activeItemId, onSelectItem, onRefresh, onCompile }) {
  const [newTitle, setNewTitle] = useState('')
  const [showCompleted, setShowCompleted] = useState(false)

  async function addItem(e) {
    e.preventDefault()
    if (!newTitle.trim() || !list) return
    await api.createItem({ list_id: list.id, title: newTitle.trim() })
    setNewTitle('')
    onRefresh()
  }

  async function toggle(item) {
    if (item.status === 'completed') await api.reopenItem(item.id)
    else await api.completeItem(item.id)
    onRefresh()
  }

  if (!list) {
    return (
      <div className="flex-1 flex items-center justify-center text-ink-4">
        Pick a list on the left, or create one.
      </div>
    )
  }

  const visible = showCompleted ? items : items.filter(i => i.status !== 'completed')

  return (
    <section className="flex-1 flex flex-col border-r border-line-1 min-w-0">
      <header className="p-4 border-b border-line-1 flex items-center justify-between gap-2 bg-surface-1/80 backdrop-blur-md">
        <h2 className="text-lg font-semibold truncate font-display tracking-tight">
          {list.icon || '📝'} {list.name}
        </h2>
        <div className="flex items-center gap-2">
          {onCompile && (
            <button
              onClick={onCompile}
              className="px-2 py-1 text-xs bg-brand-orange rounded hover:bg-brand-orange-400"
              title="Brain-dump → items (AI compile)"
            >
              ✨ Compile
            </button>
          )}
          <label className="text-xs text-ink-3 flex items-center gap-1">
            <input
              type="checkbox"
              checked={showCompleted}
              onChange={e => setShowCompleted(e.target.checked)}
            />
            Show completed
          </label>
        </div>
      </header>

      <form onSubmit={addItem} className="p-4 border-b border-line-1">
        <input
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
          placeholder="Add an item…"
          className="w-full px-3 py-2 bg-surface-2 border border-line-1 rounded"
        />
      </form>

      <ul className="flex-1 overflow-y-auto">
        {visible.length === 0 && (
          <li className="p-4 text-sm text-ink-4">Nothing here yet.</li>
        )}
        {visible.map(item => (
          <li
            key={item.id}
            className={`flex items-center gap-3 px-4 py-2 border-b border-gray-800 cursor-pointer hover:bg-surface-2 ${
              item.id === activeItemId ? 'bg-surface-2' : ''
            }`}
            onClick={() => onSelectItem(item.id)}
          >
            <input
              type="checkbox"
              checked={item.status === 'completed'}
              onChange={e => { e.stopPropagation(); toggle(item) }}
              onClick={e => e.stopPropagation()}
              className="w-4 h-4"
            />
            <span
              className={`flex-1 truncate ${item.status === 'completed' ? 'line-through text-ink-4' : ''}`}
            >
              {item.title}
            </span>
            {item.spiciness > 1 && (
              <span className="text-xs" title={`Spiciness ${item.spiciness}`}>
                {'🌶️'.repeat(Math.min(item.spiciness, 5))}
              </span>
            )}
            {item.tags?.length > 0 && (
              <span className="text-xs text-ink-3">{item.tags.map(t => `#${t}`).join(' ')}</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
