import { memo } from 'react';
import { Handle, Position } from 'reactflow';

function ListNode({ data, selected }) {
  const summary = data?.ref_summary;
  const tombstone = !summary && (data?.kind === 'list');
  const color = data?.color || 'var(--brand-cobalt)';

  const itemCount = summary?.item_count ?? 0;
  const completedCount = summary?.completed_count ?? 0;
  const progress = itemCount > 0 ? Math.min(100, Math.round((completedCount / itemCount) * 100)) : 0;

  const handleClick = (e) => {
    if (e.defaultPrevented) return;
    if (data?.onOpenEntity && !tombstone) {
      data.onOpenEntity({ kind: 'list', id: data.ref_id });
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
        <span className="bn-header-icon">📋</span>
        <span className="bn-header-title">
          {tombstone ? '⚠ List deleted' : (summary?.name || 'Untitled list')}
        </span>
      </div>
      {!tombstone && (
        <>
          <div className="bn-body">
            <div className="bn-progress" aria-label="progress">
              <div className="bn-progress-bar" style={{ width: `${progress}%` }} />
            </div>
          </div>
          <div className="bn-footer">
            {completedCount} / {itemCount} done
          </div>
        </>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

export default memo(ListNode);
