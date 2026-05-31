import { useEffect, useRef } from 'react';
import { useStore } from 'reactflow';

// Overlay that draws alignment guide lines while a node is dragged. The
// `horizontal` / `vertical` props are flow-space coordinates (from
// getHelperLines); we project them through the live viewport transform and
// stroke 1px lines across the canvas.

const GUIDE_COLOR = '#FF4F00'; // International Orange — design-system accent

const canvasStyle = {
  position: 'absolute',
  top: 0,
  left: 0,
  width: '100%',
  height: '100%',
  pointerEvents: 'none',
  zIndex: 10,
};

export default function HelperLines({ horizontal, vertical }) {
  const width = useStore((s) => s.width);
  const height = useStore((s) => s.height);
  const tx = useStore((s) => s.transform[0]);
  const ty = useStore((s) => s.transform[1]);
  const zoom = useStore((s) => s.transform[2]);
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx || !width || !height) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = GUIDE_COLOR;
    ctx.lineWidth = 1;

    if (typeof vertical === 'number') {
      const x = vertical * zoom + tx;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    if (typeof horizontal === 'number') {
      const y = horizontal * zoom + ty;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  }, [width, height, tx, ty, zoom, horizontal, vertical]);

  return <canvas ref={canvasRef} className="board-helper-lines" style={canvasStyle} />;
}
