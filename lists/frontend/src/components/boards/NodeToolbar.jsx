import { useEffect, useMemo, useRef, useState } from 'react';
import { getLists, getNotes } from '../../api';

function Picker({ kind, onPick, onClose, onDragStart }) {
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
      <div className="board-picker-hint">Click to drop at center · drag to place</div>
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
            draggable
            onDragStart={(e) => onDragStart(e, kind, it)}
            onClick={() => onPick(it)}
            title={(kind === 'list' ? it.name : it.title) || ''}
          >
            <span className="board-picker-item-icon">{kind === 'list' ? '📋' : '📄'}</span>
            <span className="board-picker-item-label">
              {kind === 'list' ? (it.name || 'Untitled list') : (it.title || 'Untitled note')}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function NodeToolbar({
  onAddCard,
  onAddList,
  onAddNote,
  onDragStartNew,
}) {
  const [open, setOpen] = useState(null); // 'list' | 'note' | null

  const handlePick = (kind) => (item) => {
    if (kind === 'list') onAddList(item);
    else onAddNote(item);
    setOpen(null);
  };

  const handleDragStart = (kind, item) => (e) => {
    onDragStartNew(e, { kind, item });
  };

  return (
    <div className="board-toolbar" onClick={(e) => e.stopPropagation()}>
      <button
        className="board-toolbar-btn"
        draggable
        onDragStart={(e) => onDragStartNew(e, { kind: 'card' })}
        onClick={() => { setOpen(null); onAddCard(); }}
        title="Add card · click for center, drag to place"
      >
        <span className="board-toolbar-icon">🗒️</span>
        <span>New card</span>
      </button>
      <div style={{ position: 'relative' }}>
        <button
          className="board-toolbar-btn"
          onClick={() => setOpen((v) => (v === 'list' ? null : 'list'))}
          title="Embed an existing list"
        >
          <span className="board-toolbar-icon">📋</span>
          <span>Add list ▾</span>
        </button>
        {open === 'list' && (
          <Picker
            kind="list"
            onPick={handlePick('list')}
            onClose={() => setOpen(null)}
            onDragStart={(e, kind, item) => { onDragStartNew(e, { kind, item }); setOpen(null); }}
          />
        )}
      </div>
      <div style={{ position: 'relative' }}>
        <button
          className="board-toolbar-btn"
          onClick={() => setOpen((v) => (v === 'note' ? null : 'note'))}
          title="Embed an existing note"
        >
          <span className="board-toolbar-icon">📄</span>
          <span>Add note ▾</span>
        </button>
        {open === 'note' && (
          <Picker
            kind="note"
            onPick={handlePick('note')}
            onClose={() => setOpen(null)}
            onDragStart={(e, kind, item) => { onDragStartNew(e, { kind, item }); setOpen(null); }}
          />
        )}
      </div>
    </div>
  );
}
