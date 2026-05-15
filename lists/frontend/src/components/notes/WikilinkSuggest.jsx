import { useEffect, useMemo, useState } from 'react';
import * as api from '../../api';

const W = 280;
const MAX_ROWS = 8;

let cache = null; // module-level cache shared across editor mounts
let cacheAt = 0;

async function getNotes() {
  const now = Date.now();
  if (cache && now - cacheAt < 5000) return cache;
  try {
    cache = await api.getNotes({ archived: false });
    cacheAt = now;
  } catch {
    cache = cache || [];
  }
  return cache || [];
}

export function invalidateNoteCache() {
  cache = null;
  cacheAt = 0;
}

export default function WikilinkSuggest({ trigger, onPick, onClose }) {
  const [notes, setNotes] = useState([]);
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (!trigger) return;
    let cancelled = false;
    getNotes().then((ns) => { if (!cancelled) setNotes(ns); });
    return () => { cancelled = true; };
  }, [trigger]);

  const filtered = useMemo(() => {
    if (!trigger) return [];
    const q = (trigger.query || '').toLowerCase();
    if (!q) {
      return notes.slice(0, MAX_ROWS);
    }
    return notes
      .filter((n) => (n.title || '').toLowerCase().includes(q))
      .slice(0, MAX_ROWS);
  }, [notes, trigger]);

  useEffect(() => { setIdx(0); }, [trigger?.query]);

  useEffect(() => {
    if (!trigger) return undefined;
    function onKey(e) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setIdx((i) => Math.min(filtered.length - 1, i + 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setIdx((i) => Math.max(0, i - 1));
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        if (filtered[idx]) {
          e.preventDefault();
          onPick && onPick(filtered[idx]);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose && onClose();
      }
    }
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [trigger, filtered, idx, onPick, onClose]);

  if (!trigger || filtered.length === 0) return null;
  const top = Math.min(window.innerHeight - 240, trigger.y);
  const left = Math.min(window.innerWidth - W - 16, trigger.x);

  return (
    <div
      role="listbox"
      style={{ position: 'fixed', left, top, width: W, zIndex: 60 }}
      className="rounded-lg border border-line-1 bg-surface-2 shadow-glow-cobalt overflow-hidden"
    >
      <div className="px-2 py-1 text-[10px] uppercase tracking-wider text-ink-4 border-b border-line-1">
        Wikilink → {trigger.query || '(type to filter)'}
      </div>
      <ul className="max-h-[280px] overflow-auto">
        {filtered.map((n, i) => (
          <li key={n.id}>
            <button
              type="button"
              onClick={() => onPick && onPick(n)}
              onMouseEnter={() => setIdx(i)}
              className={`flex w-full items-center gap-2 px-2 py-1 text-left text-xs ${
                i === idx ? 'bg-brand-cobalt/20 text-ink-1' : 'text-ink-2 hover:bg-surface-3'
              }`}
            >
              <span className="shrink-0">{n.icon || '📄'}</span>
              <span className="truncate">{n.title || 'Untitled'}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
