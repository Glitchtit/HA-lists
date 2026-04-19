import { useEffect, useMemo, useRef, useState } from 'react';
import { getLists, getNotes } from '../../api';

function Picker({ kind, onPick, onClose }) {
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const rootRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const fetcher = kind === 'list' ? getLists : getNotes;
    setLoading(true);
    fetcher()
      .then((data) => {
        if (cancelled) return;
        setItems(Array.isArray(data) ? data : (data?.items || []));
        setLoading(false);
      })
      .catch(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [kind]);

  useEffect(() => {
    function handleDown(e) {
      if (rootRef.current && !rootRef.current.contains(e.target)) onClose();
    }
    document.addEventListener('mousedown', handleDown);
    return () => document.removeEventListener('mousedown', handleDown);
  }, [onClose]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) => {
      const label = kind === 'list' ? (it.name || '') : (it.title || '');
      return label.toLowerCase().includes(q);
    });
  }, [items, query, kind]);

  return (
    <div ref={rootRef} className="board-picker" role="listbox">
      <input
        autoFocus
        className="board-picker-search"
        placeholder={kind === 'list' ? 'Search lists…' : 'Search notes…'}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Escape') onClose(); }}
      />
      <div className="board-picker-list">
        {loading && <div className="board-picker-empty">Loading…</div>}
        {!loading && filtered.length === 0 && (
          <div className="board-picker-empty">No {kind === 'list' ? 'lists' : 'notes'} found.</div>
        )}
        {!loading && filtered.map((it) => (
          <button
            key={it.id}
            className="board-picker-item"
            onClick={() => onPick(it)}
            title={kind === 'list' ? it.name : it.title}
          >
            {kind === 'list' ? (it.name || 'Untitled list') : (it.title || 'Untitled note')}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function NodeToolbar({ onAddCard, onAddList, onAddNote, connectLoose, onToggleConnect }) {
  const [open, setOpen] = useState(null); // 'list' | 'note' | null

  const handlePick = (kind) => (item) => {
    if (kind === 'list') onAddList(item);
    else onAddNote(item);
    setOpen(null);
  };

  return (
    <div className="board-toolbar" onClick={(e) => e.stopPropagation()}>
      <button onClick={() => { setOpen(null); onAddCard(); }}>+ Card</button>
      <div style={{ position: 'relative' }}>
        <button onClick={() => setOpen((v) => (v === 'list' ? null : 'list'))}>+ List</button>
        {open === 'list' && <Picker kind="list" onPick={handlePick('list')} onClose={() => setOpen(null)} />}
      </div>
      <div style={{ position: 'relative' }}>
        <button onClick={() => setOpen((v) => (v === 'note' ? null : 'note'))}>+ Note</button>
        {open === 'note' && <Picker kind="note" onPick={handlePick('note')} onClose={() => setOpen(null)} />}
      </div>
      <button
        className={connectLoose ? 'active' : ''}
        onClick={onToggleConnect}
        title="Toggle loose connection mode (drag between any handles)"
      >
        {connectLoose ? '⇄ Connect: Loose' : '⇄ Connect: Strict'}
      </button>
    </div>
  );
}
