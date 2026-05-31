import { memo, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Handle, Position } from 'reactflow';
import { attachmentUrl } from '../../../api';

function ImageNode({ data, selected }) {
  const [lightbox, setLightbox] = useState(false);
  const [editingAlt, setEditingAlt] = useState(false);
  const [altDraft, setAltDraft] = useState(data?.media_alt || '');

  const src = data?.board_id && data?.media_filename
    ? attachmentUrl(data.board_id, data.media_filename)
    : null;

  // Close the lightbox on Escape while it's open.
  useEffect(() => {
    if (!lightbox) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') { e.preventDefault(); setLightbox(false); } };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [lightbox]);

  const caption = data?.media_alt || data?.title || '';

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
              onDoubleClick={(e) => { e.stopPropagation(); setLightbox(true); }}
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
      {lightbox && src && createPortal(
        <div
          className="bn-lightbox"
          role="dialog"
          aria-modal="true"
          onClick={() => setLightbox(false)}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            className="bn-lightbox-close"
            title="Close (Esc)"
            onClick={(e) => { e.stopPropagation(); setLightbox(false); }}
          >✕</button>
          <figure className="bn-lightbox-figure" onClick={(e) => e.stopPropagation()}>
            <img src={src} alt={caption} draggable={false} />
            {caption && <figcaption>{caption}</figcaption>}
          </figure>
        </div>,
        document.body,
      )}
    </>
  );
}

export default memo(ImageNode);
