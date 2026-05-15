import { useState } from 'react';

const TONES = ['neutral', 'professional', 'casual', 'concise', 'friendly', 'technical'];

function safeFilename(name) {
  return String(name || 'Untitled')
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 120) || 'Untitled';
}

function exportNote(note) {
  if (!note) return;
  const title = note.title || 'Untitled note';
  const body = note.body || '';
  // Prepend an H1 if the body doesn't already start with the title as a heading.
  const startsWithTitle = body.split(/\r?\n/, 1)[0]?.trim() === `# ${title}`.trim();
  const content = startsWithTitle ? body : `# ${title}\n\n${body}`;
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${safeFilename(title)}.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function Spinner() {
  return (
    <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-ink-3 border-t-transparent" />
  );
}

function Modal({ open, onClose, title, children }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-xl border border-line-1 bg-surface-1 p-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-semibold text-ink-1">{title}</div>
          <button type="button" onClick={onClose} className="text-ink-3 hover:text-ink-1">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export default function NoteToolbar({ note, onAction, lists = [] }) {
  const [busy, setBusy] = useState(null);
  const [continuePrompt, setContinuePrompt] = useState('');
  const [continueOpen, setContinueOpen] = useState(false);
  const [tone, setTone] = useState('neutral');
  const [listPickerOpen, setListPickerOpen] = useState(false);

  const run = async (kind, args) => {
    if (!onAction || busy) return;
    setBusy(kind);
    try {
      await onAction(kind, args);
    } finally {
      setBusy(null);
    }
  };

  const btn = (kind, label, extra) => (
    <button
      key={kind}
      type="button"
      disabled={!!busy}
      onClick={extra || (() => run(kind))}
      className="inline-flex items-center gap-1.5 rounded-md border border-line-1 bg-surface-2 px-2.5 py-1 text-xs text-ink-2 hover:bg-surface-3 disabled:opacity-50"
    >
      {busy === kind ? <Spinner /> : null}
      <span>{label}</span>
    </button>
  );

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-line-1 bg-surface-1 px-4 py-2">
      <span className="text-[11px] uppercase tracking-wider text-ink-3 mr-1">AI</span>
      {btn('summarize', 'Summarize')}
      {btn('continue', 'Continue', () => setContinueOpen(true))}

      <div className="inline-flex items-center gap-1 rounded-md border border-line-1 bg-surface-2 px-2 py-1 text-xs">
        <label className="text-ink-3">Tone</label>
        <select
          className="bg-transparent text-ink-2 outline-none"
          value={tone}
          onChange={(e) => setTone(e.target.value)}
        >
          {TONES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <button
          type="button"
          disabled={!!busy}
          onClick={() => run('rewrite', { tone })}
          className="ml-1 rounded bg-surface-3 px-1.5 py-0.5 text-[11px] text-ink-1 hover:bg-surface-4 disabled:opacity-50"
        >
          {busy === 'rewrite' ? <Spinner /> : 'Rewrite'}
        </button>
      </div>

      {btn('extract-tasks', 'Extract tasks', () => setListPickerOpen(true))}
      {btn('outline', 'Outline')}

      <span className="ml-2 text-[11px] uppercase tracking-wider text-ink-3">Refactor</span>
      <button
        type="button"
        disabled={!note}
        onClick={() => typeof window !== 'undefined' && window.__listsExtractSelection?.()}
        className="inline-flex items-center gap-1.5 rounded-md border border-line-1 bg-surface-2 px-2.5 py-1 text-xs text-ink-2 hover:bg-surface-3 disabled:opacity-50"
        title="Extract selected text to a new note, leaving a [[wikilink]] in its place. Requires source / split mode."
      >
        ✂️ Extract
      </button>

      <span className="ml-2 text-[11px] uppercase tracking-wider text-ink-3">Export</span>
      <button
        type="button"
        disabled={!note}
        onClick={() => exportNote(note)}
        className="inline-flex items-center gap-1.5 rounded-md border border-line-1 bg-surface-2 px-2.5 py-1 text-xs text-ink-2 hover:bg-surface-3 disabled:opacity-50"
        title="Download note as .md"
      >
        ⬇️ .md
      </button>

      <Modal open={continueOpen} onClose={() => setContinueOpen(false)} title="Continue writing">
        <textarea
          className="h-24 w-full rounded-md border border-line-1 bg-surface-2 p-2 text-sm text-ink-1 outline-none focus:border-brand-cobalt-400"
          placeholder="Optional prompt (where should it go next?)"
          value={continuePrompt}
          onChange={(e) => setContinuePrompt(e.target.value)}
        />
        <div className="mt-3 flex justify-end gap-2">
          <button
            type="button"
            className="rounded-md px-3 py-1 text-sm text-ink-3 hover:text-ink-1"
            onClick={() => setContinueOpen(false)}
          >
            Cancel
          </button>
          <button
            type="button"
            className="rounded-md bg-brand-cobalt px-3 py-1 text-sm text-white hover:bg-brand-cobalt-600"
            onClick={async () => {
              setContinueOpen(false);
              await run('continue', { prompt: continuePrompt });
              setContinuePrompt('');
            }}
          >
            Continue
          </button>
        </div>
      </Modal>

      <Modal open={listPickerOpen} onClose={() => setListPickerOpen(false)} title="Extract tasks to…">
        {lists.length === 0 ? (
          <div className="text-sm text-ink-3">No lists available.</div>
        ) : (
          <ul className="max-h-80 overflow-auto">
            {lists.map((l) => (
              <li key={l.id}>
                <button
                  type="button"
                  className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm text-ink-1 hover:bg-surface-2"
                  onClick={async () => {
                    setListPickerOpen(false);
                    await run('extract-tasks', { targetListId: l.id, list: l });
                  }}
                >
                  <span>{l.title || l.name || `List #${l.id}`}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Modal>
    </div>
  );
}
