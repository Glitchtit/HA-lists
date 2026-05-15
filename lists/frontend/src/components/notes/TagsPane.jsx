import { useEffect, useState } from 'react';
import * as api from '../../api';

export default function TagsPane({ onSelect }) {
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [notesById, setNotesById] = useState({});

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.getNoteTags()
      .then((t) => { if (!cancelled) { setTags(t); setError(null); } })
      .catch((e) => { if (!cancelled) setError(e.message || 'Failed to load tags'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  async function toggle(tag) {
    if (expanded === tag) { setExpanded(null); return; }
    setExpanded(tag);
    const entry = tags.find((t) => t.tag === tag);
    if (!entry) return;
    const missing = entry.note_ids.filter((id) => !notesById[id]);
    if (missing.length === 0) return;
    try {
      const fetched = await Promise.all(missing.map((id) => api.getNote(id).catch(() => null)));
      setNotesById((prev) => {
        const next = { ...prev };
        for (const n of fetched) {
          if (n) next[n.id] = n;
        }
        return next;
      });
    } catch {
      // ignore
    }
  }

  if (loading) return <div className="p-4 text-sm text-ink-3">Loading tags…</div>;
  if (error) return <div className="p-4 text-sm text-semantic-danger">{error}</div>;
  if (tags.length === 0) {
    return (
      <div className="p-4 text-sm text-ink-3 italic">
        No tags yet — add <code className="font-mono">#tag</code> in any note body to see them here
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <ul className="p-2 space-y-1">
        {tags.map((entry) => {
          const isOpen = expanded === entry.tag;
          return (
            <li key={entry.tag}>
              <button
                onClick={() => toggle(entry.tag)}
                className={`w-full flex items-center justify-between gap-2 px-2 py-1 text-sm rounded text-left ${
                  isOpen ? 'bg-brand-cobalt/15 text-ink-1' : 'text-ink-2 hover:bg-surface-3 hover:text-ink-1'
                }`}
              >
                <span className="truncate font-mono text-brand-cobalt-300">#{entry.tag}</span>
                <span className="shrink-0 text-xs text-ink-4 tabular-nums">{entry.count}</span>
              </button>
              {isOpen && (
                <ul className="ml-3 mt-1 mb-2 space-y-0.5 border-l border-line-1 pl-2">
                  {entry.note_ids.map((nid) => {
                    const n = notesById[nid];
                    return (
                      <li key={nid}>
                        <button
                          onClick={() => onSelect && onSelect(nid)}
                          className="w-full text-left px-2 py-0.5 text-xs rounded text-ink-3 hover:bg-surface-3 hover:text-ink-1 truncate"
                          title={n?.title || `Note ${nid}`}
                        >
                          {n ? (n.icon || '📄') : '…'} {n?.title || `Note ${nid}`}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
