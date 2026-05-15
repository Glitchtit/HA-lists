import { useEffect, useRef, useState } from 'react';

const HOVER_DELAY_MS = 350;
const POPUP_WIDTH = 360;
const POPUP_MAX_HEIGHT = 320;

export default function Wikilink({ title, onClick, onResolve, children }) {
  const [hovered, setHovered] = useState(false);
  const [note, setNote] = useState(null);
  const [pos, setPos] = useState(null);
  const enterTimerRef = useRef(null);
  const leaveTimerRef = useRef(null);
  const linkRef = useRef(null);

  useEffect(() => () => {
    if (enterTimerRef.current) clearTimeout(enterTimerRef.current);
    if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current);
  }, []);

  function computePosition() {
    const el = linkRef.current;
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    const top = rect.bottom + 6;
    let left = rect.left;
    if (left + POPUP_WIDTH + 12 > window.innerWidth) {
      left = Math.max(8, window.innerWidth - POPUP_WIDTH - 12);
    }
    const flipUp = top + POPUP_MAX_HEIGHT + 12 > window.innerHeight;
    return { left, top: flipUp ? Math.max(8, rect.top - POPUP_MAX_HEIGHT - 6) : top };
  }

  function startHover() {
    if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current);
    if (enterTimerRef.current) clearTimeout(enterTimerRef.current);
    enterTimerRef.current = setTimeout(async () => {
      if (!onResolve) return;
      setPos(computePosition());
      setHovered(true);
      try {
        const n = await onResolve(title);
        setNote(n || null);
      } catch {
        setNote(null);
      }
    }, HOVER_DELAY_MS);
  }

  function endHover() {
    if (enterTimerRef.current) clearTimeout(enterTimerRef.current);
    leaveTimerRef.current = setTimeout(() => {
      setHovered(false);
      setNote(null);
    }, 120);
  }

  return (
    <>
      <span
        ref={linkRef}
        className="wikilink"
        role="button"
        tabIndex={0}
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClick && onClick(title); }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onClick && onClick(title);
          }
        }}
        onMouseEnter={startHover}
        onMouseLeave={endHover}
        onFocus={startHover}
        onBlur={endHover}
      >
        {children}
      </span>
      {hovered && pos && (
        <div
          role="tooltip"
          onMouseEnter={() => { if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current); }}
          onMouseLeave={endHover}
          style={{
            position: 'fixed',
            left: pos.left,
            top: pos.top,
            width: POPUP_WIDTH,
            maxHeight: POPUP_MAX_HEIGHT,
            zIndex: 60,
          }}
          className="overflow-auto rounded-xl border border-line-1 bg-surface-2 px-3 py-2 text-sm text-ink-1 shadow-lg"
        >
          {note === null ? (
            <div className="text-xs text-ink-3 italic">
              {title} — not found
            </div>
          ) : (
            <>
              <div className="mb-1 flex items-center gap-2 text-xs text-ink-3">
                <span>{note.icon || '📄'}</span>
                <span className="truncate font-medium">{note.title || 'Untitled'}</span>
              </div>
              <pre className="whitespace-pre-wrap break-words text-xs text-ink-2 font-sans">
                {(note.body || '').slice(0, 700)}
                {(note.body || '').length > 700 ? '…' : ''}
              </pre>
            </>
          )}
        </div>
      )}
    </>
  );
}
