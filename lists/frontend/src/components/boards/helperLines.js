// Node-to-node alignment snapping for the board canvas.
//
// Adapted from ReactFlow's official "helper lines" example. Given the single
// `position` change emitted while a node is dragged, find the nearest aligned
// position (edges + centers) against the other nodes and return both the snapped
// position and the flow-space coordinates for the guide lines to draw.
//
// Groups are excluded as snap targets so a card inside a group doesn't magnet to
// the group's inner edges.

export function getHelperLines(change, nodes, distance = 6) {
  const defaultResult = {
    horizontal: undefined,
    vertical: undefined,
    snapPosition: { x: undefined, y: undefined },
  };

  const nodeA = nodes.find((n) => n.id === change.id);
  if (!nodeA || !change.position) return defaultResult;

  const aWidth = nodeA.width ?? 0;
  const aHeight = nodeA.height ?? 0;
  const aBounds = {
    left: change.position.x,
    right: change.position.x + aWidth,
    top: change.position.y,
    bottom: change.position.y + aHeight,
    centerX: change.position.x + aWidth / 2,
    centerY: change.position.y + aHeight / 2,
    width: aWidth,
    height: aHeight,
  };

  // Track the closest match found so far on each axis.
  let vDist = distance; // x-axis snapping → vertical guide line
  let hDist = distance; // y-axis snapping → horizontal guide line

  return nodes
    .filter((n) => n.id !== nodeA.id && n.data?.kind !== 'group')
    .reduce((result, nodeB) => {
      const bWidth = nodeB.width ?? 0;
      const bHeight = nodeB.height ?? 0;
      const b = {
        left: nodeB.position.x,
        right: nodeB.position.x + bWidth,
        top: nodeB.position.y,
        bottom: nodeB.position.y + bHeight,
        centerX: nodeB.position.x + bWidth / 2,
        centerY: nodeB.position.y + bHeight / 2,
      };

      // ── x-axis (vertical guide) ──────────────────────────────
      // left ↔ left
      const dLL = Math.abs(aBounds.left - b.left);
      if (dLL < vDist) {
        result.snapPosition.x = b.left;
        result.vertical = b.left;
        vDist = dLL;
      }
      // right ↔ right
      const dRR = Math.abs(aBounds.right - b.right);
      if (dRR < vDist) {
        result.snapPosition.x = b.right - aBounds.width;
        result.vertical = b.right;
        vDist = dRR;
      }
      // left ↔ right
      const dLR = Math.abs(aBounds.left - b.right);
      if (dLR < vDist) {
        result.snapPosition.x = b.right;
        result.vertical = b.right;
        vDist = dLR;
      }
      // right ↔ left
      const dRL = Math.abs(aBounds.right - b.left);
      if (dRL < vDist) {
        result.snapPosition.x = b.left - aBounds.width;
        result.vertical = b.left;
        vDist = dRL;
      }
      // center-x ↔ center-x
      const dCX = Math.abs(aBounds.centerX - b.centerX);
      if (dCX < vDist) {
        result.snapPosition.x = b.centerX - aBounds.width / 2;
        result.vertical = b.centerX;
        vDist = dCX;
      }

      // ── y-axis (horizontal guide) ────────────────────────────
      // top ↔ top
      const dTT = Math.abs(aBounds.top - b.top);
      if (dTT < hDist) {
        result.snapPosition.y = b.top;
        result.horizontal = b.top;
        hDist = dTT;
      }
      // bottom ↔ bottom
      const dBB = Math.abs(aBounds.bottom - b.bottom);
      if (dBB < hDist) {
        result.snapPosition.y = b.bottom - aBounds.height;
        result.horizontal = b.bottom;
        hDist = dBB;
      }
      // top ↔ bottom
      const dTB = Math.abs(aBounds.top - b.bottom);
      if (dTB < hDist) {
        result.snapPosition.y = b.bottom;
        result.horizontal = b.bottom;
        hDist = dTB;
      }
      // bottom ↔ top
      const dBT = Math.abs(aBounds.bottom - b.top);
      if (dBT < hDist) {
        result.snapPosition.y = b.top - aBounds.height;
        result.horizontal = b.top;
        hDist = dBT;
      }
      // center-y ↔ center-y
      const dCY = Math.abs(aBounds.centerY - b.centerY);
      if (dCY < hDist) {
        result.snapPosition.y = b.centerY - aBounds.height / 2;
        result.horizontal = b.centerY;
        hDist = dCY;
      }

      return result;
    }, defaultResult);
}

// Snapping while *resizing* a node: snap whichever edge is being dragged to a
// nearby node's edge or center. NodeResizer emits a `dimensions` change (and a
// `position` change when the top/left handle moves); we derive the new bounds,
// figure out which edges moved, and align them. Returns the adjusted
// width/height/x/y plus guide-line coords, or null when nothing is in range.
export function getResizeHelperLines(self, dimChange, posChange, nodes, distance = 6) {
  const curL = self.position.x;
  const curT = self.position.y;
  const curR = curL + (self.width ?? 0);
  const curB = curT + (self.height ?? 0);
  const x0 = posChange ? posChange.position.x : curL;
  const y0 = posChange ? posChange.position.y : curT;
  const left = x0;
  const top = y0;
  const right = x0 + dimChange.dimensions.width;
  const bottom = y0 + dimChange.dimensions.height;

  const EPS = 0.5;
  const movingLeft = Math.abs(left - curL) > EPS;
  const movingRight = Math.abs(right - curR) > EPS;
  const movingTop = Math.abs(top - curT) > EPS;
  const movingBottom = Math.abs(bottom - curB) > EPS;

  let bestX = distance;
  let bestY = distance;
  let vertical;
  let horizontal;
  let snapLeft = left;
  let snapRight = right;
  let snapTop = top;
  let snapBottom = bottom;

  for (const nb of nodes) {
    if (nb.id === self.id || nb.data?.kind === 'group') continue;
    const bL = nb.position.x;
    const bR = nb.position.x + (nb.width ?? 0);
    const bT = nb.position.y;
    const bB = nb.position.y + (nb.height ?? 0);
    const xs = [bL, bR, (bL + bR) / 2];
    const ys = [bT, bB, (bT + bB) / 2];
    if (movingRight) for (const t of xs) { const d = Math.abs(right - t); if (d < bestX) { bestX = d; snapRight = t; vertical = t; } }
    if (movingLeft) for (const t of xs) { const d = Math.abs(left - t); if (d < bestX) { bestX = d; snapLeft = t; vertical = t; } }
    if (movingBottom) for (const t of ys) { const d = Math.abs(bottom - t); if (d < bestY) { bestY = d; snapBottom = t; horizontal = t; } }
    if (movingTop) for (const t of ys) { const d = Math.abs(top - t); if (d < bestY) { bestY = d; snapTop = t; horizontal = t; } }
  }

  let width = dimChange.dimensions.width;
  let height = dimChange.dimensions.height;
  let x = x0;
  let y = y0;
  let outV;
  let outH;
  if (vertical != null) {
    const w = snapRight - snapLeft;
    if (w >= 40) { width = w; x = snapLeft; outV = vertical; }
  }
  if (horizontal != null) {
    const h = snapBottom - snapTop;
    if (h >= 40) { height = h; y = snapTop; outH = horizontal; }
  }
  if (outV == null && outH == null) return null;
  return { width, height, x, y, vertical: outV, horizontal: outH };
}
