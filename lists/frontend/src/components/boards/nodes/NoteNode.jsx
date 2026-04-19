import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import NotePreview from '../../notes/NotePreview';

// Close any unclosed fenced code block (e.g. from body_preview truncation)
function safePreview(text) {
  if (!text) return '';
  const fenceCount = (text.match(/^```/gm) || []).length;
  return fenceCount % 2 !== 0 ? text + '\n```' : text;
}

function NoteNode({ data, selected }) {
  const summary = data?.ref_summary;
  // Only tombstone if we have a ref_id but no summary — not when summary is simply absent
  const tombstone = data?.ref_id != null && !summary;
  const color = data?.color || 'var(--brand-cobalt)';

  const handleClick = (e) => {
    if (e.defaultPrevented) return;
    if (data?.onOpenEntity && !tombstone) {
      data.onOpenEntity({ kind: 'note', id: data.ref_id });
    }
  };

  return (
    <div
      className={`bn ${selected ? 'selected' : ''} ${tombstone ? 'bn-tombstone' : ''}`}
      style={tombstone ? undefined : { borderLeftColor: color }}
      onClick={handleClick}
    >
      <Handle type="target" position={Position.Top} />
      <div className="bn-header">
        <span className="bn-header-icon">📝</span>
        <span className="bn-header-title">
          {tombstone ? '⚠ Note deleted' : (summary?.title || 'Untitled note')}
        </span>
      </div>
      {!tombstone && (
        <div className="bn-body">
          <div className="bn-note-body nowheel">
            <NotePreview body={safePreview(summary?.body_preview)} simplified />
          </div>
        </div>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

export default memo(NoteNode);
