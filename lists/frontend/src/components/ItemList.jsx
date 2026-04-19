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
      <div className="flex-1 flex items-center justify-center text-gray-500">
        Pick a list on the left, or create one.
      </div>
    )
  }

  const visible = showCompleted ? items : items.filter(i => i.status !== 'completed')

  return (
    <section className="flex-1 flex flex-col border-r border-gray-700 min-w-0">
      <header className="p-4 border-b border-gray-700 flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold truncate">
          {list.icon || '📝'} {list.name}
        </h2>
        <div className="flex items-center gap-2">
          {onCompile && (
            <button
              onClick={onCompile}
              className="px-2 py-1 text-xs bg-purple-700 rounded hover:bg-purple-600"
              title="Brain-dump → items (AI compile)"
            >
              ✨ Compile
            </button>
          )}
          <label className="text-xs text-gray-400 flex items-center gap-1">
            <input
              type="checkbox"
              checked={showCompleted}
              onChange={e => setShowCompleted(e.target.checked)}
            />
            Show completed
          </label>
        </div>
      </header>

      <form onSubmit={addItem} className="p-4 border-b border-gray-700">
        <input
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
          placeholder="Add an item…"
          className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded"
        />
      </form>

      <ul className="flex-1 overflow-y-auto">
        {visible.length === 0 && (
          <li className="p-4 text-sm text-gray-500">Nothing here yet.</li>
        )}
        {visible.map(item => (
          <li
            key={item.id}
            className={`flex items-center gap-3 px-4 py-2 border-b border-gray-800 cursor-pointer hover:bg-gray-800 ${
              item.id === activeItemId ? 'bg-gray-800' : ''
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
              className={`flex-1 truncate ${item.status === 'completed' ? 'line-through text-gray-500' : ''}`}
            >
              {item.title}
            </span>
            {item.spiciness > 1 && (
              <span className="text-xs" title={`Spiciness ${item.spiciness}`}>
                {'🌶️'.repeat(Math.min(item.spiciness, 5))}
              </span>
            )}
            {item.tags?.length > 0 && (
              <span className="text-xs text-gray-400">{item.tags.map(t => `#${t}`).join(' ')}</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
