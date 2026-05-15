import { useEffect, useMemo, useRef, useState } from 'react';
import NoteSource from './NoteSource';
import NotePreview from './NotePreview';
import WikilinkSuggest, { invalidateNoteCache } from './WikilinkSuggest';
import TagSuggest, { invalidateTagCache } from './TagSuggest';
import SlashSuggest from './SlashSuggest';
import * as api from '../../api';

function countStats(body) {
  const text = String(body || '');
  const chars = text.length;
  // Strip frontmatter, code fences, inline code, callout markers, and
  // wikilink/embed brackets so the word count reflects prose, not
  // markdown plumbing.
  const stripped = text
    .replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/, ' ')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`[^`]*`/g, ' ')
    .replace(/!?\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g, (_, t, a) => a || t)
    .replace(/^>\s*\[![^\]]+\][+-]?/gm, ' ')
    .replace(/[#*_~>`-]/g, ' ');
  const words = stripped.trim() ? stripped.trim().split(/\s+/).length : 0;
  return { words, chars };
}

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
  onWikilinkOpenInBackground,
  onNoteSelect,
  onEmbedFetch,
  mode: modeProp,
  onModeChange,
  onExtracted,
}) {
  const sourceRef = useRef(null);
  const [linkTrigger, setLinkTrigger] = useState(null);
  const [tagTrigger, setTagTrigger] = useState(null);
  const [slashTrigger, setSlashTrigger] = useState(null);

  // Refresh autocomplete caches when a note saves (title might have changed)
  useEffect(() => { invalidateNoteCache(); invalidateTagCache(); }, [note?.id, note?.title]);
  const [modeState, setModeState] = useState('preview'); // 'split' | 'source' | 'preview'
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

  const stats = useMemo(() => countStats(draftBody), [draftBody]);

  async function extractSelection() {
    if (mode === 'preview') {
      // Selection is in CodeMirror — make sure it's mounted.
      return null;
    }
    const ref = sourceRef.current;
    if (!ref) return null;
    const sel = ref.getSelection();
    if (!sel.text || !sel.text.trim()) {
      if (typeof window !== 'undefined') {
        window.alert('Select some text in the editor first.');
      }
      return null;
    }
    const firstLine = sel.text.split('\n', 1)[0].replace(/^#+\s+/, '').trim();
    const suggested = firstLine.slice(0, 80) || 'Extracted note';
    const title = window.prompt('New note title:', suggested);
    if (!title) return null;
    try {
      const created = await api.createNote({
        title: title.trim(),
        body: sel.text,
        folder_id: note.folder_id ?? null,
      });
      ref.replaceSelection(`[[${created.title}]]`);
      onExtracted && onExtracted(created);
      return created;
    } catch (e) {
      if (typeof window !== 'undefined') {
        window.alert(e?.response?.data?.detail || e.message || 'Failed to extract');
      }
      return null;
    }
  }

  // Expose extractor on window for the toolbar (simple bus — avoids
  // threading a ref through App.jsx for one button).
  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    window.__listsExtractSelection = extractSelection;
    return () => { if (window.__listsExtractSelection === extractSelection) delete window.__listsExtractSelection; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [note?.id, mode, draftBody]);

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
              ref={sourceRef}
              value={draftBody}
              onChange={(v) => setDraftBody(v)}
              onBlur={(v) => commitBody(v)}
              onLinkAutocomplete={setLinkTrigger}
              onTagAutocomplete={setTagTrigger}
              onSlashAutocomplete={setSlashTrigger}
            />
          </div>
        )}
        {mode !== 'source' && (
          <div className={`min-w-0 overflow-auto px-6 py-4 ${mode === 'split' ? 'w-1/2' : 'w-full'}`}>
            <NotePreview
              body={draftBody}
              onWikilinkClick={onWikilinkClick}
              onWikilinkOpenInBackground={onWikilinkOpenInBackground}
              onNoteSelect={onNoteSelect}
              onEmbedResolve={onEmbedFetch}
              onToggleChecklist={handleToggleChecklist}
              onBodyChange={(next) => { setDraftBody(next); commitBody(next); }}
              visitedEmbeds={new Set(note.id != null ? [note.id] : [])}
            />
          </div>
        )}
      </div>

      <WikilinkSuggest
        trigger={linkTrigger}
        onPick={(n) => {
          const ref = sourceRef.current;
          if (ref && linkTrigger) {
            ref.replaceRange(linkTrigger.from, linkTrigger.to, `[[${n.title}]]`);
          }
          setLinkTrigger(null);
        }}
        onClose={() => setLinkTrigger(null)}
      />
      <TagSuggest
        trigger={tagTrigger}
        onPick={(t) => {
          const ref = sourceRef.current;
          if (ref && tagTrigger) {
            ref.replaceRange(tagTrigger.from, tagTrigger.to, `#${t.tag} `);
          }
          setTagTrigger(null);
        }}
        onClose={() => setTagTrigger(null)}
      />
      <SlashSuggest
        trigger={slashTrigger}
        onPick={(cmd) => {
          const ref = sourceRef.current;
          if (ref && slashTrigger) {
            const text = typeof cmd.snippet === 'function' ? cmd.snippet() : cmd.snippet;
            ref.replaceRange(slashTrigger.from, slashTrigger.to, text);
          }
          setSlashTrigger(null);
        }}
        onClose={() => setSlashTrigger(null)}
      />

      <div className="flex items-center justify-end gap-3 border-t border-line-1 bg-surface-1 px-4 py-1 text-xs text-ink-4 font-mono">
        <span title="Word count">{stats.words.toLocaleString()} {stats.words === 1 ? 'word' : 'words'}</span>
        <span className="text-ink-4/60">·</span>
        <span title="Character count">{stats.chars.toLocaleString()} {stats.chars === 1 ? 'character' : 'characters'}</span>
      </div>
    </div>
  );
}
