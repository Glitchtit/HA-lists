import { useCallback, useEffect, useState } from 'react'
import * as api from './api'
import Sidebar from './components/Sidebar'
import ItemList from './components/ItemList'
import ItemDetail from './components/ItemDetail'
import CompileDialog from './components/CompileDialog'
import ConfirmDialog from './components/ConfirmDialog'
import NoteEditor from './components/notes/NoteEditor'
import NoteToolbar from './components/notes/NoteToolbar'
import NotesRightPane from './components/notes/NotesRightPane'
import NoteGraph from './components/notes/NoteGraph'
import NoteTemplatePicker from './components/notes/NoteTemplatePicker'
import TabBar from './components/TabBar'
import HotkeysModal from './components/HotkeysModal'
import WorkspacesModal from './components/WorkspacesModal'
import CustomCSSModal, { applyStoredCSS } from './components/CustomCSSModal'
import BoardView from './components/boards/BoardView.jsx'
import CommandPalette from './components/search/CommandPalette.jsx'
import WhatsNewModal from './components/WhatsNewModal'

export default function App() {
  const [folders, setFolders] = useState([])
  const [lists, setLists] = useState([])
  const [notes, setNotes] = useState([])
  const [boards, setBoards] = useState([])
  const [items, setItems] = useState([])
  const [persons, setPersons] = useState([])
  const [activeEntity, setActiveEntity] = useState(null) // {kind:'list'|'note'|'board', id}
  const [activeItemId, setActiveItemId] = useState(null)
  const [activeNote, setActiveNote] = useState(null)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [compileOpen, setCompileOpen] = useState(false)
  const [rewriteConfirm, setRewriteConfirm] = useState(null)
  const [editorMode, setEditorMode] = useState('preview') // 'split'|'source'|'preview'
  const [noteBodyVersion, setNoteBodyVersion] = useState(0)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [recent, setRecent] = useState(() => {
    try { return JSON.parse(localStorage.getItem('lists_recent') || '[]') } catch { return [] }
  })
  const [tabs, setTabs] = useState([]) // [{kind, id}]
  const [templatePickerOpen, setTemplatePickerOpen] = useState(false)
  const [hotkeysOpen, setHotkeysOpen] = useState(false)
  const [workspacesOpen, setWorkspacesOpen] = useState(false)
  const [cssOpen, setCssOpen] = useState(false)

  // Apply user CSS once on mount; survives across sessions.
  useEffect(() => { applyStoredCSS() }, [])

  useEffect(() => {
    const onKey = (e) => {
      const key = (e.key || '').toLowerCase()
      if ((e.metaKey || e.ctrlKey) && key === 'k') {
        const tag = (e.target?.tagName || '').toLowerCase()
        if (tag === 'input' || tag === 'textarea' || e.target?.isContentEditable) {
          if (!paletteOpen) return
        }
        e.preventDefault()
        setPaletteOpen((v) => !v)
      } else if (e.key === 'Escape' && paletteOpen) {
        setPaletteOpen(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [paletteOpen])

  async function loadTopLevel() {
    try {
      const [f, l, n, b, p] = await Promise.all([
        api.getFolders(false),
        api.getLists(),
        api.getNotes({ archived: false }),
        api.listBoards({ archived: false }),
        api.getPersons(),
      ])
      setFolders(f)
      setLists(l)
      setNotes(n)
      setBoards(b)
      setPersons(p)
      setError(null)
    } catch (e) {
      setError(e.message || 'Failed to load')
    }
  }

  async function loadItems(listId) {
    if (!listId) { setItems([]); return }
    try {
      setItems(await api.getItems({ list_id: listId }))
    } catch (e) {
      setError(e.message || 'Failed to load items')
    }
  }

  async function loadNote(id) {
    if (!id) { setActiveNote(null); return }
    try {
      setActiveNote(await api.getNote(id))
    } catch (e) {
      setError(e.message || 'Failed to load note')
    }
  }

  useEffect(() => { loadTopLevel() }, [])

  useEffect(() => {
    if (!activeEntity) { setItems([]); setActiveNote(null); return }
    if (activeEntity.kind === 'list') {
      setActiveNote(null)
      loadItems(activeEntity.id)
    } else if (activeEntity.kind === 'note') {
      setItems([])
      setActiveItemId(null)
      loadNote(activeEntity.id)
    }
    if (['list', 'note', 'board'].includes(activeEntity.kind)) {
      setRecent((prev) => {
        const filtered = prev.filter((e) => !(e.kind === activeEntity.kind && e.id === activeEntity.id))
        const next = [{ kind: activeEntity.kind, id: activeEntity.id, ts: Date.now() }, ...filtered].slice(0, 10)
        try { localStorage.setItem('lists_recent', JSON.stringify(next)) } catch {}
        return next
      })
      setTabs((prev) => {
        if (prev.some((t) => t.kind === activeEntity.kind && t.id === activeEntity.id)) return prev
        const next = [...prev, { kind: activeEntity.kind, id: activeEntity.id, pinned: false }]
        // Cap at 12, but never drop pinned tabs.
        if (next.length <= 12) return next
        const drop = next.findIndex((t) => !t.pinned)
        if (drop < 0) return next // all pinned — let it grow
        return [...next.slice(0, drop), ...next.slice(drop + 1)]
      })
    }
  }, [activeEntity?.kind, activeEntity?.id])

  const activeList = activeEntity?.kind === 'list' ? (lists.find(l => l.id === activeEntity.id) || null) : null

  function flashToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  function onSelect({ kind, id }) {
    setActiveEntity({ kind, id })
    setActiveItemId(null)
  }

  // ── Note handlers ─────────────────────────────────────────────────────────
  async function handleNoteChange(partial) {
    if (!activeNote) return
    try {
      const updated = await api.updateNote(activeNote.id, partial)
      setActiveNote(updated)
      if ('title' in partial || 'pinned' in partial || 'archived' in partial || 'folder_id' in partial || 'icon' in partial) {
        const n = await api.getNotes({ archived: false })
        setNotes(n)
      }
    } catch (e) {
      setError(e.message || 'Failed to save note')
    }
  }

  async function handleWikilinkClick(title) {
    try {
      const hit = await api.resolveNote(title)
      if (hit) { setActiveEntity({ kind: 'note', id: hit.note_id }); return }
      if (window.confirm(`Create note "${title}"?`)) {
        const n = await api.createNote({ title, body: '', folder_id: activeNote?.folder_id ?? null })
        await loadTopLevel()
        setActiveEntity({ kind: 'note', id: n.id })
      }
    } catch (e) {
      setError(e.message || 'Wikilink resolve failed')
    }
  }

  const handleEmbedFetch = useCallback(async (title) => {
    try {
      const hit = await api.resolveNote(title)
      if (!hit) return null
      return await api.getNote(hit.note_id)
    } catch {
      return null
    }
  }, [])

  async function handleNoteAction(kind, args) {
    if (!activeNote) return
    try {
      if (kind === 'summarize') {
        const { summary } = await api.aiNoteSummarize(activeNote.id)
        const callout = `> [!info] Summary\n> ${String(summary || '').split('\n').join('\n> ')}`
        const body = callout + '\n\n' + (activeNote.body || '')
        await handleNoteChange({ body })
        setNoteBodyVersion((v) => v + 1)
      } else if (kind === 'continue') {
        const { continuation } = await api.aiNoteContinue(activeNote.id, args?.prompt || '')
        const body = (activeNote.body || '') + '\n\n' + (continuation || '')
        await handleNoteChange({ body })
        setNoteBodyVersion((v) => v + 1)
      } else if (kind === 'rewrite') {
        const tone = args?.tone || 'neutral'
        await new Promise((resolve) => {
          setRewriteConfirm({
            title: `Rewrite note in "${tone}" tone?`,
            message: 'This will replace the current body. You can undo from your editor history only while the note remains open.',
            onConfirm: async () => {
              setRewriteConfirm(null)
              try {
                const { body } = await api.aiNoteRewrite(activeNote.id, tone)
                await handleNoteChange({ body })
                setNoteBodyVersion((v) => v + 1)
              } catch (e) {
                setError(e.message || 'Rewrite failed')
              } finally {
                resolve()
              }
            },
            onCancel: () => { setRewriteConfirm(null); resolve() },
          })
        })
      } else if (kind === 'extract-tasks') {
        const targetListId = args?.targetListId
        if (!targetListId) return
        const res = await api.aiNoteExtractTasks(activeNote.id, targetListId)
        const count = Array.isArray(res?.created) ? res.created.length : 0
        flashToast(`Extracted ${count} task${count === 1 ? '' : 's'}`)
        if (activeEntity?.kind === 'list' && activeEntity.id === targetListId) {
          loadItems(targetListId)
        }
      } else if (kind === 'outline') {
        const { outline } = await api.aiNoteOutline(activeNote.id)
        const body = (activeNote.body || '') + '\n\n## Outline\n' + (outline || '')
        await handleNoteChange({ body })
        setNoteBodyVersion((v) => v + 1)
      }
    } catch (e) {
      setError(e.message || `AI ${kind} failed`)
    }
  }

  async function openDailyNote() {
    try {
      const n = await api.getOrCreateDailyNote()
      await loadTopLevel()
      setActiveEntity({ kind: 'note', id: n.id })
    } catch (e) {
      setError(e.message || 'Failed to open daily note')
    }
  }

  function closeTab(tab) {
    setTabs((prev) => {
      const next = prev.filter((t) => !(t.kind === tab.kind && t.id === tab.id))
      const isActive = activeEntity?.kind === tab.kind && activeEntity.id === tab.id
      if (isActive) {
        const fallback = next[next.length - 1]
        setActiveEntity(fallback ? { kind: fallback.kind, id: fallback.id } : null)
      }
      return next
    })
  }

  function togglePinTab(tab) {
    setTabs((prev) => prev.map((t) =>
      t.kind === tab.kind && t.id === tab.id ? { ...t, pinned: !t.pinned } : t
    ))
  }

  function openRandomNote() {
    const pool = notes.filter((n) => !n.archived)
    if (pool.length === 0) {
      flashToast('No notes to pick from')
      return
    }
    let pick = pool[Math.floor(Math.random() * pool.length)]
    if (pool.length > 1 && activeEntity?.kind === 'note' && pick.id === activeEntity.id) {
      const others = pool.filter((n) => n.id !== activeEntity.id)
      pick = others[Math.floor(Math.random() * others.length)]
    }
    setActiveEntity({ kind: 'note', id: pick.id })
    flashToast(`🎲 ${pick.title || 'Untitled note'}`)
  }

  // ── Keyboard shortcuts (Ctrl+N new note, Ctrl+Enter toggle preview, Ctrl+Alt+T daily note) ──
  useEffect(() => {
    function onKey(e) {
      const t = e.target
      const inEditable = t && (
        t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable ||
        (t.closest && t.closest('.cm-editor'))
      )
      const ctrl = e.ctrlKey || e.metaKey
      if (ctrl && !e.shiftKey && !e.altKey && (e.key === 'n' || e.key === 'N')) {
        if (inEditable) return
        e.preventDefault()
        let folderId = null
        if (activeEntity?.kind === 'note' && activeNote) folderId = activeNote.folder_id ?? null
        else if (activeEntity?.kind === 'list' && activeList) folderId = activeList.folder_id ?? null
        ;(async () => {
          try {
            const n = await api.createNote({ title: 'Untitled note', body: '', folder_id: folderId })
            await loadTopLevel()
            setActiveEntity({ kind: 'note', id: n.id })
          } catch (err) {
            setError(err.message || 'Create note failed')
          }
        })()
      } else if (ctrl && e.altKey && (e.key === 't' || e.key === 'T')) {
        if (inEditable) return
        e.preventDefault()
        openDailyNote()
      } else if (ctrl && !e.shiftKey && !e.altKey && (e.key === 'f' || e.key === 'F')) {
        // Ctrl+F: switch to split mode (if needed) so CodeMirror's own
        // search panel (registered via @codemirror/search) can take over.
        if (activeEntity?.kind === 'note' && editorMode === 'preview') {
          setEditorMode('split')
          requestAnimationFrame(() => {
            const cm = document.querySelector('.cm-editor .cm-content')
            if (cm) cm.focus()
          })
          // Don't prevent default — let the browser pass Ctrl+F on the next
          // tick so the CodeMirror keymap catches it.
        }
      } else if (e.key === '?' && !ctrl && !e.altKey) {
        if (inEditable) return
        e.preventDefault()
        setHotkeysOpen(true)
      } else if (e.key === 'Escape' && hotkeysOpen) {
        setHotkeysOpen(false)
      } else if (ctrl && e.key === 'Enter') {
        if (activeEntity?.kind !== 'note') return
        e.preventDefault()
        setEditorMode((m) => (m === 'preview' ? 'split' : 'preview'))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [activeEntity?.kind, activeEntity?.id, activeNote, activeList, hotkeysOpen, editorMode])

  return (
    <div className="h-full flex flex-col md:flex-row">
      <WhatsNewModal />
      <Sidebar
        folders={folders}
        lists={lists}
        notes={notes}
        boards={boards}
        activeEntity={activeEntity}
        onSelect={onSelect}
        onRefresh={loadTopLevel}
        onOpenDailyNote={openDailyNote}
        onOpenRandomNote={openRandomNote}
        onOpenTemplatePicker={() => setTemplatePickerOpen(true)}
        onOpenWorkspaces={() => setWorkspacesOpen(true)}
        onOpenCustomCSS={() => setCssOpen(true)}
        recent={recent}
      />

      <div className="flex-1 min-w-0 flex flex-col">
        <TabBar
          tabs={tabs}
          activeEntity={activeEntity}
          lists={lists}
          notes={notes}
          boards={boards}
          onSelect={(e) => setActiveEntity(e)}
          onClose={closeTab}
          onTogglePin={togglePinTab}
        />
        <div className="flex-1 min-h-0 flex">

      {activeEntity?.kind === 'graph' ? (
        <div className="flex-1 min-w-0 flex flex-col">
          <div className="border-b border-line-1 bg-surface-1 px-4 py-2 text-sm text-ink-2">
            🕸️ Note graph
          </div>
          <div className="flex-1 min-h-0">
            <NoteGraph onSelect={(e) => setActiveEntity(e)} />
          </div>
        </div>
      ) : activeEntity?.kind === 'board' ? (
        <div className="flex-1 min-w-0 flex flex-col">
          <BoardView boardId={activeEntity.id} onOpenEntity={(e) => setActiveEntity(e)} />
        </div>
      ) : activeEntity?.kind === 'note' ? (
        <div className="flex-1 min-w-0 flex flex-col">
          <NoteToolbar note={activeNote} onAction={handleNoteAction} lists={lists} />
          <div className="flex-1 min-h-0">
            <NoteEditor
              key={`${activeNote?.id}-${noteBodyVersion}`}
              note={activeNote}
              mode={editorMode}
              onModeChange={setEditorMode}
              onChange={handleNoteChange}
              onWikilinkClick={handleWikilinkClick}
              onEmbedFetch={handleEmbedFetch}
              onExtracted={() => { loadTopLevel(); flashToast('Extracted to new note') }}
            />
          </div>
        </div>
      ) : (
        <ItemList
          list={activeList}
          items={items}
          lists={lists}
          persons={persons}
          activeItemId={activeItemId}
          onSelectItem={setActiveItemId}
          onRefresh={() => { loadItems(activeEntity?.id); loadTopLevel() }}
          onCompile={activeList ? () => setCompileOpen(true) : null}
        />
      )}

      {activeEntity?.kind === 'board' || activeEntity?.kind === 'graph' ? null : activeEntity?.kind === 'note' ? (
        <NotesRightPane
          note={activeNote}
          onSelect={(id) => setActiveEntity({ kind: 'note', id })}
        />
      ) : (
        <ItemDetail
          itemId={activeItemId}
          persons={persons}
          onChange={() => loadItems(activeEntity?.id)}
          onClose={() => setActiveItemId(null)}
        />
      )}
        </div>
      </div>

      {error && (
        <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-80 bg-[rgba(239,68,68,0.18)] text-semantic-danger px-3 py-2 rounded text-sm">
          {error}
        </div>
      )}
      {toast && (
        <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-80 bg-surface-2 border border-line-1 text-ink-1 px-3 py-2 rounded text-sm shadow-lg">
          {toast}
        </div>
      )}
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onJump={(e) => setActiveEntity(e)}
      />
      <HotkeysModal open={hotkeysOpen} onClose={() => setHotkeysOpen(false)} />
      <CustomCSSModal open={cssOpen} onClose={() => setCssOpen(false)} />
      <WorkspacesModal
        open={workspacesOpen}
        onClose={() => setWorkspacesOpen(false)}
        tabs={tabs}
        activeEntity={activeEntity}
        onRestore={(w) => {
          setTabs(w.tabs || [])
          setActiveEntity(w.activeEntity || null)
        }}
      />
      <NoteTemplatePicker
        open={templatePickerOpen}
        folderId={
          activeEntity?.kind === 'note' && activeNote ? activeNote.folder_id :
          activeEntity?.kind === 'list' && activeList ? activeList.folder_id :
          null
        }
        onClose={() => setTemplatePickerOpen(false)}
        onCreated={async (n) => { await loadTopLevel(); setActiveEntity({ kind: 'note', id: n.id }); }}
      />
      {compileOpen && activeList && (
        <CompileDialog
          listId={activeList.id}
          listName={activeList.name}
          onClose={() => setCompileOpen(false)}
          onRefresh={() => loadItems(activeList.id)}
        />
      )}
      <ConfirmDialog
        open={!!rewriteConfirm}
        title={rewriteConfirm?.title}
        message={rewriteConfirm?.message}
        confirmLabel="Rewrite"
        onConfirm={rewriteConfirm?.onConfirm}
        onCancel={rewriteConfirm?.onCancel}
      />
    </div>
  )
}
