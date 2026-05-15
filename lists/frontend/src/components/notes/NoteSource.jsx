import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import { EditorState } from '@codemirror/state';
import { EditorView, keymap } from '@codemirror/view';
import { history, defaultKeymap, historyKeymap } from '@codemirror/commands';
import { markdown } from '@codemirror/lang-markdown';
import { search, searchKeymap, highlightSelectionMatches } from '@codemirror/search';
import { oneDark } from '@codemirror/theme-one-dark';

const NoteSource = forwardRef(function NoteSource({ value, onChange, onBlur, className = '' }, ref) {
  const hostRef = useRef(null);
  const viewRef = useRef(null);

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
        keymap.of([...searchKeymap, ...defaultKeymap, ...historyKeymap]),
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
