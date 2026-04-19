import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { attachmentUrl } from '../../../api';

function iconForMime(mime = '') {
  if (mime.startsWith('image/')) return '🖼️';
  if (mime.startsWith('video/')) return '🎞️';
  if (mime.startsWith('audio/')) return '🎧';
  if (mime.includes('pdf')) return '📕';
  if (mime.includes('zip') || mime.includes('tar') || mime.includes('gzip')) return '🗜️';
  if (mime.startsWith('text/')) return '📄';
  return '📎';
}

function formatSize(n) {
  if (!Number.isFinite(n) || n < 0) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function FileNode({ data, selected }) {
  const href = data?.board_id && data?.media_filename
    ? attachmentUrl(data.board_id, data.media_filename)
    : null;
  const label = data?.title || data?.media_alt || data?.media_filename || 'file';
  const size = formatSize(data?.media_size);

  return (
    <div
      className={`bn bn-file ${selected ? 'selected' : ''}`}
      onClick={(e) => e.stopPropagation()}
    >
      <Handle type="target" position={Position.Top} />
      <div className="bn-header">
        <span className="bn-header-icon">{iconForMime(data?.media_mime)}</span>
        <span className="bn-header-title" title={label}>{label}</span>
      </div>
      <div className="bn-body bn-file-body">
        <div className="bn-file-meta">
          {data?.media_mime && <span className="bn-file-mime">{data.media_mime}</span>}
          {size && <span className="bn-file-size">{size}</span>}
        </div>
        {href && (
          <a
            className="bn-file-download nodrag"
            href={href}
            download={data?.title || data?.media_filename}
            target="_blank"
            rel="noopener noreferrer"
          >
            ⬇ Download
          </a>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

export default memo(FileNode);
