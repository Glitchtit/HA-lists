import { memo, useEffect, useState } from 'react';
import { NodeResizer } from 'reactflow';

const PRESET_TINTS = [
  { name: 'cobalt', stroke: 'var(--brand-cobalt)',   fill: 'rgba(0, 71, 171, 0.12)' },
  { name: 'orange', stroke: 'var(--brand-orange)',   fill: 'rgba(255, 79, 0, 0.10)' },
  { name: 'green',  stroke: 'var(--success)',        fill: 'rgba(16, 185, 129, 0.10)' },
  { name: 'amber',  stroke: 'var(--warning)',        fill: 'rgba(245, 158, 11, 0.12)' },
  { name: 'rose',   stroke: 'var(--danger)',         fill: 'rgba(239, 68, 68, 0.12)' },
  { name: 'slate',  stroke: 'var(--fg-4)',           fill: 'rgba(148, 163, 184, 0.10)' },
];

function paletteFor(color) {
  const hit = PRESET_TINTS.find((p) => p.stroke === color);
  return hit || PRESET_TINTS[0];
}

function GroupNode({ data, selected }) {
  const [title, setTitle] = useState(data?.title || '');
  const [swatchOpen, setSwatchOpen] = useState(false);
  useEffect(() => { setTitle(data?.title || ''); }, [data?.title]);

  const palette = paletteFor(data?.color);
  const save = (patch) => data?.onUpdate?.(patch);
  const commitTitle = () => {
    if (title !== (data?.title || '')) save({ title });
  };
  const commitSize = (w, h) => save({ width: w, height: h });

  return (
    <div
      className={`bn-group ${selected ? 'selected' : ''}`}
      style={{
        background: palette.fill,
        borderColor: palette.stroke,
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <NodeResizer
        color={palette.stroke}
        isVisible={selected}
        minWidth={200}
        minHeight={140}
        onResizeEnd={(_e, size) => commitSize(size.width, size.height)}
      />
      <div className="bn-group-header" style={{ background: palette.stroke }}>
        <span className="bn-group-icon">📦</span>
        <input
          className="bn-group-title nodrag"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={commitTitle}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); e.currentTarget.blur(); }
            else if (e.key === 'Escape') { setTitle(data?.title || ''); e.currentTarget.blur(); }
          }}
          placeholder="Group title…"
        />
        <button
          type="button"
          className="bn-group-swatch-btn nodrag"
          title="Change colour"
          onClick={(e) => { e.stopPropagation(); setSwatchOpen((v) => !v); }}
        >🎨</button>
      </div>
      {swatchOpen && (
        <div className="bn-group-swatches nodrag" onClick={(e) => e.stopPropagation()}>
          {PRESET_TINTS.map((p) => (
            <button
              key={p.name}
              type="button"
              className="bn-group-swatch"
              title={p.name}
              style={{ background: p.stroke }}
              onClick={() => { save({ color: p.stroke }); setSwatchOpen(false); }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default memo(GroupNode);
