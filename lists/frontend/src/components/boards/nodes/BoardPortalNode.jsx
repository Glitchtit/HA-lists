import { memo } from 'react';
import { Handle, Position } from 'reactflow';

function formatTimestamp(raw) {
  if (!raw) return '';
  try {
    const d = new Date(raw.includes('T') ? raw : raw.replace(' ', 'T') + 'Z');
    if (Number.isNaN(d.getTime())) return raw;
    return d.toLocaleString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return raw;
  }
}

function BoardPortalNode({ data, selected }) {
  const summary = data?.ref_summary;
  const tombstone = data?.ref_id != null && !summary;
  const color = data?.color || 'var(--brand-orange)';

  const handleClick = (e) => {
    if (e.defaultPrevented) return;
    if (data?.onOpenEntity && !tombstone) {
      data.onOpenEntity({ kind: 'board', id: data.ref_id });
    }
  };

  const handleDoubleClick = (e) => {
    if (e.defaultPrevented) return;
    if (data?.onOpenEntity && !tombstone) {
      e.stopPropagation();
      data.onOpenEntity({ kind: 'board', id: data.ref_id });
    }
  };

  const nodeCount = summary?.node_count ?? 0;
  const edgeCount = summary?.edge_count ?? 0;

  return (
    <div
      className={`bn bn-portal ${selected ? 'selected' : ''} ${tombstone ? 'bn-tombstone' : ''}`}
      style={tombstone ? undefined : { borderLeftColor: color }}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      title={tombstone ? 'Target board deleted' : 'Double-click to open this board'}
    >
      <Handle type="target" position={Position.Top} />
      <div className="bn-header">
        <span className="bn-header-icon">{tombstone ? '⚠' : (summary?.icon || '🗂️')}</span>
        <span className="bn-header-title">
          {tombstone ? '⚠ Board deleted' : (summary?.name || 'Untitled board')}
        </span>
      </div>
      {!tombstone && (
        <>
          <div className="bn-body">
            <div className="bn-portal-stats">
              <span className="bn-portal-stat">
                <span className="bn-portal-stat-num">{nodeCount}</span>
                <span className="bn-portal-stat-lbl">{nodeCount === 1 ? 'card' : 'cards'}</span>
              </span>
              <span className="bn-portal-sep">·</span>
              <span className="bn-portal-stat">
                <span className="bn-portal-stat-num">{edgeCount}</span>
                <span className="bn-portal-stat-lbl">{edgeCount === 1 ? 'link' : 'links'}</span>
              </span>
            </div>
          </div>
          <div className="bn-footer">
            {summary?.last_modified
              ? `Updated ${formatTimestamp(summary.last_modified)}`
              : 'Open board →'}
          </div>
        </>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

export default memo(BoardPortalNode);
