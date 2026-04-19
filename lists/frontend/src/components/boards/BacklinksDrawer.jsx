import { useEffect, useState } from 'react';
import { getBoardBacklinks } from '../../api';

export default function BacklinksDrawer({ boardId, onJump, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    if (!boardId) return;
    setLoading(true);
    getBoardBacklinks(boardId)
      .then((d) => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch(() => { if (!cancelled) { setData({ portals: [], cards: [] }); setLoading(false); } });
    return () => { cancelled = true; };
  }, [boardId]);

  const portals = data?.portals || [];
  const cards = data?.cards || [];
  const total = portals.length + cards.length;

  return (
    <div className="board-backlinks-drawer">
      <div className="board-backlinks-header">
        <div className="flex items-center gap-2">
          <span>🔗</span>
          <span className="font-medium text-ink-1">Backlinks</span>
          <span className="text-xs text-ink-3">({total})</span>
        </div>
        <button
          onClick={onClose}
          className="text-ink-3 hover:text-ink-1 px-1"
          title="Close"
        >✕</button>
      </div>
      <div className="board-backlinks-body">
        {loading && <div className="board-backlinks-empty">Loading…</div>}
        {!loading && total === 0 && (
          <div className="board-backlinks-empty">No boards or cards link here yet.</div>
        )}
        {!loading && portals.length > 0 && (
          <div className="board-backlinks-section">
            <div className="board-backlinks-section-title">Portals</div>
            {portals.map((p) => (
              <button
                key={`p-${p.node_id}`}
                className="board-backlinks-item"
                onClick={() => onJump({ kind: 'board', id: p.board_id })}
                title={p.board_name}
              >
                <span className="board-backlinks-icon">{p.board_icon || '🗂️'}</span>
                <span className="truncate">{p.board_name || 'Untitled board'}</span>
              </button>
            ))}
          </div>
        )}
        {!loading && cards.length > 0 && (
          <div className="board-backlinks-section">
            <div className="board-backlinks-section-title">Mentioned in cards</div>
            {cards.map((c) => (
              <button
                key={`c-${c.node_id}`}
                className="board-backlinks-item"
                onClick={() => onJump({ kind: 'board', id: c.board_id })}
                title={`${c.board_name} · ${c.title}`}
              >
                <span className="board-backlinks-icon">🃏</span>
                <div className="min-w-0 flex-1 text-left">
                  <div className="truncate">{c.title}</div>
                  <div className="board-backlinks-sub">
                    in {c.board_icon || '🧩'} {c.board_name}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
