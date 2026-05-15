import { useEffect, useMemo, useState } from 'react';

const COMMANDS = [
  { id: 'h1', label: 'Heading 1', hint: '#', snippet: '# ' },
  { id: 'h2', label: 'Heading 2', hint: '##', snippet: '## ' },
  { id: 'h3', label: 'Heading 3', hint: '###', snippet: '### ' },
  { id: 'bullet', label: 'Bullet list', hint: '-', snippet: '- ' },
  { id: 'numbered', label: 'Numbered list', hint: '1.', snippet: '1. ' },
  { id: 'todo', label: 'Checklist item', hint: '- [ ]', snippet: '- [ ] ' },
  { id: 'quote', label: 'Quote', hint: '>', snippet: '> ' },
  { id: 'divider', label: 'Divider', hint: '---', snippet: '---\n' },
  { id: 'code', label: 'Code block', hint: '```', snippet: '```\n\n```\n', cursorOffset: 4 },
  { id: 'callout', label: 'Callout', hint: '> [!info]', snippet: '> [!info] \n> \n', cursorOffset: 10 },
  { id: 'table', label: 'Table', hint: '|…|', snippet: '| Col 1 | Col 2 |\n|-------|-------|\n|       |       |\n' },
  { id: 'wikilink', label: 'Wikilink', hint: '[[', snippet: '[[]]', cursorOffset: 2 },
  { id: 'embed', label: 'Embed', hint: '![[', snippet: '![[]]', cursorOffset: 3 },
  { id: 'today', label: 'Today date', hint: 'YYYY-MM-DD', snippet: () => new Date().toISOString().slice(0, 10) },
  { id: 'now', label: 'Time now', hint: 'HH:MM', snippet: () => new Date().toTimeString().slice(0, 5) },
];

const W = 280;
const MAX_ROWS = 8;

export default function SlashSuggest({ trigger, onPick, onClose }) {
  const [idx, setIdx] = useState(0);

  const filtered = useMemo(() => {
    if (!trigger) return [];
    const q = (trigger.query || '').toLowerCase();
    if (!q) return COMMANDS.slice(0, MAX_ROWS);
    return COMMANDS.filter((c) =>
      c.label.toLowerCase().includes(q) || c.id.includes(q) || c.hint.toLowerCase().includes(q)
    ).slice(0, MAX_ROWS);
  }, [trigger]);

  useEffect(() => { setIdx(0); }, [trigger?.query]);

  useEffect(() => {
    if (!trigger) return undefined;
    function onKey(e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setIdx((i) => Math.min(filtered.length - 1, i + 1)); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setIdx((i) => Math.max(0, i - 1)); }
      else if (e.key === 'Enter' || e.key === 'Tab') {
        if (filtered[idx]) { e.preventDefault(); onPick && onPick(filtered[idx]); }
      } else if (e.key === 'Escape') { e.preventDefault(); onClose && onClose(); }
    }
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [trigger, filtered, idx, onPick, onClose]);

  if (!trigger || filtered.length === 0) return null;
  const top = Math.min(window.innerHeight - 280, trigger.y);
  const left = Math.min(window.innerWidth - W - 16, trigger.x);

  return (
    <div
      role="listbox"
      style={{ position: 'fixed', left, top, width: W, zIndex: 60 }}
      className="rounded-lg border border-line-1 bg-surface-2 shadow-glow-cobalt overflow-hidden"
    >
      <div className="px-2 py-1 text-[10px] uppercase tracking-wider text-ink-4 border-b border-line-1">
        Insert → /{trigger.query || '(type to filter)'}
      </div>
      <ul className="max-h-[320px] overflow-auto">
        {filtered.map((c, i) => (
          <li key={c.id}>
            <button
              type="button"
              onClick={() => onPick && onPick(c)}
              onMouseEnter={() => setIdx(i)}
              className={`flex w-full items-center justify-between gap-2 px-2 py-1 text-left text-xs ${
                i === idx ? 'bg-brand-cobalt/20 text-ink-1' : 'text-ink-2 hover:bg-surface-3'
              }`}
            >
              <span className="truncate">{c.label}</span>
              <span className="shrink-0 font-mono text-ink-4">{c.hint}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
