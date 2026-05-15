function PropertyValue({ value }) {
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

export default function PropertiesPanel({ props }) {
  if (!props || Object.keys(props).length === 0) return null;
  return (
    <div className="mb-4 rounded-xl border border-line-1 bg-surface-2 px-3 py-2">
      <div className="mb-1 text-xs uppercase tracking-wider text-ink-4">Properties</div>
      <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1">
        {Object.entries(props).map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-xs text-ink-3 self-center">
              <span className="mr-1">{keyIcon(k)}</span>{k}
            </dt>
            <dd className="self-center min-w-0">
              <PropertyValue value={v} />
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
