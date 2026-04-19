import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { searchAll } from '../../api';

const TYPE_META = {
  board: { icon: '🧩', label: 'Board' },
  note: { icon: '📝', label: 'Note' },
  card: { icon: '🃏', label: 'Card' },
};

export default function CommandPalette({ open, onClose, onJump }) {
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(0);
  const inputRef = useRef(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    setQ('');
    setResults([]);
    setActive(0);
    const id = setTimeout(() => inputRef.current?.focus(), 0);
    return () => clearTimeout(id);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const query = q.trim();
    if (!query) {
      setResults([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    debounceRef.current = setTimeout(() => {
      searchAll(query, 20)
        .then((data) => {
          setResults(data?.results || []);
          setActive(0);
        })
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, 150);
    return () => clearTimeout(debounceRef.current);
  }, [q, open]);

  const jump = useCallback((r) => {
    if (!r) return;
    if (r.type === 'board') onJump({ kind: 'board', id: r.id });
    else if (r.type === 'note') onJump({ kind: 'note', id: r.id });
    else if (r.type === 'card' && r.board_id) onJump({ kind: 'board', id: r.board_id });
    onClose();
  }, [onJump, onClose]);

  const onKeyDown = useCallback((e) => {
    if (e.key === 'Escape') { onClose(); return; }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => Math.min(results.length - 1, a + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      jump(results[active]);
    }
  }, [onClose, results, active, jump]);

  const hint = useMemo(() => {
    if (loading) return 'Searching…';
    if (!q.trim()) return 'Type to search boards, notes, and cards';
    if (!results.length) return 'No matches';
    return `${results.length} result${results.length === 1 ? '' : 's'}`;
  }, [loading, q, results.length]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4"
      style={{ background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(2px)' }}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="w-full max-w-2xl rounded-xl overflow-hidden border border-line-1 shadow-2xl"
        style={{ background: 'var(--surface-2, #1f2937)' }}
      >
        <div className="flex items-center gap-2 px-3 py-2 border-b border-line-1">
          <span className="text-lg">🔍</span>
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Search everything…"
            className="flex-1 bg-transparent outline-none text-ink-1 placeholder-ink-3 text-base"
          />
          <span className="text-xs text-ink-3">Esc</span>
        </div>
        <div className="max-h-[50vh] overflow-y-auto">
          {results.map((r, i) => {
            const meta = TYPE_META[r.type] || { icon: '•', label: r.type };
            const activeRow = i === active;
            return (
              <button
                key={`${r.type}-${r.id}`}
                onMouseEnter={() => setActive(i)}
                onClick={() => jump(r)}
                className={`w-full text-left px-3 py-2 flex items-start gap-3 ${
                  activeRow ? 'bg-surface-3' : 'hover:bg-surface-3'
                }`}
              >
                <span className="text-xl leading-tight mt-0.5">{meta.icon}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-ink-1 font-medium">{r.title}</span>
                    <span className="text-[10px] uppercase tracking-wide text-ink-3 px-1.5 py-0.5 rounded bg-surface-1 border border-line-1">
                      {meta.label}
                    </span>
                  </div>
                  {r.snippet && (
                    <div className="text-xs text-ink-3 truncate mt-0.5">{r.snippet}</div>
                  )}
                </div>
              </button>
            );
          })}
        </div>
        <div className="px-3 py-1.5 text-xs text-ink-3 border-t border-line-1 flex items-center justify-between">
          <span>{hint}</span>
          <span>↑↓ navigate · ↵ open</span>
        </div>
      </div>
    </div>
  );
}
