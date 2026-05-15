import { useState } from 'react';

export default function TabBar({ tabs, activeEntity, lists, notes, boards, onSelect, onClose, onTogglePin }) {
  const [menu, setMenu] = useState(null);
  if (!tabs || tabs.length === 0) return null;

  function meta(t) {
    if (t.kind === 'list') {
      const l = lists.find((x) => x.id === t.id);
      return { title: l?.name || `List #${t.id}`, icon: l?.icon || '📋', missing: !l };
    }
    if (t.kind === 'note') {
      const n = notes.find((x) => x.id === t.id);
      return { title: n?.title || `Note #${t.id}`, icon: n?.icon || '📄', missing: !n };
    }
    if (t.kind === 'board') {
      const b = boards.find((x) => x.id === t.id);
      return { title: b?.name || `Board #${t.id}`, icon: b?.icon || '🗂️', missing: !b };
    }
    return { title: '?', icon: '?', missing: true };
  }

  // Pinned tabs render before unpinned tabs while preserving the open order.
  const sorted = [
    ...tabs.filter((t) => t.pinned),
    ...tabs.filter((t) => !t.pinned),
  ];

  return (
    <>
      <div className="flex items-center gap-1 overflow-x-auto border-b border-line-1 bg-surface-2 px-2 py-1">
        {sorted.map((t) => {
          const m = meta(t);
          const isActive = activeEntity?.kind === t.kind && activeEntity.id === t.id;
          return (
            <div
              key={`${t.kind}-${t.id}`}
              onContextMenu={(e) => {
                e.preventDefault();
                setMenu({ tab: t, x: e.clientX, y: e.clientY });
              }}
              className={`group flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs whitespace-nowrap max-w-[220px] ${
                isActive
                  ? 'bg-surface-1 border-brand-cobalt text-ink-1'
                  : 'bg-surface-2 border-line-1 text-ink-3 hover:bg-surface-3 hover:text-ink-1'
              } ${m.missing ? 'opacity-60' : ''}`}
            >
              <button
                type="button"
                onClick={() => onSelect && onSelect({ kind: t.kind, id: t.id })}
                className="flex items-center gap-1 truncate"
                title={m.title}
              >
                {t.pinned && <span className="shrink-0 text-brand-orange">📌</span>}
                <span className="shrink-0">{m.icon}</span>
                <span className="truncate">{m.title}</span>
              </button>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onClose && onClose(t); }}
                className="shrink-0 ml-1 text-ink-4 hover:text-semantic-danger opacity-60 group-hover:opacity-100"
                aria-label={`Close ${m.title}`}
                title="Close tab"
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>
      {menu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setMenu(null)}
          onContextMenu={(e) => { e.preventDefault(); setMenu(null); }}
        >
          <div
            style={{ position: 'fixed', left: menu.x, top: menu.y }}
            className="rounded-lg border border-line-1 bg-surface-2 py-1 shadow-glow-cobalt min-w-[160px]"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="block w-full px-3 py-1 text-left text-xs text-ink-1 hover:bg-surface-3"
              onClick={() => { onTogglePin && onTogglePin(menu.tab); setMenu(null); }}
            >
              {menu.tab.pinned ? '📌 Unpin tab' : '📌 Pin tab'}
            </button>
            <button
              className="block w-full px-3 py-1 text-left text-xs text-ink-1 hover:bg-surface-3"
              onClick={() => { onClose && onClose(menu.tab); setMenu(null); }}
            >
              ✕ Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}
