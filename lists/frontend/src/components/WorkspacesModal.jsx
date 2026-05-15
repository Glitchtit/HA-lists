import { useEffect, useState } from 'react';

const STORAGE_KEY = 'lists_workspaces';

function loadWorkspaces() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveWorkspaces(ws) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(ws)); } catch {}
}

export default function WorkspacesModal({ open, onClose, tabs, activeEntity, onRestore }) {
  const [workspaces, setWorkspaces] = useState(() => loadWorkspaces());
  const [name, setName] = useState('');

  useEffect(() => {
    if (open) {
      setWorkspaces(loadWorkspaces());
      setName('');
    }
  }, [open]);

  if (!open) return null;

  function save() {
    const trimmed = name.trim();
    if (!trimmed) return;
    const next = [
      ...workspaces.filter((w) => w.name.toLowerCase() !== trimmed.toLowerCase()),
      { name: trimmed, tabs: tabs || [], activeEntity: activeEntity || null, savedAt: Date.now() },
    ].sort((a, b) => a.name.localeCompare(b.name));
    setWorkspaces(next);
    saveWorkspaces(next);
    setName('');
  }

  function remove(n) {
    const next = workspaces.filter((w) => w.name !== n);
    setWorkspaces(next);
    saveWorkspaces(next);
  }

  function restore(w) {
    onRestore && onRestore(w);
    onClose && onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose && onClose(); }}
    >
      <div className="w-full max-w-md flex flex-col bg-surface-1 border border-line-1 rounded-2xl shadow-glow-cobalt overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-line-1">
          <div className="text-base font-display text-ink-1">💼 Workspaces</div>
          <button onClick={onClose} className="text-ink-3 hover:text-ink-1" aria-label="Close">✕</button>
        </div>
        <div className="px-4 py-3 border-b border-line-1 flex gap-1">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Save current layout as…"
            className="flex-1 px-2 py-1 text-sm bg-surface-3 text-ink-1 rounded outline-none"
            onKeyDown={(e) => { if (e.key === 'Enter') save(); }}
          />
          <button
            onClick={save}
            disabled={!name.trim()}
            className="px-3 text-sm bg-brand-cobalt text-white rounded hover:bg-brand-cobalt-400 disabled:opacity-50"
          >
            Save
          </button>
        </div>
        <div className="flex-1 overflow-auto p-3 space-y-1 min-h-[120px]">
          {workspaces.length === 0 ? (
            <div className="text-sm text-ink-3 italic">
              No workspaces yet — open the tabs you want, name the layout above, and click Save.
            </div>
          ) : (
            workspaces.map((w) => (
              <div key={w.name} className="flex items-center justify-between gap-2 px-2 py-1.5 rounded bg-surface-2 hover:bg-surface-3">
                <button
                  onClick={() => restore(w)}
                  className="flex-1 text-left text-sm text-ink-1 truncate"
                  title={`${(w.tabs || []).length} tabs · saved ${new Date(w.savedAt || 0).toLocaleString()}`}
                >
                  {w.name}
                  <span className="ml-2 text-xs text-ink-4">{(w.tabs || []).length} tabs</span>
                </button>
                <button
                  onClick={() => remove(w.name)}
                  className="text-ink-4 hover:text-semantic-danger text-xs"
                  aria-label={`Delete workspace ${w.name}`}
                  title="Delete workspace"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
