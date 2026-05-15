import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import { EditorState } from '@codemirror/state';
import { EditorView, keymap } from '@codemirror/view';
import { history, defaultKeymap, historyKeymap } from '@codemirror/commands';
import { markdown } from '@codemirror/lang-markdown';
import { search, searchKeymap, highlightSelectionMatches } from '@codemirror/search';
import { foldGutter, foldKeymap } from '@codemirror/language';
import { oneDark } from '@codemirror/theme-one-dark';

const NoteSource = forwardRef(function NoteSource({ value, onChange, onBlur, onLinkAutocomplete, onTagAutocomplete, onSlashAutocomplete, className = '' }, ref) {
  const hostRef = useRef(null);
  const viewRef = useRef(null);
  const onLinkAutocompleteRef = useRef(onLinkAutocomplete);
  useEffect(() => { onLinkAutocompleteRef.current = onLinkAutocomplete; }, [onLinkAutocomplete]);
  const onTagAutocompleteRef = useRef(onTagAutocomplete);
  useEffect(() => { onTagAutocompleteRef.current = onTagAutocomplete; }, [onTagAutocomplete]);
  const onSlashAutocompleteRef = useRef(onSlashAutocomplete);
  useEffect(() => { onSlashAutocompleteRef.current = onSlashAutocomplete; }, [onSlashAutocomplete]);

  useImperativeHandle(ref, () => ({
    getSelection() {
      const view = viewRef.current;
      if (!view) return { text: '', from: 0, to: 0 };
      const sel = view.state.selection.main;
      return {
        text: view.state.doc.sliceString(sel.from, sel.to),
        from: sel.from,
        to: sel.to,
      };
    },
    replaceSelection(text) {
      const view = viewRef.current;
      if (!view) return;
      const sel = view.state.selection.main;
      view.dispatch({
        changes: { from: sel.from, to: sel.to, insert: text },
        selection: { anchor: sel.from + text.length },
      });
      view.focus();
    },
    replaceRange(from, to, text) {
      const view = viewRef.current;
      if (!view) return;
      view.dispatch({
        changes: { from, to, insert: text },
        selection: { anchor: from + text.length },
      });
      view.focus();
    },
  }), []);
  const onChangeRef = useRef(onChange);
  const onBlurRef = useRef(onBlur);

  useEffect(() => { onChangeRef.current = onChange; }, [onChange]);
  useEffect(() => { onBlurRef.current = onBlur; }, [onBlur]);

  useEffect(() => {
    if (!hostRef.current) return;

    const updateListener = EditorView.updateListener.of((upd) => {
      if (upd.docChanged && onChangeRef.current) {
        onChangeRef.current(upd.state.doc.toString());
      }
      if (upd.docChanged || upd.selectionSet) {
        const view = upd.view;
        const pos = view.state.selection.main.head;
        const lineStart = view.state.doc.lineAt(pos).from;
        const before = view.state.doc.sliceString(lineStart, pos);
        let handled = false;
        // Wikilink trigger: open [[ unclosed
        if (onLinkAutocompleteRef.current) {
          const open = before.lastIndexOf('[[');
          if (open !== -1) {
            const between = before.slice(open + 2);
            if (!/[\]\n]/.test(between)) {
              const coords = view.coordsAtPos(pos);
              if (coords) {
                onLinkAutocompleteRef.current({
                  query: between,
                  x: coords.left,
                  y: coords.bottom + 4,
                  from: lineStart + open,
                  to: pos,
                });
                handled = true;
              }
            }
          }
          if (!handled) onLinkAutocompleteRef.current(null);
        }
        // Tag trigger: #word at start or after whitespace, not inside [[…
        if (!handled && onTagAutocompleteRef.current) {
          const hashMatch = /(^|\s)#([A-Za-z0-9][\w/-]*)$/.exec(before);
          if (hashMatch) {
            const offsetInBefore = hashMatch.index + (hashMatch[1] ? 1 : 0);
            const from = lineStart + offsetInBefore;
            const coords = view.coordsAtPos(pos);
            if (coords) {
              onTagAutocompleteRef.current({
                query: hashMatch[2],
                x: coords.left,
                y: coords.bottom + 4,
                from,
                to: pos,
              });
              handled = true;
            }
          }
          if (!handled) onTagAutocompleteRef.current(null);
        }
        // Slash trigger: '/word' at the start of a line (column 0)
        if (!handled && onSlashAutocompleteRef.current) {
          const slashMatch = /^\/([A-Za-z]*)$/.exec(before);
          if (slashMatch) {
            const from = lineStart;
            const coords = view.coordsAtPos(pos);
            if (coords) {
              onSlashAutocompleteRef.current({
                query: slashMatch[1],
                x: coords.left,
                y: coords.bottom + 4,
                from,
                to: pos,
              });
              return;
            }
          }
          onSlashAutocompleteRef.current(null);
        }
      }
    });

    const blurHandler = EditorView.domEventHandlers({
      blur: () => {
        if (onBlurRef.current && viewRef.current) {
          onBlurRef.current(viewRef.current.state.doc.toString());
        }
        return false;
      },
    });

    const state = EditorState.create({
      doc: value || '',
      extensions: [
        history(),
        search({ top: true }),
        highlightSelectionMatches(),
        foldGutter(),
        keymap.of([...searchKeymap, ...foldKeymap, ...defaultKeymap, ...historyKeymap]),
        markdown(),
        oneDark,
        EditorView.lineWrapping,
        updateListener,
        blurHandler,
        EditorView.theme({
          '&': { height: '100%', fontSize: '14px' },
          '.cm-scroller': { fontFamily: 'var(--font-mono, JetBrains Mono, monospace)' },
          '.cm-content': { padding: '12px' },
        }),
      ],
    });

    const view = new EditorView({ state, parent: hostRef.current });
    viewRef.current = view;
    return () => {
      view.destroy();
      viewRef.current = null;
    };
    // Only mount once; value syncing handled by effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync external value changes (e.g. different note loaded) into the editor.
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const current = view.state.doc.toString();
    if ((value || '') === current) return;
    view.dispatch({
      changes: { from: 0, to: current.length, insert: value || '' },
    });
  }, [value]);

  return <div ref={hostRef} className={`note-source h-full w-full ${className}`} />;
});

export default NoteSource;
