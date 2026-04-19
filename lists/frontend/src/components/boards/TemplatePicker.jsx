import { useEffect, useMemo, useRef, useState } from 'react';
import { getBoardTemplates } from '../../api';

export default function TemplatePicker({ open, anchor, onPick, onClose }) {
  const [templates, setTemplates] = useState([]);
  const [q, setQ] = useState('');
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(true);
  const inputRef = useRef(null);
  const rootRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    setQ('');
    setActive(0);
    setLoading(true);
    getBoardTemplates()
      .then((data) => { setTemplates(Array.isArray(data) ? data : []); })
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false));
    const id = setTimeout(() => inputRef.current?.focus(), 0);
    return () => clearTimeout(id);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) onClose();
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open, onClose]);

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    if (!query) return templates;
    return templates.filter((t) =>
      (t.name || '').toLowerCase().includes(query)
      || (t.category || '').toLowerCase().includes(query),
    );
  }, [templates, q]);

  const onKeyDown = (e) => {
    if (e.key === 'Escape') { onClose(); return; }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => Math.min(filtered.length - 1, a + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const t = filtered[active];
      if (t) { onPick(t); onClose(); }
    }
  };

  if (!open) return null;

  const left = anchor?.x ?? 80;
  const top = anchor?.y ?? 80;

  return (
    <div
      ref={rootRef}
      className="board-template-picker"
      style={{ left, top }}
    >
      <input
        ref={inputRef}
        value={q}
        onChange={(e) => { setQ(e.target.value); setActive(0); }}
        onKeyDown={onKeyDown}
        placeholder="Search templates…"
        className="board-template-search"
      />
      <div className="board-template-list">
        {loading && <div className="board-template-empty">Loading…</div>}
        {!loading && filtered.length === 0 && (
          <div className="board-template-empty">No templates match.</div>
        )}
        {!loading && filtered.map((t, i) => (
          <button
            key={t.id}
            className={`board-template-item ${i === active ? 'active' : ''}`}
            onMouseEnter={() => setActive(i)}
            onClick={() => { onPick(t); onClose(); }}
          >
            <span className="board-template-icon">{t.icon || '🗒️'}</span>
            <div className="min-w-0 flex-1 text-left">
              <div className="board-template-name">{t.name}</div>
              <div className="board-template-cat">{t.category}</div>
            </div>
          </button>
        ))}
      </div>
      <div className="board-template-hint">↑↓ navigate · ↵ insert · esc close</div>
    </div>
  );
}
