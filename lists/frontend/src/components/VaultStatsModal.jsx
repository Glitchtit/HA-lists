import { useEffect, useState } from 'react';
import * as api from '../api';

function Stat({ label, value, icon }) {
  return (
    <div className="rounded-xl border border-line-1 bg-surface-2 px-4 py-3">
      <div className="text-2xl mb-0.5">{icon}</div>
      <div className="text-xl font-display text-ink-1 tabular-nums">
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      <div className="text-[11px] uppercase tracking-wider text-ink-4">{label}</div>
    </div>
  );
}

export default function VaultStatsModal({ open, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setError(null);
    setData(null);
    api.getVaultStats()
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setError(e.message || 'Failed to load stats'); });
    return () => { cancelled = true; };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose && onClose(); }}
    >
      <div className="w-full max-w-2xl flex flex-col bg-surface-1 border border-line-1 rounded-2xl shadow-glow-cobalt overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-line-1">
          <div className="text-base font-display text-ink-1">📊 Vault stats</div>
          <button onClick={onClose} className="text-ink-3 hover:text-ink-1" aria-label="Close">✕</button>
        </div>
        <div className="p-4">
          {error && <div className="text-sm text-semantic-danger">{error}</div>}
          {!data && !error && <div className="text-sm text-ink-3">Loading…</div>}
          {data && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <Stat icon="📝" label="Notes" value={data.notes_active} />
              <Stat icon="🗄️" label="Archived" value={data.notes_archived} />
              <Stat icon="📁" label="Folders" value={data.folders} />
              <Stat icon="📋" label="Lists" value={data.lists} />
              <Stat icon="🗂️" label="Boards" value={data.boards} />
              <Stat icon="🏷️" label="Distinct tags" value={data.tags} />
              <Stat icon="🔗" label="Wikilinks" value={data.wikilinks} />
              <Stat icon="🪪" label="Aliases" value={data.aliases} />
              <Stat icon="✍️" label="Words" value={data.words} />
              <Stat icon="🔤" label="Characters" value={data.characters} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
