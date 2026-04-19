import { useState } from 'react'
import * as api from '../api'

export default function Sidebar({ folders, lists, activeListId, onSelectList, onRefresh }) {
  const [newListName, setNewListName] = useState('')
  const [newFolderName, setNewFolderName] = useState('')
  const [adding, setAdding] = useState(null)

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

  return (
    <aside className="w-full md:w-64 bg-gray-800 border-r border-gray-700 p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold">Lists</h1>
        <button
          onClick={() => setAdding('folder')}
          className="text-sm text-gray-400 hover:text-white"
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
            className="flex-1 px-2 py-1 text-sm bg-gray-700 rounded"
          />
          <button className="px-2 text-sm bg-blue-600 rounded hover:bg-blue-500">Add</button>
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
        />
      ))}

      <div className="mt-4">
        <div className="flex items-center justify-between text-xs uppercase text-gray-500 mb-1">
          <span>Unfiled</span>
          <button
            onClick={() => setAdding('loose')}
            className="text-gray-400 hover:text-white"
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
              className="flex-1 px-2 py-1 text-sm bg-gray-700 rounded"
            />
            <button className="px-2 text-sm bg-blue-600 rounded hover:bg-blue-500">Add</button>
          </form>
        )}
        {looseLists.map(list => (
          <ListRow
            key={list.id}
            list={list}
            active={list.id === activeListId}
            onClick={() => onSelectList(list.id)}
          />
        ))}
      </div>
    </aside>
  )
}

function FolderSection({ folder, lists, activeListId, onSelectList, adding, setAdding, newListName, setNewListName, addList }) {
  const key = `folder-${folder.id}`
  return (
    <div className="mb-3">
      <div className="flex items-center justify-between text-sm font-medium text-gray-300 mb-1">
        <span>{folder.icon || '📁'} {folder.name}</span>
        <button
          onClick={() => setAdding(key)}
          className="text-gray-400 hover:text-white text-xs"
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
            className="flex-1 px-2 py-1 text-sm bg-gray-700 rounded"
          />
          <button className="px-2 text-sm bg-blue-600 rounded hover:bg-blue-500">Add</button>
        </form>
      )}
      {lists.map(l => (
        <ListRow
          key={l.id}
          list={l}
          active={l.id === activeListId}
          onClick={() => onSelectList(l.id)}
        />
      ))}
    </div>
  )
}

function ListRow({ list, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-2 py-1.5 rounded text-sm truncate ${
        active ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'
      }`}
    >
      {list.icon || '📝'} {list.name}
    </button>
  )
}
