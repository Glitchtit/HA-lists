const SHORTCUTS = [
  { group: 'Navigation', items: [
    { keys: ['Ctrl', 'K'], desc: 'Open command palette / global search' },
    { keys: ['Ctrl', 'N'], desc: 'New note' },
    { keys: ['Ctrl', 'Alt', 'T'], desc: "Open today's daily note" },
    { keys: ['Ctrl', 'Enter'], desc: 'Toggle preview/split in note editor' },
    { keys: ['?'], desc: 'Open this shortcuts help' },
    { keys: ['Esc'], desc: 'Close palettes / modals' },
  ]},
  { group: 'Editing', items: [
    { keys: ['F2'], desc: 'Rename selected folder / list / note / board' },
    { keys: ['Del'], desc: 'Delete selected entity (with confirm)' },
    { keys: ['Ctrl', 'D'], desc: 'Duplicate folder / list / item' },
  ]},
  { group: 'Boards (canvas)', items: [
    { keys: ['t'], desc: 'Open template picker at cursor' },
    { keys: ['c'], desc: 'Quick-capture a blank card at cursor' },
    { keys: ['Ctrl', 'V'], desc: 'Paste image / file as a node' },
  ]},
];

function Key({ children }) {
  return (
    <kbd className="rounded border border-line-1 bg-surface-3 px-1.5 py-0.5 text-[11px] font-mono text-ink-1 shadow-sm">
      {children}
    </kbd>
  );
}

export default function HotkeysModal({ open, onClose }) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose && onClose(); }}
    >
      <div className="w-full max-w-lg max-h-[80vh] flex flex-col bg-surface-1 border border-line-1 rounded-2xl shadow-glow-cobalt overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-line-1">
          <div className="text-base font-display text-ink-1">⌨️ Keyboard shortcuts</div>
          <button onClick={onClose} className="text-ink-3 hover:text-ink-1" aria-label="Close">✕</button>
        </div>
        <div className="flex-1 overflow-auto px-4 py-3 space-y-4">
          {SHORTCUTS.map((sect) => (
            <section key={sect.group}>
              <h3 className="mb-2 text-[11px] uppercase tracking-wider text-ink-4">{sect.group}</h3>
              <ul className="space-y-1">
                {sect.items.map((s, i) => (
                  <li key={i} className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-ink-2">{s.desc}</span>
                    <span className="shrink-0 flex items-center gap-1">
                      {s.keys.map((k, j) => (
                        <span key={j} className="flex items-center gap-1">
                          {j > 0 && <span className="text-ink-4 text-xs">+</span>}
                          <Key>{k}</Key>
                        </span>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
        <div className="px-4 py-2 border-t border-line-1 text-xs text-ink-4">
          Press <Key>?</Key> anywhere outside an input to open this list.
        </div>
      </div>
    </div>
  );
}
