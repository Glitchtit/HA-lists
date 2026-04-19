import { useEffect, useState } from 'react';
import { getBacklinks } from '../../api';

export default function Backlinks({ noteId, onSelect }) {
  const [state, setState] = useState({ loading: true, items: null, error: null });

  useEffect(() => {
    let cancelled = false;
    if (noteId == null) {
      setState({ loading: false, items: [], error: null });
      return;
    }
    setState({ loading: true, items: null, error: null });
    getBacklinks(noteId)
      .then((data) => {
        if (cancelled) return;
        setState({ loading: false, items: Array.isArray(data) ? data : (data?.items || []), error: null });
      })
      .catch((e) => {
        if (cancelled) return;
        if (e?.response?.status === 404) {
          setState({ loading: false, items: [], error: null });
        } else {
          setState({ loading: false, items: [], error: e?.message || 'Failed to load backlinks' });
        }
      });
    return () => { cancelled = true; };
  }, [noteId]);

  return (
    <div className="flex h-full flex-col border-l border-line-1 bg-surface-1">
      <div className="border-b border-line-1 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-ink-3">
        Backlinks
      </div>
      <div className="flex-1 overflow-auto p-2">
        {state.loading && <div className="text-xs text-ink-3">Loading…</div>}
        {!state.loading && state.error && (
          <div className="text-xs text-semantic-danger">{state.error}</div>
        )}
        {!state.loading && !state.error && (!state.items || state.items.length === 0) && (
          <div className="text-xs text-ink-3">No backlinks yet</div>
        )}
        {!state.loading && state.items && state.items.length > 0 && (
          <ul className="space-y-1">
            {state.items.map((b, i) => (
              <li key={b.id ?? b.note_id ?? i}>
                <button
                  type="button"
                  onClick={() => onSelect && onSelect(b.id ?? b.note_id)}
                  className="group w-full rounded-md border border-transparent px-2 py-1.5 text-left hover:border-line-1 hover:bg-surface-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm text-ink-1">{b.title || 'Untitled'}</span>
                    {b.link_type && (
                      <span className="shrink-0 rounded-full border border-line-1 bg-surface-2 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-ink-3 group-hover:bg-surface-3">
                        {b.link_type}
                      </span>
                    )}
                  </div>
                  {b.snippet && (
                    <div className="mt-0.5 line-clamp-2 text-xs text-ink-3">{b.snippet}</div>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
