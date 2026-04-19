import { useEffect, useState } from 'react'
import * as api from '../api'
import ContextMenu from './ContextMenu'
import ConfirmDialog from './ConfirmDialog'
import InlineEditLabel from './InlineEditLabel'

export default function ItemList({ list, items, activeItemId, onSelectItem, onRefresh, onCompile, lists = [], persons = [] }) {
  const [newTitle, setNewTitle] = useState('')
  const [showCompleted, setShowCompleted] = useState(false)
  const [menu, setMenu] = useState(null)
  const [confirm, setConfirm] = useState(null)
  const [editingId, setEditingId] = useState(null)

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

  // Keyboard shortcuts when an item is active.
  useEffect(() => {
    function onKey(e) {
      if (!activeItemId) return
      // Ignore if focus is inside an editable element.
      const t = document.activeElement
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
      const item = items.find(i => i.id === activeItemId)
      if (!item) return
      if (e.key === 'F2') { e.preventDefault(); setEditingId(item.id) }
      else if (e.key === 'Delete') {
        e.preventDefault()
        setConfirm({
          title: `Delete "${item.title}"?`,
          message: 'The item and its subtasks will be permanently deleted.',
          danger: true,
          onConfirm: async () => { await api.deleteItem(item.id); setConfirm(null); onRefresh() },
        })
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'd') {
        e.preventDefault()
        api.duplicateItem(item.id).then(onRefresh)
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [activeItemId, items, onRefresh])

  if (!list) {
    return (
      <div className="flex-1 flex items-center justify-center text-ink-4">
        Pick a list on the left, or create one.
      </div>
    )
  }

  const visible = showCompleted ? items : items.filter(i => i.status !== 'completed')
  const menuItem = menu ? items.find(i => i.id === menu.id) : null

  function openMenu(e, id) {
    e.preventDefault(); e.stopPropagation()
    onSelectItem(id)
    setMenu({ id, x: e.clientX, y: e.clientY })
  }

  const menuItems = menuItem ? [
    { label: 'Rename', icon: '✏️', hint: 'F2', onClick: () => setEditingId(menuItem.id) },
    {
      label: menuItem.status === 'completed' ? 'Reopen' : 'Complete',
      icon: menuItem.status === 'completed' ? '↩️' : '✔️',
      onClick: () => toggle(menuItem),
    },
    { label: 'Duplicate', icon: '📑', hint: 'Ctrl+D', onClick: async () => { await api.duplicateItem(menuItem.id); onRefresh() } },
    {
      label: 'Move to list', icon: '📂',
      children: lists
        .filter(l => l.id !== menuItem.list_id)
        .map(l => ({
          label: `${l.icon || '📝'} ${l.name}`,
          onClick: async () => { await api.updateItem(menuItem.id, { list_id: l.id }); onRefresh() },
        })),
    },
    {
      label: 'Assign to', icon: '👤',
      children: [
        {
          label: '— Unassigned —',
          onClick: async () => { await api.updateItem(menuItem.id, { assigned_to: null }); onRefresh() },
        },
        { separator: true },
        ...persons.map(p => ({
          label: p.name,
          disabled: p.entity_id === menuItem.assigned_to,
          onClick: async () => { await api.updateItem(menuItem.id, { assigned_to: p.entity_id }); onRefresh() },
        })),
      ],
    },
    {
      label: 'Spiciness', icon: '🌶️',
      children: [1, 2, 3, 4, 5].map(n => ({
        label: '🌶️'.repeat(n),
        disabled: menuItem.spiciness === n,
        onClick: async () => { await api.updateItem(menuItem.id, { spiciness: n }); onRefresh() },
      })),
    },
    {
      label: 'Priority', icon: '🚩',
      children: [
        { label: 'None', disabled: menuItem.priority === 0, onClick: async () => { await api.updateItem(menuItem.id, { priority: 0 }); onRefresh() } },
        { label: 'Low', disabled: menuItem.priority === 1, onClick: async () => { await api.updateItem(menuItem.id, { priority: 1 }); onRefresh() } },
        { label: 'Medium', disabled: menuItem.priority === 2, onClick: async () => { await api.updateItem(menuItem.id, { priority: 2 }); onRefresh() } },
        { label: 'High', disabled: menuItem.priority === 3, onClick: async () => { await api.updateItem(menuItem.id, { priority: 3 }); onRefresh() } },
      ],
    },
    { separator: true },
    {
      label: 'Delete', icon: '🗑️', danger: true, hint: 'Del',
      onClick: () => setConfirm({
        title: `Delete "${menuItem.title}"?`,
        message: 'The item and its subtasks will be permanently deleted.',
        danger: true,
        onConfirm: async () => { await api.deleteItem(menuItem.id); setConfirm(null); onRefresh() },
      }),
    },
  ] : []

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
            className={`group flex items-center gap-3 px-4 py-2 border-b border-gray-800 cursor-pointer hover:bg-surface-2 ${
              item.id === activeItemId ? 'bg-surface-2' : ''
            }`}
            onClick={() => onSelectItem(item.id)}
            onContextMenu={(e) => openMenu(e, item.id)}
          >
            <input
              type="checkbox"
              checked={item.status === 'completed'}
              onChange={e => { e.stopPropagation(); toggle(item) }}
              onClick={e => e.stopPropagation()}
              className="w-4 h-4"
            />
            {editingId === item.id ? (
              <InlineEditLabel
                value={item.title}
                editing
                onCommit={async (title) => { await api.updateItem(item.id, { title }); setEditingId(null); onRefresh() }}
                onCancel={() => setEditingId(null)}
                inputClassName="flex-1 px-1 py-0 bg-surface-3 border border-brand-cobalt rounded outline-none text-sm"
              />
            ) : (
              <span
                className={`flex-1 truncate ${item.status === 'completed' ? 'line-through text-ink-4' : ''}`}
              >
                {item.title}
              </span>
            )}
            {item.spiciness > 1 && (
              <span className="text-xs" title={`Spiciness ${item.spiciness}`}>
                {'🌶️'.repeat(Math.min(item.spiciness, 5))}
              </span>
            )}
            {item.tags?.length > 0 && (
              <span className="text-xs text-ink-3">{item.tags.map(t => `#${t}`).join(' ')}</span>
            )}
            <button
              onClick={(e) => openMenu(e, item.id)}
              className="opacity-0 group-hover:opacity-100 md:opacity-0 text-ink-4 hover:text-white text-xs px-1"
              title="Actions"
              aria-label="Actions"
            >
              ⋯
            </button>
          </li>
        ))}
      </ul>

      <ContextMenu
        open={!!menu}
        x={menu?.x || 0}
        y={menu?.y || 0}
        items={menuItems}
        onClose={() => setMenu(null)}
      />

      <ConfirmDialog
        open={!!confirm}
        title={confirm?.title}
        message={confirm?.message}
        confirmLabel={confirm?.danger ? 'Delete' : 'Confirm'}
        danger={confirm?.danger}
        onConfirm={confirm?.onConfirm}
        onCancel={() => setConfirm(null)}
      />
    </section>
  )
}
