import { useState } from 'react';
import Outline from './Outline';
import Backlinks from './Backlinks';

export default function NotesRightPane({ note, onSelect }) {
  const [tab, setTab] = useState('outline');

  if (!note) {
    return (
      <aside className="hidden md:flex md:w-80 flex-col border-l border-line-1 bg-surface-1 text-sm text-ink-3 items-center justify-center">
        No note
      </aside>
    );
  }

  return (
    <aside className="hidden md:flex md:w-80 flex-col border-l border-line-1 bg-surface-1">
      <div className="flex border-b border-line-1 bg-surface-2 text-xs">
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
