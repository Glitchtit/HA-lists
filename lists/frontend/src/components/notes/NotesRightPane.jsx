import { useState } from 'react';
import Outline from './Outline';
import Backlinks from './Backlinks';

export default function NotesRightPane({ note, onSelect }) {
  const [tab, setTab] = useState('outline');
  const [visible, setVisible] = useState(false);

  // Collapsed: just show the toggle button
  if (!visible) {
    return (
      <aside className="hidden md:flex flex-col border-l border-line-1 bg-surface-1">
        <button
          type="button"
          title="Show outline & backlinks"
          onClick={() => setVisible(true)}
          className="p-2 text-ink-3 hover:text-ink-1 hover:bg-surface-3 transition-colors"
          style={{ writingMode: 'vertical-rl', fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', padding: '12px 6px' }}
        >
          ☰ Outline
        </button>
      </aside>
    );
  }

  if (!note) {
    return (
      <aside className="hidden md:flex md:w-72 flex-col border-l border-line-1 bg-surface-1 text-sm text-ink-3 items-center justify-center">
        <button
          type="button"
          title="Hide sidebar"
          onClick={() => setVisible(false)}
          className="absolute top-2 right-2 p-1 text-ink-3 hover:text-ink-1 hover:bg-surface-3 rounded transition-colors"
        >
          ✕
        </button>
        No note
      </aside>
    );
  }

  return (
    <aside className="hidden md:flex md:w-72 flex-col border-l border-line-1 bg-surface-1">
      <div className="flex items-center border-b border-line-1 bg-surface-2 text-xs">
        {['outline', 'backlinks'].map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`flex-1 px-3 py-2 uppercase tracking-wider transition-colors ${
              tab === t
                ? 'bg-surface-1 text-ink-1 border-b-2 border-brand-cobalt'
                : 'text-ink-3 hover:text-ink-1 hover:bg-surface-3'
            }`}
          >
            {t}
          </button>
        ))}
        <button
          type="button"
          title="Hide sidebar"
          onClick={() => setVisible(false)}
          className="px-2 py-2 text-ink-3 hover:text-ink-1 hover:bg-surface-3 transition-colors"
        >
          ✕
        </button>
      </div>
      <div className="flex-1 min-h-0 overflow-hidden">
        {tab === 'outline' ? (
          <Outline body={note.body || ''} />
        ) : (
          <Backlinks noteId={note.id} onSelect={onSelect} />
        )}
      </div>
    </aside>
  );
}
