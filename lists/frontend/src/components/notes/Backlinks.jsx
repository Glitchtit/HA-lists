import { useEffect, useState } from 'react';
import { getBacklinks, getUnlinkedMentions } from '../../api';

function Item({ b, onSelect }) {
  return (
    <li>
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
  );
}

export default function Backlinks({ noteId, onSelect }) {
  const [state, setState] = useState({ loading: true, links: [], unlinked: [], error: null });

  useEffect(() => {
    let cancelled = false;
    if (noteId == null) {
      setState({ loading: false, links: [], unlinked: [], error: null });
      return;
    }
    setState({ loading: true, links: [], unlinked: [], error: null });
    Promise.all([
      getBacklinks(noteId).catch((e) => (e?.response?.status === 404 ? [] : Promise.reject(e))),
      getUnlinkedMentions(noteId).catch((e) => (e?.response?.status === 404 ? [] : Promise.reject(e))),
    ])
      .then(([links, unlinked]) => {
        if (cancelled) return;
        setState({
          loading: false,
          links: Array.isArray(links) ? links : (links?.items || []),
          unlinked: Array.isArray(unlinked) ? unlinked : [],
          error: null,
        });
      })
      .catch((e) => {
        if (cancelled) return;
        setState({ loading: false, links: [], unlinked: [], error: e?.message || 'Failed to load backlinks' });
      });
    return () => { cancelled = true; };
  }, [noteId]);

  const pickId = (b) => b.id ?? b.note_id;

  return (
    <div className="flex h-full flex-col border-l border-line-1 bg-surface-1">
      <div className="flex-1 overflow-auto p-2">
        {state.loading && <div className="text-xs text-ink-3">Loading…</div>}
        {!state.loading && state.error && (
          <div className="text-xs text-semantic-danger">{state.error}</div>
        )}
        {!state.loading && !state.error && (
          <>
            <div className="px-1 pt-1 pb-2 text-xs font-semibold uppercase tracking-wider text-ink-3">
              Backlinks
            </div>
            {state.links.length === 0 ? (
              <div className="text-xs text-ink-3 italic px-1 pb-2">No backlinks yet</div>
            ) : (
              <ul className="space-y-1 mb-3">
                {state.links.map((b, i) => (
                  <Item key={`l-${pickId(b) ?? i}`} b={b} onSelect={onSelect} />
                ))}
              </ul>
            )}
            <div className="px-1 pt-1 pb-2 text-xs font-semibold uppercase tracking-wider text-ink-3 border-t border-line-1">
              Unlinked mentions
            </div>
            {state.unlinked.length === 0 ? (
              <div className="text-xs text-ink-3 italic px-1">None</div>
            ) : (
              <ul className="space-y-1">
                {state.unlinked.map((b, i) => (
                  <Item key={`u-${pickId(b) ?? i}`} b={b} onSelect={onSelect} />
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </div>
  );
}
