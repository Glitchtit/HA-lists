import { useEffect, useState } from 'react';
import NoteSource from './NoteSource';
import NotePreview from './NotePreview';

function toggleChecklistAt(body, offset) {
  if (typeof offset !== 'number' || offset < 0 || offset >= body.length) return body;
  // Find the nearest '[ ]' or '[x]' at or after the offset on that line.
  const lineStart = body.lastIndexOf('\n', offset) + 1;
  const lineEnd = body.indexOf('\n', offset);
  const end = lineEnd === -1 ? body.length : lineEnd;
  const line = body.slice(lineStart, end);
  const m = /\[( |x|X)\]/.exec(line);
  if (!m) return body;
  const absIdx = lineStart + m.index;
  const current = body[absIdx + 1];
  const replacement = current === ' ' ? 'x' : ' ';
  return body.slice(0, absIdx + 1) + replacement + body.slice(absIdx + 2);
}

export default function NoteEditor({
  note,
  onChange,
  onWikilinkClick,
  onEmbedFetch,
  mode: modeProp,
  onModeChange,
}) {
  const [modeState, setModeState] = useState('split'); // 'split' | 'source' | 'preview'
  const mode = modeProp ?? modeState;
  const setMode = (m) => { if (onModeChange) onModeChange(m); else setModeState(m); };
  const [draftTitle, setDraftTitle] = useState(note?.title || '');
  const [draftBody, setDraftBody] = useState(note?.body || '');

  useEffect(() => {
    setDraftTitle(note?.title || '');
    setDraftBody(note?.body || '');
  }, [note?.id]);

  const commitTitle = () => {
    if (!note) return;
    if ((draftTitle || '') !== (note.title || '')) {
      onChange && onChange({ title: draftTitle });
    }
  };
  const commitBody = (val) => {
    if (!note) return;
    const next = typeof val === 'string' ? val : draftBody;
    if (next !== (note.body || '')) {
      onChange && onChange({ body: next });
    }
  };

  const handleToggleChecklist = (offset) => {
    const next = toggleChecklistAt(draftBody, offset);
    if (next !== draftBody) {
      setDraftBody(next);
      onChange && onChange({ body: next });
    }
  };

  if (!note) {
    return (
      <div className="flex h-full items-center justify-center text-ink-3 text-sm">
        No note selected
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-line-1 bg-surface-1 px-4 py-2">
        <input
          className="min-w-0 flex-1 bg-transparent text-lg font-semibold text-ink-1 outline-none placeholder:text-ink-4"
          value={draftTitle}
          placeholder="Untitled note"
          onChange={(e) => setDraftTitle(e.target.value)}
          onBlur={commitTitle}
          onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur(); }}
        />
        <div className="flex overflow-hidden rounded-lg border border-line-1 bg-surface-2 text-xs">
          {['source', 'split', 'preview'].map((m) => (
            <button
              key={m}
              type="button"
              className={`px-3 py-1 transition-colors ${mode === m ? 'bg-brand-cobalt text-white' : 'text-ink-2 hover:bg-surface-3'}`}
              onClick={() => setMode(m)}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        {mode !== 'preview' && (
          <div className={`min-w-0 ${mode === 'split' ? 'w-1/2 border-r border-line-1' : 'w-full'}`}>
            <NoteSource
              value={draftBody}
              onChange={(v) => setDraftBody(v)}
              onBlur={(v) => commitBody(v)}
            />
          </div>
        )}
        {mode !== 'source' && (
          <div className={`min-w-0 overflow-auto px-6 py-4 ${mode === 'split' ? 'w-1/2' : 'w-full'}`}>
            <NotePreview
              body={draftBody}
              onWikilinkClick={onWikilinkClick}
              onEmbedResolve={onEmbedFetch}
              onToggleChecklist={handleToggleChecklist}
              visitedEmbeds={new Set(note.id != null ? [note.id] : [])}
            />
          </div>
        )}
      </div>
    </div>
  );
}
