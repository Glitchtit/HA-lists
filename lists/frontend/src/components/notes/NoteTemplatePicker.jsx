import { useEffect, useState } from 'react';
import * as api from '../../api';

export default function NoteTemplatePicker({ open, folderId, onClose, onCreated }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [title, setTitle] = useState('');
  const [selected, setSelected] = useState(null);
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setTitle('');
    setSelected(null);
    api.getNoteTemplates()
      .then((t) => { if (!cancelled) setTemplates(t); })
      .catch((e) => { if (!cancelled) setError(e.message || 'Failed to load templates'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [open]);

  if (!open) return null;

  async function apply(tpl) {
    setApplying(true);
    try {
      const note = await api.applyNoteTemplate(tpl.id, {
        title: title.trim() || undefined,
        folder_id: folderId ?? undefined,
      });
      onCreated && onCreated(note);
      onClose && onClose();
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to apply template');
    } finally {
      setApplying(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose && onClose(); }}
    >
      <div className="w-full max-w-2xl max-h-[80vh] flex flex-col bg-surface-1 border border-line-1 rounded-2xl shadow-glow-cobalt overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-line-1">
          <div className="text-base font-display text-ink-1">📋 New from template</div>
          <button onClick={onClose} className="text-ink-3 hover:text-ink-1" aria-label="Close">✕</button>
        </div>
        <div className="px-4 py-3 border-b border-line-1">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Override title (optional) — supports {{date}} {{time}}"
            className="w-full px-3 py-2 text-sm bg-surface-3 text-ink-1 rounded-lg outline-none"
          />
        </div>
        {error && (
          <div className="px-4 py-2 text-xs text-semantic-danger bg-semantic-danger/10">{error}</div>
        )}
        <div className="flex-1 overflow-auto p-3">
          {loading ? (
            <div className="text-sm text-ink-3">Loading…</div>
          ) : templates.length === 0 ? (
            <div className="text-sm text-ink-3 italic">No templates available</div>
          ) : (
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {templates.map((t) => (
                <li key={t.id}>
                  <button
                    onClick={() => { setSelected(t); apply(t); }}
                    disabled={applying}
                    className={`w-full text-left rounded-xl border border-line-1 bg-surface-2 hover:bg-surface-3 hover:border-brand-cobalt-400 transition-colors p-3 ${
                      selected?.id === t.id ? 'border-brand-cobalt' : ''
                    } ${applying ? 'opacity-60 cursor-wait' : ''}`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xl">{t.icon || '📝'}</span>
                      <span className="text-sm font-medium text-ink-1 truncate">{t.name}</span>
                      {t.is_system && (
                        <span className="ml-auto text-[10px] uppercase tracking-wider text-ink-4 px-1.5 py-0.5 rounded bg-surface-3">system</span>
                      )}
                    </div>
                    <pre className="whitespace-pre-wrap break-words text-xs text-ink-3 max-h-20 overflow-hidden font-sans">
                      {(t.body_md || '').slice(0, 220)}{(t.body_md || '').length > 220 ? '…' : ''}
                    </pre>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="px-4 py-2 border-t border-line-1 text-xs text-ink-4">
          Variables: <code className="font-mono">{'{{date}}'}</code>, <code className="font-mono">{'{{time}}'}</code>, <code className="font-mono">{'{{title}}'}</code>, <code className="font-mono">{'{{date:%Y-%m-%d}}'}</code>
        </div>
      </div>
    </div>
  );
}
