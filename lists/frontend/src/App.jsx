import { useEffect, useState } from 'react'
import * as api from './api'
import Sidebar from './components/Sidebar'
import ItemList from './components/ItemList'
import ItemDetail from './components/ItemDetail'
import CompileDialog from './components/CompileDialog'

export default function App() {
  const [folders, setFolders] = useState([])
  const [lists, setLists] = useState([])
  const [items, setItems] = useState([])
  const [persons, setPersons] = useState([])
  const [activeListId, setActiveListId] = useState(null)
  const [activeItemId, setActiveItemId] = useState(null)
  const [error, setError] = useState(null)
  const [compileOpen, setCompileOpen] = useState(false)

  async function loadTopLevel() {
    try {
      const [f, l, p] = await Promise.all([
        api.getFolders(false),
        api.getLists(),
        api.getPersons(),
      ])
      setFolders(f)
      setLists(l)
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

  useEffect(() => { loadTopLevel() }, [])
  useEffect(() => { loadItems(activeListId) }, [activeListId])

  const activeList = lists.find(l => l.id === activeListId) || null

  return (
    <div className="h-full flex flex-col md:flex-row">
      <Sidebar
        folders={folders}
        lists={lists}
        activeListId={activeListId}
        onSelectList={id => { setActiveListId(id); setActiveItemId(null) }}
        onRefresh={loadTopLevel}
      />
      <ItemList
        list={activeList}
        items={items}
        activeItemId={activeItemId}
        onSelectItem={setActiveItemId}
        onRefresh={() => loadItems(activeListId)}
        onCompile={activeList ? () => setCompileOpen(true) : null}
      />
      <ItemDetail
        itemId={activeItemId}
        persons={persons}
        onChange={() => loadItems(activeListId)}
        onClose={() => setActiveItemId(null)}
      />
      {error && (
        <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-80 bg-red-900 text-red-100 px-3 py-2 rounded text-sm">
          {error}
        </div>
      )}
      {compileOpen && activeList && (
        <CompileDialog
          listId={activeList.id}
          listName={activeList.name}
          onClose={() => setCompileOpen(false)}
          onRefresh={() => loadItems(activeListId)}
        />
      )}
    </div>
  )
}
