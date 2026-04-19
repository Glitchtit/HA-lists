import { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';
import { attachmentUrl } from '../../../api';

function ImageNode({ data, selected }) {
  const [lightbox, setLightbox] = useState(false);
  const [editingAlt, setEditingAlt] = useState(false);
  const [altDraft, setAltDraft] = useState(data?.media_alt || '');

  const src = data?.board_id && data?.media_filename
    ? attachmentUrl(data.board_id, data.media_filename)
    : null;

  const commitAlt = () => {
    setEditingAlt(false);
    if (altDraft !== (data?.media_alt || '')) {
      data?.onUpdate?.({ media_alt: altDraft || '' });
    }
  };

  return (
    <>
      <div
        className={`bn bn-image ${selected ? 'selected' : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        <Handle type="target" position={Position.Top} />
        <div className="bn-image-wrap">
          {src ? (
            <img
              src={src}
              alt={data?.media_alt || ''}
              className="bn-image-thumb nodrag"
              onDoubleClick={() => setLightbox(true)}
              draggable={false}
            />
          ) : (
            <div className="bn-image-missing">⚠ image missing</div>
          )}
        </div>
        <div className="bn-image-meta">
          {editingAlt ? (
            <input
              className="bn-image-alt-input nodrag"
              autoFocus
              value={altDraft}
              onChange={(e) => setAltDraft(e.target.value)}
              onBlur={commitAlt}
              onKeyDown={(e) => {
                if (e.key === 'Enter') { e.preventDefault(); e.currentTarget.blur(); }
                else if (e.key === 'Escape') { setAltDraft(data?.media_alt || ''); setEditingAlt(false); }
              }}
              placeholder="Describe this image…"
            />
          ) : (
            <button
              type="button"
              className="bn-image-alt"
              title="Click to edit alt text"
              onClick={() => { setAltDraft(data?.media_alt || ''); setEditingAlt(true); }}
            >
              {data?.media_alt || <span className="bn-image-alt-empty">+ alt text</span>}
            </button>
          )}
        </div>
        <Handle type="source" position={Position.Bottom} />
      </div>
      {lightbox && src && (
        <div
          className="bn-lightbox"
          onClick={() => setLightbox(false)}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <img src={src} alt={data?.media_alt || ''} />
        </div>
      )}
    </>
  );
}

export default memo(ImageNode);
