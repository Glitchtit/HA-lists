import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { Handle, Position } from 'reactflow';
import NotePreview from '../../notes/NotePreview';

const PRESET_COLORS = [
  { name: 'gray',   value: 'var(--bg-3)' },
  { name: 'cobalt', value: 'var(--brand-cobalt)' },
  { name: 'green',  value: 'var(--success)' },
  { name: 'amber',  value: 'var(--warning)' },
  { name: 'rose',   value: 'var(--danger)' },
  { name: 'purple', value: '#7C3AED' },
];

function toggleChecklistAt(body, offset) {
  if (typeof offset !== 'number' || offset < 0 || offset >= body.length) return body;
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

function tintForColor(color) {
  // Semi-transparent card background derived from the dot colour.
  if (!color) return 'var(--bg-3)';
  if (color.startsWith('var(')) return color;
  return color;
}

function CardNode({ data, selected, id }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(data?.title || '');
  const [body, setBody] = useState(data?.body || '');
  const [colorOpen, setColorOpen] = useState(false);
  const textareaRef = useRef(null);

  useEffect(() => { setTitle(data?.title || ''); }, [data?.title]);
  useEffect(() => { setBody(data?.body || ''); }, [data?.body]);

  useEffect(() => {
    if (editing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.selectionStart = textareaRef.current.value.length;
    }
  }, [editing]);

  const color = data?.color;
  const dotColor = color || 'var(--fg-4)';

  const save = (patch) => {
    if (data?.onUpdate) data.onUpdate(patch);
  };

  const commitTitle = () => {
    if (title !== (data?.title || '')) save({ title });
  };
  const commitBody = () => {
    setEditing(false);
    if (body !== (data?.body || '')) save({ body });
  };

  const handleToggleChecklist = useCallback((offset) => {
    setBody((prev) => {
      const next = toggleChecklistAt(prev, offset);
      if (next !== prev) {
        // Save immediately — no blur needed for checkbox clicks.
        if (data?.onUpdate) data.onUpdate({ body: next });
      }
      return next;
    });
  }, [data]);

  const handleBodyKey = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      commitBody();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setBody(data?.body || '');
      setEditing(false);
    }
  };

  return (
    <div
      className={`bn bn-card ${selected ? 'selected' : ''}`}
      style={{
        background: tintForColor(color) || 'var(--bg-3)',
        borderLeftColor: color || 'var(--brand-cobalt)',
        position: 'relative',
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <Handle type="target" position={Position.Top} />
      <div className="bn-header">
        <span className="bn-header-icon">📌</span>
        <input
          className="bn-card-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={commitTitle}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); e.currentTarget.blur(); }
            else if (e.key === 'Escape') { setTitle(data?.title || ''); e.currentTarget.blur(); }
          }}
          placeholder="Card title…"
        />
        <span
          className="bn-card-dot"
          title="Change colour"
          style={{ background: dotColor }}
          onClick={(e) => { e.stopPropagation(); setColorOpen((v) => !v); }}
        />
      </div>
      {colorOpen && (
        <div className="bn-color-popover" onClick={(e) => e.stopPropagation()}>
          {PRESET_COLORS.map((c) => (
            <span
              key={c.name}
              className="bn-color-swatch"
              title={c.name}
              style={{ background: c.value }}
              onClick={() => { save({ color: c.value }); setColorOpen(false); }}
            />
          ))}
        </div>
      )}
      <div
        className="bn-body"
        onDoubleClick={() => setEditing(true)}
      >
        {editing ? (
          <textarea
            ref={textareaRef}
            className="bn-card-body nodrag nowheel"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            onBlur={commitBody}
            onKeyDown={handleBodyKey}
            placeholder="Write something… (Ctrl+Enter to save)"
          />
        ) : (
          <div className="bn-note-body nowheel">
            <NotePreview body={body || '*Double-click to edit*'} onToggleChecklist={handleToggleChecklist} />
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

export default memo(CardNode);
