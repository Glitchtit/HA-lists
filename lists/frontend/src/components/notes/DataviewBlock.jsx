import { useEffect, useState } from 'react';
import * as api from '../../api';

function parseDataview(text) {
  const params = {};
  let warn = null;
  for (const raw of String(text || '').split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('//') || line.startsWith('#')) continue;
    // Supported one-liners
    let m = /^tag\s*[:=]\s*"?([\w/-]+)"?$/.exec(line);
    if (m) { params.tag = m[1]; continue; }
    m = /^folder_id\s*[:=]\s*(null|\d+)$/.exec(line);
    if (m) { params.folder_id = m[1] === 'null' ? null : Number(m[1]); continue; }
    m = /^limit\s*[:=]\s*(\d+)$/.exec(line);
    if (m) { params.limit = Number(m[1]); continue; }
    m = /^sort\s*[:=]\s*(title|updated|created)$/.exec(line);
    if (m) { params.sort = m[1]; continue; }
    warn = warn || `Ignored: ${line}`;
  }
  return { params, warn };
}

export default function DataviewBlock({ code, onSelect }) {
  const [state, setState] = useState({ loading: true, rows: [], error: null });
  const { params, warn } = parseDataview(code);

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, rows: [], error: null });
    api.queryNotes(params)
      .then((rows) => { if (!cancelled) setState({ loading: false, rows, error: null }); })
      .catch((e) => { if (!cancelled) setState({ loading: false, rows: [], error: e.message || 'Query failed' }); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(params)]);

  return (
    <div className="my-2 rounded-lg border border-brand-cobalt-400/40 bg-surface-2 px-3 py-2">
      <div className="mb-1 flex items-center justify-between text-[10px] uppercase tracking-wider text-ink-4">
        <span>🔍 Dataview</span>
        <span className="font-mono text-ink-3">{Object.keys(params).length ? JSON.stringify(params) : 'all'}</span>
      </div>
      {warn && <div className="text-xs text-semantic-warning mb-1">{warn}</div>}
      {state.loading && <div className="text-xs text-ink-3">Loading…</div>}
      {state.error && <div className="text-xs text-semantic-danger">{state.error}</div>}
      {!state.loading && !state.error && state.rows.length === 0 && (
        <div className="text-xs text-ink-3 italic">No notes match this query.</div>
      )}
      {!state.loading && state.rows.length > 0 && (
        <ul className="space-y-0.5">
          {state.rows.map((n) => (
            <li key={n.id}>
              <button
                type="button"
                onClick={() => onSelect && onSelect(n.id)}
                className="flex items-center gap-2 w-full text-left px-1.5 py-0.5 rounded hover:bg-surface-3 text-sm text-ink-2"
              >
                <span className="shrink-0">{n.icon || '📄'}</span>
                <span className="truncate">{n.title || 'Untitled'}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
