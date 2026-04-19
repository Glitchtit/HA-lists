import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import NotePreview from '../../notes/NotePreview';

function NoteNode({ data, selected }) {
  const summary = data?.ref_summary;
  const tombstone = !summary && (data?.kind === 'note');
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
            <NotePreview body={summary?.body_preview || ''} />
          </div>
        </div>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

export default memo(NoteNode);
