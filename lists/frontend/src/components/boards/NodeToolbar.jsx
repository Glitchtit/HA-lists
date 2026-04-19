import { useEffect, useMemo, useRef, useState } from 'react';
import { getLists, getNotes, listBoards } from '../../api';

function Picker({ kind, onPick, onClose, onDragStart, excludeId }) {
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const rootRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const fetcher = kind === 'list' ? getLists : kind === 'note' ? getNotes : listBoards;
    setLoading(true);
    fetcher()
      .then((data) => {
        if (cancelled) return;
        const all = Array.isArray(data) ? data : (data?.items || []);
        const filtered = excludeId != null
          ? all.filter((it) => it.id !== excludeId)
          : all;
        setItems(filtered);
        setLoading(false);
      })
      .catch(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [kind, excludeId]);

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
      const label = kind === 'note' ? (it.title || '') : (it.name || '');
      return label.toLowerCase().includes(q);
    });
  }, [items, query, kind]);

  const placeholder = kind === 'list'
    ? 'Search lists…'
    : kind === 'note' ? 'Search notes…' : 'Search boards…';
  const emptyLabel = kind === 'list'
    ? 'lists'
    : kind === 'note' ? 'notes' : 'boards';
  const itemIcon = kind === 'list' ? '📋' : kind === 'note' ? '📄' : '🗂️';

  return (
    <div ref={rootRef} className="board-picker" role="listbox">
      <div className="board-picker-hint">Click to drop at center · drag to place</div>
      <input
        autoFocus
        className="board-picker-search"
        placeholder={placeholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Escape') onClose(); }}
      />
      <div className="board-picker-list">
        {loading && <div className="board-picker-empty">Loading…</div>}
        {!loading && filtered.length === 0 && (
          <div className="board-picker-empty">No {emptyLabel} found.</div>
        )}
        {!loading && filtered.map((it) => (
          <button
            key={it.id}
            className="board-picker-item"
            draggable
            onDragStart={(e) => onDragStart(e, kind, it)}
            onClick={() => onPick(it)}
            title={(kind === 'note' ? it.title : it.name) || ''}
          >
            <span className="board-picker-item-icon">{it.icon || itemIcon}</span>
            <span className="board-picker-item-label">
              {kind === 'note'
                ? (it.title || 'Untitled note')
                : (it.name || (kind === 'list' ? 'Untitled list' : 'Untitled board'))}
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
  onAddBoard,
  onAddGroup,
  onUploadFiles,
  onDragStartNew,
  currentBoardId,
  onOpenTemplates,
}) {
  const [open, setOpen] = useState(null); // 'list' | 'note' | 'board' | null
  const fileInputRef = useRef(null);

  const handlePick = (kind) => (item) => {
    if (kind === 'list') onAddList(item);
    else if (kind === 'note') onAddNote(item);
    else if (kind === 'board') onAddBoard?.(item);
    setOpen(null);
  };

  const onPickFiles = (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length && onUploadFiles) onUploadFiles(files);
    // reset so selecting the same file again re-fires change
    e.target.value = '';
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
      <div style={{ position: 'relative' }}>
        <button
          className="board-toolbar-btn"
          onClick={() => setOpen((v) => (v === 'board' ? null : 'board'))}
          title="Open another board as a portal on this canvas"
        >
          <span className="board-toolbar-icon">🗂️</span>
          <span>Add board ▾</span>
        </button>
        {open === 'board' && (
          <Picker
            kind="board"
            onPick={handlePick('board')}
            onClose={() => setOpen(null)}
            onDragStart={(e, kind, item) => { onDragStartNew(e, { kind, item }); setOpen(null); }}
            excludeId={currentBoardId}
          />
        )}
      </div>
      <button
        className="board-toolbar-btn"
        draggable
        onDragStart={(e) => onDragStartNew(e, { kind: 'group' })}
        onClick={() => { setOpen(null); onAddGroup?.(); }}
        title="Add group frame · click for center, drag to place"
      >
        <span className="board-toolbar-icon">📦</span>
        <span>New group</span>
      </button>
      <button
        className="board-toolbar-btn"
        onClick={() => { setOpen(null); onOpenTemplates?.(); }}
        title="Insert a card from a template (shortcut: t)"
      >
        <span className="board-toolbar-icon">🧩</span>
        <span>Templates</span>
      </button>
      <button
        className="board-toolbar-btn"
        onClick={() => { setOpen(null); fileInputRef.current?.click(); }}
        title="Upload image or file · also: paste or drop onto the canvas"
      >
        <span className="board-toolbar-icon">📎</span>
        <span>Upload</span>
      </button>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        style={{ display: 'none' }}
        onChange={onPickFiles}
      />
    </div>
  );
}
