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
import BoardView from './components/boards/BoardView.jsx'

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

  // ── Keyboard shortcuts (Ctrl+N new note, Ctrl+Enter toggle preview) ──────
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
      } else if (ctrl && e.key === 'Enter') {
        if (activeEntity?.kind !== 'note') return
        e.preventDefault()
        setEditorMode((m) => (m === 'preview' ? 'split' : 'preview'))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [activeEntity?.kind, activeEntity?.id, activeNote, activeList])

  return (
    <div className="h-full flex flex-col md:flex-row">
      <Sidebar
        folders={folders}
        lists={lists}
        notes={notes}
        boards={boards}
        activeEntity={activeEntity}
        onSelect={onSelect}
        onRefresh={loadTopLevel}
      />

      {activeEntity?.kind === 'board' ? (
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

      {activeEntity?.kind === 'board' ? null : activeEntity?.kind === 'note' ? (
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
