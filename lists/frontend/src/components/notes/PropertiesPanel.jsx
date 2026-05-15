import { useState } from 'react';
import { setFrontmatter } from './frontmatter';

function PropertyValueView({ value }) {
  if (Array.isArray(value)) {
    return (
      <div className="flex flex-wrap gap-1">
        {value.map((v, i) => (
          <span
            key={`${i}-${String(v)}`}
            className="px-1.5 py-0.5 rounded bg-brand-cobalt/15 text-brand-cobalt-300 text-xs"
          >
            {String(v)}
          </span>
        ))}
      </div>
    );
  }
  if (value === null) return <span className="text-ink-4 italic">null</span>;
  if (typeof value === 'boolean') {
    return <span className="font-mono text-ink-2 text-xs">{String(value)}</span>;
  }
  return <span className="text-ink-1 text-sm">{String(value)}</span>;
}

function keyIcon(key) {
  const k = key.toLowerCase();
  if (k === 'tags' || k === 'tag') return '🏷️';
  if (k === 'aliases' || k === 'alias') return '🪪';
  if (k === 'date' || k === 'created' || k === 'updated') return '📅';
  if (k === 'author') return '👤';
  if (k === 'status') return '🚦';
  if (k === 'priority') return '⭐';
  return '•';
}

function parseValueInput(raw) {
  const v = raw.trim();
  if (v === '') return '';
  if (v === 'true') return true;
  if (v === 'false') return false;
  if (v === 'null') return null;
  if (/^-?\d+$/.test(v)) return Number(v);
  if (/^-?\d+\.\d+$/.test(v)) return Number(v);
  if (v.startsWith('[') && v.endsWith(']')) {
    const inner = v.slice(1, -1).trim();
    if (!inner) return [];
    return inner.split(',').map((s) => s.trim().replace(/^['"]|['"]$/g, ''));
  }
  return v;
}

function ValueEditor({ initial, onSave, onCancel }) {
  const initialText = Array.isArray(initial)
    ? `[${initial.map(String).join(', ')}]`
    : initial === null ? 'null' : String(initial);
  const [text, setText] = useState(initialText);
  return (
    <span className="flex items-center gap-1">
      <input
        autoFocus
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') { e.preventDefault(); onSave(parseValueInput(text)); }
          if (e.key === 'Escape') { e.preventDefault(); onCancel(); }
        }}
        onBlur={() => onSave(parseValueInput(text))}
        className="flex-1 min-w-0 px-1 py-0 text-sm bg-surface-3 text-ink-1 rounded outline-none border border-brand-cobalt"
      />
    </span>
  );
}

export default function PropertiesPanel({ props, body, onBodyChange }) {
  const [editingKey, setEditingKey] = useState(null);
  const [addOpen, setAddOpen] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');

  const hasProps = props && Object.keys(props).length > 0;
  const editable = typeof onBodyChange === 'function';

  function update(newProps) {
    if (!editable) return;
    const nextBody = setFrontmatter(body || '', newProps);
    onBodyChange(nextBody);
  }

  function setValue(key, value) {
    const next = { ...(props || {}) };
    next[key] = value;
    update(next);
    setEditingKey(null);
  }

  function deleteKey(key) {
    const next = { ...(props || {}) };
    delete next[key];
    update(next);
  }

  function addProperty() {
    const k = newKey.trim();
    if (!k) return;
    const v = parseValueInput(newValue);
    setValue(k, v);
    setNewKey('');
    setNewValue('');
    setAddOpen(false);
  }

  if (!hasProps && !editable) return null;
  if (!hasProps && !addOpen) {
    return editable ? (
      <div className="mb-4 rounded-xl border border-line-1 bg-surface-2 px-3 py-2">
        <button
          onClick={() => setAddOpen(true)}
          className="text-xs text-ink-3 hover:text-ink-1"
        >
          + Add property
        </button>
      </div>
    ) : null;
  }

  return (
    <div className="mb-4 rounded-xl border border-line-1 bg-surface-2 px-3 py-2">
      <div className="mb-1 flex items-center justify-between">
        <div className="text-xs uppercase tracking-wider text-ink-4">Properties</div>
        {editable && (
          <button
            onClick={() => setAddOpen((v) => !v)}
            className="text-xs text-ink-3 hover:text-ink-1"
            aria-label="Add property"
          >
            {addOpen ? '×' : '+'}
          </button>
        )}
      </div>
      <dl className="grid grid-cols-[max-content_1fr_max-content] gap-x-3 gap-y-1">
        {Object.entries(props || {}).map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-xs text-ink-3 self-center">
              <span className="mr-1">{keyIcon(k)}</span>{k}
            </dt>
            <dd className="self-center min-w-0">
              {editable && editingKey === k ? (
                <ValueEditor
                  initial={v}
                  onSave={(val) => setValue(k, val)}
                  onCancel={() => setEditingKey(null)}
                />
              ) : editable ? (
                <button
                  type="button"
                  onClick={() => setEditingKey(k)}
                  className="text-left w-full hover:bg-surface-3 rounded px-1 -mx-1"
                  title="Click to edit"
                >
                  <PropertyValueView value={v} />
                </button>
              ) : (
                <PropertyValueView value={v} />
              )}
            </dd>
            {editable && (
              <div className="self-center">
                <button
                  type="button"
                  onClick={() => deleteKey(k)}
                  className="text-ink-4 hover:text-semantic-danger text-xs"
                  aria-label={`Delete property ${k}`}
                  title="Remove property"
                >
                  ✕
                </button>
              </div>
            )}
          </div>
        ))}
      </dl>
      {editable && addOpen && (
        <div className="mt-2 pt-2 border-t border-line-1 flex gap-1">
          <input
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="key"
            className="w-1/3 px-2 py-1 text-xs bg-surface-3 text-ink-1 rounded outline-none"
            onKeyDown={(e) => { if (e.key === 'Enter') addProperty(); if (e.key === 'Escape') setAddOpen(false); }}
          />
          <input
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            placeholder="value (or [a, b, c])"
            className="flex-1 px-2 py-1 text-xs bg-surface-3 text-ink-1 rounded outline-none"
            onKeyDown={(e) => { if (e.key === 'Enter') addProperty(); if (e.key === 'Escape') setAddOpen(false); }}
          />
          <button
            onClick={addProperty}
            disabled={!newKey.trim()}
            className="px-2 text-xs bg-brand-cobalt text-white rounded hover:bg-brand-cobalt-400 disabled:opacity-50"
          >
            Add
          </button>
        </div>
      )}
    </div>
  );
}
