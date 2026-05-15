import { useEffect, useState } from 'react';
import { getOutgoingLinks } from '../../api';

export default function OutgoingLinks({ noteId, onSelect }) {
  const [state, setState] = useState({ loading: true, items: [], error: null });

  useEffect(() => {
    let cancelled = false;
    if (noteId == null) { setState({ loading: false, items: [], error: null }); return; }
    setState({ loading: true, items: [], error: null });
    getOutgoingLinks(noteId)
      .then((items) => { if (!cancelled) setState({ loading: false, items, error: null }); })
      .catch((e) => {
        if (cancelled) return;
        if (e.response?.status === 404) setState({ loading: false, items: [], error: null });
        else setState({ loading: false, items: [], error: e.message || 'Failed to load outgoing links' });
      });
    return () => { cancelled = true; };
  }, [noteId]);

  return (
    <div className="flex h-full flex-col">
      <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-ink-3 border-b border-line-1">
        Outgoing links
      </div>
      <div className="flex-1 overflow-auto p-2">
        {state.loading && <div className="text-xs text-ink-3">Loading…</div>}
        {!state.loading && state.error && (
          <div className="text-xs text-semantic-danger">{state.error}</div>
        )}
        {!state.loading && !state.error && state.items.length === 0 && (
          <div className="text-xs text-ink-3 italic">No outgoing links yet</div>
        )}
        {!state.loading && state.items.length > 0 && (
          <ul className="space-y-1">
            {state.items.map((it, i) => (
              <li key={`${it.target_title}-${i}`}>
                <button
                  type="button"
                  disabled={!it.note_id}
                  onClick={() => it.note_id && onSelect && onSelect(it.note_id)}
                  className={`group w-full rounded-md border border-transparent px-2 py-1.5 text-left ${
                    it.note_id ? 'hover:border-line-1 hover:bg-surface-2' : 'opacity-70 cursor-default'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm text-ink-1 flex items-center gap-1">
                      <span>{it.resolved_icon || (it.note_id ? '📄' : '❓')}</span>
                      <span className="truncate">{it.resolved_title || it.target_title}</span>
                    </span>
                    <span className={`shrink-0 rounded-full border border-line-1 px-1.5 py-0.5 text-[10px] uppercase tracking-wider ${
                      it.link_type === 'embed' ? 'bg-brand-orange/15 text-brand-orange-300' : 'bg-surface-2 text-ink-3'
                    }`}>
                      {it.link_type}
                    </span>
                  </div>
                  {!it.note_id && (
                    <div className="mt-0.5 text-[11px] text-ink-4 italic">unresolved</div>
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
