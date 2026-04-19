import { useState } from 'react'
import * as api from '../api'
import ContextMenu from './ContextMenu'
import ConfirmDialog from './ConfirmDialog'
import InlineEditLabel from './InlineEditLabel'

const ICON_CHOICES = ['📁', '📋', '📝', '🛒', '🏠', '💼', '🎯', '🔧', '🌱', '🍽️', '🎨', '🏃']

export default function Sidebar({ folders, lists, activeListId, onSelectList, onRefresh }) {
  const [newListName, setNewListName] = useState('')
  const [newFolderName, setNewFolderName] = useState('')
  const [adding, setAdding] = useState(null)
  const [menu, setMenu] = useState(null)           // { kind, id, x, y }
  const [confirm, setConfirm] = useState(null)     // { title, message, onConfirm, danger }
  const [editing, setEditing] = useState(null)     // { kind, id }

  async function addFolder(e) {
    e.preventDefault()
    if (!newFolderName.trim()) return
    await api.createFolder({ name: newFolderName.trim() })
    setNewFolderName('')
    setAdding(null)
    onRefresh()
  }

  async function addList(folderId) {
    if (!newListName.trim()) return
    await api.createList({
      name: newListName.trim(),
      folder_id: folderId,
    })
    setNewListName('')
    setAdding(null)
    onRefresh()
  }

  const listsByFolder = {}
  const looseLists = []
  for (const l of lists) {
    if (l.folder_id == null) looseLists.push(l)
    else (listsByFolder[l.folder_id] ||= []).push(l)
  }

  function openMenu(e, kind, id) {
    e.preventDefault(); e.stopPropagation()
    setMenu({ kind, id, x: e.clientX, y: e.clientY })
  }

  function closeMenu() { setMenu(null) }

  // Resolve entity from current menu target.
  const menuFolder = menu?.kind === 'folder' ? folders.find(f => f.id === menu.id) : null
  const menuList = menu?.kind === 'list' ? lists.find(l => l.id === menu.id) : null

  const folderMenuItems = menuFolder ? [
    { label: 'Rename', icon: '✏️', hint: 'F2', onClick: () => setEditing({ kind: 'folder', id: menuFolder.id }) },
    { label: 'New list in folder', icon: '➕', onClick: () => setAdding(`folder-${menuFolder.id}`) },
    {
      label: 'Change icon', icon: '🎨',
      children: ICON_CHOICES.map(ic => ({
        label: ic, onClick: async () => { await api.updateFolder(menuFolder.id, { icon: ic }); onRefresh() },
      })),
    },
    { label: 'Duplicate', icon: '📑', hint: 'Ctrl+D', onClick: async () => { await api.duplicateFolder(menuFolder.id); onRefresh() } },
    {
      label: menuFolder.archived ? 'Unarchive' : 'Archive', icon: '🗄️',
      onClick: async () => { await api.updateFolder(menuFolder.id, { archived: !menuFolder.archived }); onRefresh() },
    },
    { separator: true },
    {
      label: 'Delete', icon: '🗑️', danger: true, hint: 'Del',
      onClick: () => {
        const count = (listsByFolder[menuFolder.id] || []).length
        setConfirm({
          title: `Delete folder "${menuFolder.name}"?`,
          message: count > 0
            ? `This folder contains ${count} list${count > 1 ? 's' : ''}. The lists will be kept and moved to Unfiled.`
            : 'The folder will be permanently deleted.',
          danger: true,
          onConfirm: async () => { await api.deleteFolder(menuFolder.id); setConfirm(null); onRefresh() },
        })
      },
    },
  ] : []

  const listMenuItems = menuList ? [
    { label: 'Rename', icon: '✏️', hint: 'F2', onClick: () => setEditing({ kind: 'list', id: menuList.id }) },
    { label: 'Duplicate', icon: '📑', hint: 'Ctrl+D', onClick: async () => { await api.duplicateList(menuList.id); onRefresh() } },
    {
      label: 'Move to folder', icon: '📂',
      children: [
        {
          label: '— Unfiled —',
          onClick: async () => { await api.updateList(menuList.id, { folder_id: null }); onRefresh() },
        },
        { separator: true },
        ...folders.map(f => ({
          label: `${f.icon || '📁'} ${f.name}`,
          disabled: f.id === menuList.folder_id,
          onClick: async () => { await api.updateList(menuList.id, { folder_id: f.id }); onRefresh() },
        })),
      ],
    },
    {
      label: 'Change icon', icon: '🎨',
      children: ICON_CHOICES.map(ic => ({
        label: ic, onClick: async () => { await api.updateList(menuList.id, { icon: ic }); onRefresh() },
      })),
    },
    {
      label: menuList.archived ? 'Unarchive' : 'Archive', icon: '🗄️',
      onClick: async () => { await api.updateList(menuList.id, { archived: !menuList.archived }); onRefresh() },
    },
    { separator: true },
    {
      label: 'Delete', icon: '🗑️', danger: true, hint: 'Del',
      onClick: () => {
        setConfirm({
          title: `Delete list "${menuList.name}"?`,
          message: 'All items and subtasks in this list will also be deleted. This cannot be undone.',
          danger: true,
          onConfirm: async () => { await api.deleteList(menuList.id); setConfirm(null); onRefresh() },
        })
      },
    },
  ] : []

  return (
    <aside className="w-full md:w-64 bg-surface-2 border-r border-line-1 p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-display font-bold tracking-tight">📋 Lists</h1>
        <button
          onClick={() => setAdding('folder')}
          className="text-sm text-ink-3 hover:text-white"
          title="New folder"
        >
          + folder
        </button>
      </div>

      {adding === 'folder' && (
        <form onSubmit={addFolder} className="mb-3 flex gap-1">
          <input
            autoFocus
            value={newFolderName}
            onChange={e => setNewFolderName(e.target.value)}
            placeholder="Folder name"
            className="flex-1 px-2 py-1 text-sm bg-surface-3 rounded"
          />
          <button className="px-2 text-sm bg-brand-cobalt rounded hover:bg-brand-cobalt-400">Add</button>
        </form>
      )}

      {folders.map(folder => (
        <FolderSection
          key={folder.id}
          folder={folder}
          lists={listsByFolder[folder.id] || []}
          activeListId={activeListId}
          onSelectList={onSelectList}
          adding={adding}
          setAdding={setAdding}
          newListName={newListName}
          setNewListName={setNewListName}
          addList={addList}
          onFolderMenu={(e) => openMenu(e, 'folder', folder.id)}
          onListMenu={(e, id) => openMenu(e, 'list', id)}
          editing={editing}
          setEditing={setEditing}
          onRefresh={onRefresh}
        />
      ))}

      <div className="mt-4">
        <div className="flex items-center justify-between text-xs uppercase text-ink-4 mb-1">
          <span>Unfiled</span>
          <button
            onClick={() => setAdding('loose')}
            className="text-ink-3 hover:text-white"
            title="New list"
          >
            +
          </button>
        </div>
        {adding === 'loose' && (
          <form onSubmit={e => { e.preventDefault(); addList(null) }} className="mb-2 flex gap-1">
            <input
              autoFocus
              value={newListName}
              onChange={e => setNewListName(e.target.value)}
              placeholder="List name"
              className="flex-1 px-2 py-1 text-sm bg-surface-3 rounded"
            />
            <button className="px-2 text-sm bg-brand-cobalt rounded hover:bg-brand-cobalt-400">Add</button>
          </form>
        )}
        {looseLists.map(list => (
          <ListRow
            key={list.id}
            list={list}
            active={list.id === activeListId}
            onClick={() => onSelectList(list.id)}
            onContextMenu={(e) => openMenu(e, 'list', list.id)}
            editing={editing?.kind === 'list' && editing.id === list.id}
            onCommitRename={async (name) => { await api.updateList(list.id, { name }); setEditing(null); onRefresh() }}
            onCancelRename={() => setEditing(null)}
          />
        ))}
      </div>

      <ContextMenu
        open={!!menu}
        x={menu?.x || 0}
        y={menu?.y || 0}
        items={menu?.kind === 'folder' ? folderMenuItems : listMenuItems}
        onClose={closeMenu}
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

function FolderSection({
  folder, lists, activeListId, onSelectList, adding, setAdding,
  newListName, setNewListName, addList,
  onFolderMenu, onListMenu, editing, setEditing, onRefresh,
}) {
  const key = `folder-${folder.id}`
  const isEditing = editing?.kind === 'folder' && editing.id === folder.id
  return (
    <div className="mb-3">
      <div
        className="flex items-center justify-between text-sm font-medium text-ink-2 mb-1 rounded px-1 py-0.5 hover:bg-surface-3"
        onContextMenu={onFolderMenu}
      >
        <span className="flex items-center gap-1 flex-1 min-w-0">
          <span>{folder.icon || '📁'}</span>
          <InlineEditLabel
            value={folder.name}
            editing={isEditing}
            onCommit={async (name) => { await api.updateFolder(folder.id, { name }); setEditing(null); onRefresh() }}
            onCancel={() => setEditing(null)}
            className="truncate"
            inputClassName="flex-1 min-w-0 px-1 py-0 bg-surface-3 border border-brand-cobalt rounded outline-none text-sm"
          />
        </span>
        <button
          onClick={() => setAdding(key)}
          className="text-ink-3 hover:text-white text-xs"
          title="New list in folder"
        >
          +
        </button>
      </div>
      {adding === key && (
        <form onSubmit={e => { e.preventDefault(); addList(folder.id) }} className="mb-2 flex gap-1">
          <input
            autoFocus
            value={newListName}
            onChange={e => setNewListName(e.target.value)}
            placeholder="List name"
            className="flex-1 px-2 py-1 text-sm bg-surface-3 rounded"
          />
          <button className="px-2 text-sm bg-brand-cobalt rounded hover:bg-brand-cobalt-400">Add</button>
        </form>
      )}
      {lists.map(l => (
        <ListRow
          key={l.id}
          list={l}
          active={l.id === activeListId}
          onClick={() => onSelectList(l.id)}
          onContextMenu={(e) => onListMenu(e, l.id)}
          editing={editing?.kind === 'list' && editing.id === l.id}
          onCommitRename={async (name) => { await api.updateList(l.id, { name }); setEditing(null); onRefresh() }}
          onCancelRename={() => setEditing(null)}
        />
      ))}
    </div>
  )
}

function ListRow({ list, active, onClick, onContextMenu, editing, onCommitRename, onCancelRename }) {
  return (
    <div
      onContextMenu={onContextMenu}
      className={`w-full flex items-center gap-1 px-2 py-1.5 rounded text-sm ${
        active ? 'bg-brand-cobalt text-white' : 'text-ink-2 hover:bg-surface-3'
      } ${editing ? '' : 'cursor-pointer'}`}
      onClick={editing ? undefined : onClick}
    >
      <span>{list.icon || '📝'}</span>
      {editing ? (
        <InlineEditLabel
          value={list.name}
          editing
          onCommit={onCommitRename}
          onCancel={onCancelRename}
          inputClassName="flex-1 min-w-0 px-1 py-0 bg-surface-3 text-ink-1 border border-brand-cobalt rounded outline-none text-sm"
        />
      ) : (
        <span className="truncate flex-1">{list.name}</span>
      )}
    </div>
  )
}
