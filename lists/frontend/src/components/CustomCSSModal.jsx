import { useEffect, useState } from 'react';

const KEY = 'lists_custom_css';

export function applyStoredCSS() {
  try {
    const css = localStorage.getItem(KEY) || '';
    let el = document.getElementById('lists-custom-css');
    if (!el) {
      el = document.createElement('style');
      el.id = 'lists-custom-css';
      document.head.appendChild(el);
    }
    el.textContent = css;
  } catch {
    // ignore
  }
}

export default function CustomCSSModal({ open, onClose }) {
  const [css, setCSS] = useState('');

  useEffect(() => {
    if (!open) return;
    try { setCSS(localStorage.getItem(KEY) || ''); } catch { setCSS(''); }
  }, [open]);

  if (!open) return null;

  function save() {
    try { localStorage.setItem(KEY, css); } catch {}
    applyStoredCSS();
    onClose && onClose();
  }

  function clear() {
    setCSS('');
    try { localStorage.removeItem(KEY); } catch {}
    applyStoredCSS();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose && onClose(); }}
    >
      <div className="w-full max-w-2xl max-h-[80vh] flex flex-col bg-surface-1 border border-line-1 rounded-2xl shadow-glow-cobalt overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-line-1">
          <div className="text-base font-display text-ink-1">🎨 Custom CSS</div>
          <button onClick={onClose} className="text-ink-3 hover:text-ink-1" aria-label="Close">✕</button>
        </div>
        <div className="px-4 py-2 text-xs text-ink-3 border-b border-line-1">
          Paste CSS to restyle the app — your snippets persist per-browser. Use the existing tokens
          like <code className="font-mono text-ink-1">var(--brand-orange)</code> / <code className="font-mono text-ink-1">.note-preview</code> /
          <code className="font-mono text-ink-1"> .wikilink</code>. Live-applied on Save.
        </div>
        <textarea
          value={css}
          onChange={(e) => setCSS(e.target.value)}
          spellCheck={false}
          placeholder="/* e.g. */
.note-preview h1 { letter-spacing: -0.02em }
.wikilink { text-decoration-style: dotted }"
          className="flex-1 min-h-[260px] px-4 py-3 bg-surface-0 text-ink-1 font-mono text-xs outline-none resize-none"
        />
        <div className="px-4 py-3 border-t border-line-1 flex items-center justify-between">
          <button
            onClick={clear}
            className="text-xs text-ink-4 hover:text-semantic-danger"
          >
            Clear all
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1 text-sm text-ink-3 hover:text-ink-1"
            >
              Cancel
            </button>
            <button
              onClick={save}
              className="px-3 py-1 text-sm bg-brand-cobalt text-white rounded hover:bg-brand-cobalt-400"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
