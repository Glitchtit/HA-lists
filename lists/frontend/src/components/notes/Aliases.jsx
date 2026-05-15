import { useEffect, useState } from 'react';
import * as api from '../../api';

export default function Aliases({ noteId }) {
  const [aliases, setAliases] = useState([]);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    if (!noteId) return;
    try {
      setAliases(await api.getNoteAliases(noteId));
    } catch (e) {
      setError(e.message || 'Failed to load aliases');
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [noteId]);

  async function add(e) {
    e.preventDefault();
    const a = draft.trim();
    if (!a) return;
    setLoading(true);
    setError(null);
    try {
      const next = await api.addNoteAlias(noteId, a);
      setAliases(next);
      setDraft('');
    } catch (e) {
      if (e.response?.status === 409) setError('Conflicts with an existing note title');
      else setError(e.response?.data?.detail || e.message || 'Failed to add alias');
    } finally {
      setLoading(false);
    }
  }

  async function remove(alias) {
    try {
      await api.removeNoteAlias(noteId, alias);
      setAliases((prev) => prev.filter((a) => a.toLowerCase() !== alias.toLowerCase()));
    } catch (e) {
      setError(e.message || 'Failed to remove alias');
    }
  }

  if (!noteId) {
    return <div className="p-4 text-sm text-ink-3">No note</div>;
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 text-xs text-ink-3">
        Wikilinks like <code className="font-mono text-ink-2">[[alias]]</code> resolve to this note.
      </div>
      <form onSubmit={add} className="flex gap-1 px-3 pb-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add alias…"
          className="flex-1 px-2 py-1 text-sm bg-surface-3 text-ink-1 rounded outline-none"
        />
        <button
          type="submit"
          disabled={loading || !draft.trim()}
          className="px-2 text-sm bg-brand-cobalt text-white rounded hover:bg-brand-cobalt-400 disabled:opacity-50"
        >
          Add
        </button>
      </form>
      {error && (
        <div className="mx-3 mb-2 px-2 py-1 text-xs text-semantic-danger bg-semantic-danger/10 rounded">
          {error}
        </div>
      )}
      <ul className="flex-1 overflow-auto px-3 pb-3 space-y-1">
        {aliases.length === 0 ? (
          <li className="text-xs text-ink-4 italic">No aliases yet</li>
        ) : (
          aliases.map((a) => (
            <li key={a} className="flex items-center justify-between gap-2 px-2 py-1 rounded bg-surface-2 text-sm text-ink-1">
              <span className="truncate" title={a}>{a}</span>
              <button
                type="button"
                onClick={() => remove(a)}
                className="text-xs text-ink-3 hover:text-semantic-danger"
                title="Remove alias"
                aria-label={`Remove alias ${a}`}
              >
                ✕
              </button>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
