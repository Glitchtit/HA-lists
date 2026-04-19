import { useEffect, useState } from 'react'
import * as api from '../api'
import AiJobToast from './AiJobToast'
import ContextMenu from './ContextMenu'
import ConfirmDialog from './ConfirmDialog'
import InlineEditLabel from './InlineEditLabel'

const TONES = ['formal', 'casual', 'concise', 'kind', 'firm']
const TAG_COLORS = ['#64748b', '#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899']

export default function ItemDetail({ itemId, persons, onChange, onClose }) {
  const [item, setItem] = useState(null)
  const [subtasks, setSubtasks] = useState([])
  const [newSub, setNewSub] = useState('')
  const [newTag, setNewTag] = useState('')
  const [aiBusy, setAiBusy] = useState(null)
  const [aiError, setAiError] = useState(null)
  const [breakdownTaskId, setBreakdownTaskId] = useState(null)
  const [tone, setTone] = useState('formal')
  const [menu, setMenu] = useState(null)           // { kind: 'subtask'|'tag', id|name, x, y }
  const [confirm, setConfirm] = useState(null)
  const [editingSubId, setEditingSubId] = useState(null)

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
      <aside className="hidden lg:flex w-96 border-l border-line-1 items-center justify-center text-ink-4">
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

  async function runBreakdown() {
    setAiError(null); setAiBusy('breakdown')
    try {
      const { task_id } = await api.aiBreakdown(item.id, item.spiciness)
      setBreakdownTaskId(task_id)
    } catch (e) {
      setAiError(e.response?.data?.detail || e.message)
    } finally {
      setAiBusy(null)
    }
  }

  async function runEstimate() {
    setAiError(null); setAiBusy('estimate')
    try {
      const r = await api.aiEstimate(item.id)
      setItem({ ...item, estimate_min: r.estimate_min, estimate_max: r.estimate_max })
      onChange?.()
    } catch (e) {
      setAiError(e.response?.data?.detail || e.message)
    } finally {
      setAiBusy(null)
    }
  }

  async function runFormalize() {
    if (!item.notes?.trim()) { setAiError('Nothing to formalize — notes are empty'); return }
    setAiError(null); setAiBusy('formalize')
    try {
      const r = await api.aiFormalize(item.notes, tone)
      await patch({ notes: r.text })
    } catch (e) {
      setAiError(e.response?.data?.detail || e.message)
    } finally {
      setAiBusy(null)
    }
  }

  async function deleteSubtaskConfirm(st) {
    setConfirm({
      title: `Delete subtask "${st.title}"?`,
      message: 'This subtask will be permanently deleted.',
      danger: true,
      onConfirm: async () => {
        await api.deleteSubtask(st.id)
        setConfirm(null)
        setSubtasks(await api.getSubtasks(item.id))
      },
    })
  }

  async function deleteTagGlobally(name) {
    const tags = await api.getTags()
    const tag = tags.find(t => t.name === name)
    if (!tag) return
    setConfirm({
      title: `Delete tag "#${name}" globally?`,
      message: 'This will remove the tag from every item it is attached to.',
      danger: true,
      onConfirm: async () => {
        await api.deleteTag(tag.id)
        setConfirm(null)
        setItem({ ...item, tags: (item.tags || []).filter(t => t !== name) })
        onChange?.()
      },
    })
  }

  async function renameTag(name) {
    const fresh = window.prompt(`Rename tag "${name}" to:`, name)
    if (!fresh || fresh.trim() === '' || fresh === name) return
    const tags = await api.getTags()
    const tag = tags.find(t => t.name === name)
    if (!tag) return
    try {
      await api.updateTag(tag.id, { name: fresh.trim() })
    } catch (e) {
      if (e.response?.status === 409) {
        window.alert(`Tag "${fresh}" already exists.`)
        return
      }
      throw e
    }
    setItem(await api.getItem(item.id))
    onChange?.()
  }

  async function recolorTag(name, color) {
    const tags = await api.getTags()
    const tag = tags.find(t => t.name === name)
    if (!tag) return
    await api.updateTag(tag.id, { color })
  }

  const menuSubtask = menu?.kind === 'subtask' ? subtasks.find(s => s.id === menu.id) : null
  const subtaskMenuItems = menuSubtask ? [
    { label: 'Rename', icon: '✏️', hint: 'F2', onClick: () => setEditingSubId(menuSubtask.id) },
    {
      label: menuSubtask.status === 'completed' ? 'Reopen' : 'Complete', icon: '✔️',
      onClick: () => toggleSub(menuSubtask),
    },
    { separator: true },
    { label: 'Delete', icon: '🗑️', danger: true, hint: 'Del', onClick: () => deleteSubtaskConfirm(menuSubtask) },
  ] : []

  const tagMenuItems = menu?.kind === 'tag' ? [
    { label: 'Rename', icon: '✏️', onClick: () => renameTag(menu.name) },
    {
      label: 'Change color', icon: '🎨',
      children: TAG_COLORS.map(c => ({
        label: '●', onClick: () => recolorTag(menu.name, c),
      })),
    },
    { label: 'Detach from item', icon: '⊖', onClick: () => removeTag(menu.name) },
    { separator: true },
    { label: 'Delete tag globally', icon: '🗑️', danger: true, onClick: () => deleteTagGlobally(menu.name) },
  ] : []

  return (
    <aside className="w-full lg:w-96 bg-surface-1 border-l border-line-1 overflow-y-auto">
      <div className="p-4 border-b border-line-1 flex items-start gap-2">
        <input
          value={item.title}
          onChange={e => setItem({ ...item, title: e.target.value })}
          onBlur={() => patch({ title: item.title })}
          className="flex-1 bg-transparent text-lg font-semibold outline-none"
        />
        {onClose && (
          <button onClick={onClose} className="text-ink-4 hover:text-white lg:hidden">✕</button>
        )}
      </div>

      <div className="p-4 space-y-4">
        <label className="block">
          <span className="text-xs uppercase text-ink-3">Notes</span>
          <textarea
            value={item.notes || ''}
            onChange={e => setItem({ ...item, notes: e.target.value })}
            onBlur={() => patch({ notes: item.notes })}
            rows={4}
            className="mt-1 w-full px-2 py-1 bg-surface-2 border border-line-1 rounded text-sm"
          />
        </label>

        <label className="block">
          <span className="text-xs uppercase text-ink-3">
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
            className="w-full spice"
          />
        </label>

        <label className="block">
          <span className="text-xs uppercase text-ink-3">Assigned to</span>
          <select
            value={item.assigned_to || ''}
            onChange={e => patch({ assigned_to: e.target.value || null })}
            className="mt-1 w-full px-2 py-1 bg-surface-2 border border-line-1 rounded text-sm"
          >
            <option value="">— Anyone —</option>
            {persons.map(p => (
              <option key={p.entity_id} value={p.entity_id}>{p.name}</option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-xs uppercase text-ink-3">Due</span>
          <input
            type="datetime-local"
            value={item.due_at ? item.due_at.slice(0, 16) : ''}
            onChange={e => patch({ due_at: e.target.value || null })}
            className="mt-1 w-full px-2 py-1 bg-surface-2 border border-line-1 rounded text-sm"
          />
        </label>

        <div>
          <span className="text-xs uppercase text-ink-3">Tags</span>
          <div className="flex flex-wrap gap-1 mt-1 mb-2">
            {(item.tags || []).map(t => (
              <span
                key={t}
                onContextMenu={(e) => { e.preventDefault(); e.stopPropagation(); setMenu({ kind: 'tag', name: t, x: e.clientX, y: e.clientY }) }}
                className="inline-flex items-center gap-1 px-2 py-0.5 bg-surface-2 border border-line-1 rounded text-xs cursor-context-menu"
              >
                #{t}
                <button onClick={() => removeTag(t)} className="text-ink-4 hover:text-white">×</button>
              </span>
            ))}
          </div>
          <form onSubmit={addTag} className="flex gap-1">
            <input
              value={newTag}
              onChange={e => setNewTag(e.target.value)}
              placeholder="new tag"
              className="flex-1 px-2 py-1 text-sm bg-surface-2 border border-line-1 rounded"
            />
            <button className="px-2 text-sm bg-surface-3 rounded hover:bg-surface-4">Add</button>
          </form>
        </div>

        <div>
          <span className="text-xs uppercase text-ink-3">Subtasks</span>
          <div className="mt-1 mb-2 flex flex-wrap items-center gap-1 text-xs">
            <button
              onClick={runBreakdown}
              disabled={aiBusy === 'breakdown' || !!breakdownTaskId}
              className="px-2 py-1 bg-brand-orange rounded hover:bg-brand-orange-400 disabled:opacity-50"
              title="AI breakdown into subtasks at current spiciness"
            >
              🪄 Break down ({'🌶️'.repeat(item.spiciness)})
            </button>
            <button
              onClick={runEstimate}
              disabled={aiBusy === 'estimate'}
              className="px-2 py-1 bg-surface-3 rounded hover:bg-surface-4 disabled:opacity-50"
              title="AI time estimate"
            >
              ⏱️ Estimate
              {typeof item.estimate_min === 'number' && (
                <span className="ml-1 text-ink-2">
                  ({item.estimate_min}–{item.estimate_max}m)
                </span>
              )}
            </button>
            <select
              value={tone}
              onChange={e => setTone(e.target.value)}
              className="px-1 py-1 bg-surface-2 border border-line-1 rounded"
              title="Tone for formalize"
            >
              {TONES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <button
              onClick={runFormalize}
              disabled={aiBusy === 'formalize'}
              className="px-2 py-1 bg-surface-3 rounded hover:bg-surface-4 disabled:opacity-50"
              title="Rewrite notes in chosen tone"
            >
              ✏️ Formalize notes
            </button>
          </div>
          {aiError && <div className="mb-2 text-xs text-semantic-danger">{aiError}</div>}
          <ul className="mt-1 space-y-1">
            {subtasks.map(st => (
              <li
                key={st.id}
                className="flex items-center gap-2 text-sm"
                onContextMenu={(e) => { e.preventDefault(); e.stopPropagation(); setMenu({ kind: 'subtask', id: st.id, x: e.clientX, y: e.clientY }) }}
              >
                <input
                  type="checkbox"
                  checked={st.status === 'completed'}
                  onChange={() => toggleSub(st)}
                />
                {editingSubId === st.id ? (
                  <InlineEditLabel
                    value={st.title}
                    editing
                    onCommit={async (title) => {
                      await api.updateSubtask(st.id, { title })
                      setEditingSubId(null)
                      setSubtasks(await api.getSubtasks(item.id))
                    }}
                    onCancel={() => setEditingSubId(null)}
                  />
                ) : (
                  <span className={st.status === 'completed' ? 'line-through text-ink-4' : ''}>
                    {st.title}
                  </span>
                )}
                {st.ai_generated && <span title="AI-generated" className="text-xs text-brand-orange-300">✨</span>}
              </li>
            ))}
          </ul>
          <form onSubmit={addSubtask} className="flex gap-1 mt-2">
            <input
              value={newSub}
              onChange={e => setNewSub(e.target.value)}
              placeholder="Add subtask…"
              className="flex-1 px-2 py-1 text-sm bg-surface-2 border border-line-1 rounded"
            />
            <button className="px-2 text-sm bg-surface-3 rounded hover:bg-surface-4">Add</button>
          </form>
        </div>
      </div>
      {breakdownTaskId && (
        <AiJobToast
          taskId={breakdownTaskId}
          label="Breaking down into subtasks"
          onDone={async () => {
            setSubtasks(await api.getSubtasks(item.id))
            onChange?.()
          }}
          onDismiss={() => setBreakdownTaskId(null)}
        />
      )}

      <ContextMenu
        open={!!menu}
        x={menu?.x || 0}
        y={menu?.y || 0}
        items={menu?.kind === 'subtask' ? subtaskMenuItems : tagMenuItems}
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
    </aside>
  )
}
