import { useEffect, useMemo, useRef, useState } from 'react';
import * as api from '../../api';

const W = 900;
const H = 640;
const ITERATIONS = 220;
const REPEL = 1800;
const SPRING = 0.04;
const SPRING_LEN = 110;
const CENTER = 0.012;
const DAMPING = 0.82;

function simulate(nodes, edges) {
  const n = nodes.length;
  if (n === 0) return [];
  const pts = nodes.map((node, i) => {
    const angle = (i / Math.max(1, n)) * Math.PI * 2;
    const r = Math.min(W, H) * 0.32;
    return {
      id: node.id,
      x: W / 2 + Math.cos(angle) * r,
      y: H / 2 + Math.sin(angle) * r,
      vx: 0,
      vy: 0,
    };
  });
  const idx = new Map(pts.map((p, i) => [p.id, i]));
  const adj = edges
    .map((e) => [idx.get(e.source), idx.get(e.target)])
    .filter(([a, b]) => a !== undefined && b !== undefined);

  for (let step = 0; step < ITERATIONS; step++) {
    for (let i = 0; i < n; i++) {
      const a = pts[i];
      let fx = 0;
      let fy = 0;
      for (let j = 0; j < n; j++) {
        if (i === j) continue;
        const b = pts[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const d2 = dx * dx + dy * dy + 0.01;
        const f = REPEL / d2;
        fx += (dx / Math.sqrt(d2)) * f;
        fy += (dy / Math.sqrt(d2)) * f;
      }
      fx += (W / 2 - a.x) * CENTER;
      fy += (H / 2 - a.y) * CENTER;
      a.vx = (a.vx + fx) * DAMPING;
      a.vy = (a.vy + fy) * DAMPING;
    }
    for (const [ai, bi] of adj) {
      const a = pts[ai];
      const b = pts[bi];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const d = Math.sqrt(dx * dx + dy * dy) + 0.01;
      const k = SPRING * (d - SPRING_LEN);
      const fx = (dx / d) * k;
      const fy = (dy / d) * k;
      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }
    for (const p of pts) {
      p.x += p.vx;
      p.y += p.vy;
      p.x = Math.max(20, Math.min(W - 20, p.x));
      p.y = Math.max(20, Math.min(H - 20, p.y));
    }
  }
  return pts;
}

export default function NoteGraph({ onSelect }) {
  const [data, setData] = useState({ nodes: [], edges: [] });
  const [hover, setHover] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.getNoteGraph()
      .then((d) => { if (!cancelled) { setData(d); setError(null); } })
      .catch((e) => { if (!cancelled) setError(e.message || 'Failed to load graph'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const positioned = useMemo(() => {
    const pts = simulate(data.nodes || [], data.edges || []);
    const byId = new Map(pts.map((p) => [p.id, p]));
    const nodeMap = new Map((data.nodes || []).map((n) => [n.id, n]));
    const degree = new Map();
    for (const e of data.edges || []) {
      degree.set(e.source, (degree.get(e.source) || 0) + 1);
      degree.set(e.target, (degree.get(e.target) || 0) + 1);
    }
    return {
      nodes: pts.map((p) => ({
        ...p,
        meta: nodeMap.get(p.id),
        degree: degree.get(p.id) || 0,
      })),
      edges: (data.edges || []).map((e) => ({
        ...e,
        a: byId.get(e.source),
        b: byId.get(e.target),
      })).filter((e) => e.a && e.b),
    };
  }, [data]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-ink-3">
        Loading graph…
      </div>
    );
  }
  if (error) {
    return (
      <div className="flex h-full items-center justify-center text-semantic-danger">
        {error}
      </div>
    );
  }
  if (positioned.nodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-ink-3 text-sm">
        No notes yet — create some and link them with <code className="font-mono mx-1">[[wikilinks]]</code> to see your graph
      </div>
    );
  }

  return (
    <div className="h-full w-full overflow-auto bg-surface-1">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="block w-full h-full"
        style={{ minHeight: H }}
      >
        <g stroke="var(--line-2, #2a2f3a)" strokeWidth="1">
          {positioned.edges.map((e, i) => (
            <line
              key={i}
              x1={e.a.x}
              y1={e.a.y}
              x2={e.b.x}
              y2={e.b.y}
              opacity={hover ? (e.source === hover || e.target === hover ? 0.9 : 0.18) : 0.55}
              stroke={e.link_type === 'embed' ? 'var(--brand-orange-400, #ff8a4d)' : 'var(--brand-cobalt-400, #6191e6)'}
            />
          ))}
        </g>
        <g>
          {positioned.nodes.map((n) => {
            const r = 6 + Math.min(14, Math.sqrt(n.degree) * 3);
            const isHover = hover === n.id;
            return (
              <g
                key={n.id}
                transform={`translate(${n.x}, ${n.y})`}
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHover(n.id)}
                onMouseLeave={() => setHover((h) => (h === n.id ? null : h))}
                onClick={() => onSelect && onSelect({ kind: 'note', id: n.id })}
              >
                <circle
                  r={r}
                  fill={isHover ? 'var(--brand-orange, #ff4f00)' : 'var(--brand-cobalt, #0047ab)'}
                  stroke="var(--bg-0, #0e1116)"
                  strokeWidth="1.5"
                />
                <text
                  y={r + 12}
                  textAnchor="middle"
                  fontSize="11"
                  fill="var(--fg-2, #c9d1d9)"
                  pointerEvents="none"
                  opacity={hover ? (isHover ? 1 : 0.35) : 0.85}
                >
                  {(n.meta?.title || '').slice(0, 24)}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
