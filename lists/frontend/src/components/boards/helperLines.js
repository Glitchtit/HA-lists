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
