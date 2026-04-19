import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';

import {
  getBoard,
  createBoardNode,
  updateBoardNode,
  deleteBoardNode,
  bulkUpdateBoardNodePositions,
  createBoardEdge,
  deleteBoardEdge,
  updateBoardViewport,
} from '../../api';

import ListNode from './nodes/ListNode';
import NoteNode from './nodes/NoteNode';
import CardNode from './nodes/CardNode';
import NodeToolbar from './NodeToolbar';
import './boards.css';

const NODE_TYPES = { list: ListNode, note: NoteNode, card: CardNode };

function toFlowNode(bn, handlers) {
  return {
    id: String(bn.id),
    type: bn.kind,
    position: { x: Number(bn.x ?? 0), y: Number(bn.y ?? 0) },
    width: bn.width || undefined,
    height: bn.height || undefined,
    data: { ...bn, ...handlers },
  };
}

function toFlowEdge(be) {
  return {
    id: String(be.id),
    source: String(be.source_node_id),
    target: String(be.target_node_id),
    label: be.label || undefined,
    data: { ...be },
  };
}

function BoardCanvas({ boardId, onOpenEntity }) {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewport, setViewport] = useState(null);
  const [ctxMenu, setCtxMenu] = useState(null); // {type:'node'|'edge', x, y, target}

  const rf = useReactFlow();
  const wrapperRef = useRef(null);

  // Position autosave
  const pendingPositionsRef = useRef(new Map());
  const positionTimerRef = useRef(null);

  // Viewport autosave
  const viewportTimerRef = useRef(null);

  const flushPositions = useCallback(() => {
    const map = pendingPositionsRef.current;
    if (!map || map.size === 0) return;
    const positions = Array.from(map.entries()).map(([id, p]) => ({
      id: Number(id),
      x: p.x,
      y: p.y,
    }));
    pendingPositionsRef.current = new Map();
    if (positionTimerRef.current) {
      clearTimeout(positionTimerRef.current);
      positionTimerRef.current = null;
    }
    bulkUpdateBoardNodePositions(boardId, positions).catch(() => {
      // best-effort; keep client state as-is on failure
    });
  }, [boardId]);

  const schedulePositionFlush = useCallback(() => {
    if (positionTimerRef.current) clearTimeout(positionTimerRef.current);
    positionTimerRef.current = setTimeout(() => {
      positionTimerRef.current = null;
      flushPositions();
    }, 300);
  }, [flushPositions]);

  // ─ Update helpers injected into node data ────────────────
  const handleNodeUpdate = useCallback(async (nodeId, patch) => {
    setNodes((ns) => ns.map((n) => n.id === String(nodeId)
      ? { ...n, data: { ...n.data, ...patch } }
      : n));
    try {
      await updateBoardNode(boardId, nodeId, patch);
    } catch (e) {
      // best-effort rollback: refetch node data
    }
  }, [boardId]);

  const handleNodeDelete = useCallback(async (nodeId) => {
    setNodes((ns) => ns.filter((n) => n.id !== String(nodeId)));
    setEdges((es) => es.filter((e) => e.source !== String(nodeId) && e.target !== String(nodeId)));
    try { await deleteBoardNode(boardId, nodeId); } catch (e) { /* ignore */ }
  }, [boardId]);

  const nodeHandlers = useMemo(() => ({
    onOpenEntity,
    onUpdate: undefined, // attached per-node below
    onDelete: undefined,
  }), [onOpenEntity]);

  const attachHandlers = useCallback((bn) => ({
    ...bn,
    onOpenEntity,
    onUpdate: (patch) => handleNodeUpdate(bn.id, patch),
    onDelete: () => handleNodeDelete(bn.id),
  }), [onOpenEntity, handleNodeUpdate, handleNodeDelete]);

  // ─ Initial load ──────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getBoard(boardId)
      .then((data) => {
        if (cancelled) return;
        const bn = (data.nodes || []).map((n) => toFlowNode(n, {}));
        // Rebuild with handlers bound to up-to-date ids
        const withHandlers = bn.map((fn) => ({
          ...fn,
          data: {
            ...fn.data,
            onOpenEntity,
            onUpdate: (patch) => handleNodeUpdate(fn.id, patch),
            onDelete: () => handleNodeDelete(fn.id),
          },
        }));
        setNodes(withHandlers);
        setEdges((data.edges || []).map(toFlowEdge));
        const vp = data.board?.viewport;
        if (vp && typeof vp === 'object') setViewport(vp);
        setLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e?.message || 'Failed to load board');
        setLoading(false);
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boardId]);

  // Apply loaded viewport once rf is ready
  useEffect(() => {
    if (viewport && rf && typeof rf.setViewport === 'function') {
      try { rf.setViewport(viewport); } catch (e) { /* ignore */ }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewport]);

  // Flush pending position edits on unmount/board change
  useEffect(() => () => {
    if (positionTimerRef.current) clearTimeout(positionTimerRef.current);
    if (viewportTimerRef.current) clearTimeout(viewportTimerRef.current);
    flushPositions();
  }, [flushPositions]);

  // ─ ReactFlow change handlers ─────────────────────────────
  const onNodesChange = useCallback((changes) => {
    setNodes((ns) => applyNodeChanges(changes, ns));
    for (const ch of changes) {
      if (ch.type === 'position' && ch.position && !ch.dragging) {
        // position finalised mid-interaction
        pendingPositionsRef.current.set(ch.id, ch.position);
        schedulePositionFlush();
      } else if (ch.type === 'position' && ch.position) {
        // dragging — collect continuously
        pendingPositionsRef.current.set(ch.id, ch.position);
        schedulePositionFlush();
      }
    }
  }, [schedulePositionFlush]);

  const onEdgesChange = useCallback((changes) => {
    setEdges((es) => applyEdgeChanges(changes, es));
  }, []);

  const onNodeDragStop = useCallback((_e, node) => {
    pendingPositionsRef.current.set(node.id, node.position);
    flushPositions();
  }, [flushPositions]);

  const onConnect = useCallback(async (params) => {
    const tempId = `tmp-${Date.now()}`;
    const optimistic = { ...params, id: tempId };
    setEdges((es) => addEdge(optimistic, es));
    try {
      const created = await createBoardEdge(boardId, {
        source_node_id: Number(params.source),
        target_node_id: Number(params.target),
      });
      setEdges((es) => es.map((e) => (e.id === tempId ? toFlowEdge(created) : e)));
    } catch (err) {
      setEdges((es) => es.filter((e) => e.id !== tempId));
    }
  }, [boardId]);

  const onEdgesDelete = useCallback((deleted) => {
    for (const e of deleted) {
      if (String(e.id).startsWith('tmp-')) continue;
      deleteBoardEdge(boardId, e.id).catch(() => {});
    }
  }, [boardId]);

  const onNodesDelete = useCallback((deleted) => {
    for (const n of deleted) {
      deleteBoardNode(boardId, n.id).catch(() => {});
    }
  }, [boardId]);

  const onMove = useCallback((_e, vp) => {
    if (viewportTimerRef.current) clearTimeout(viewportTimerRef.current);
    viewportTimerRef.current = setTimeout(() => {
      viewportTimerRef.current = null;
      updateBoardViewport(boardId, vp).catch(() => {});
    }, 500);
  }, [boardId]);

  // ─ Node creation helpers ─────────────────────────────────
  const viewportCenter = useCallback(() => {
    const el = wrapperRef.current;
    if (!el || !rf) return { x: 0, y: 0 };
    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    if (typeof rf.screenToFlowPosition === 'function') {
      return rf.screenToFlowPosition({ x: cx, y: cy });
    }
    if (typeof rf.project === 'function') {
      return rf.project({ x: rect.width / 2, y: rect.height / 2 });
    }
    return { x: 0, y: 0 };
  }, [rf]);

  const projectClient = useCallback((clientX, clientY) => {
    if (rf && typeof rf.screenToFlowPosition === 'function') {
      return rf.screenToFlowPosition({ x: clientX, y: clientY });
    }
    const el = wrapperRef.current;
    if (!el || !rf || typeof rf.project !== 'function') return viewportCenter();
    const rect = el.getBoundingClientRect();
    return rf.project({ x: clientX - rect.left, y: clientY - rect.top });
  }, [rf, viewportCenter]);

  const insertNode = useCallback(async (payload, refSummary = null) => {
    try {
      const created = await createBoardNode(boardId, payload);
      const fn = toFlowNode(created, {});
      fn.data = {
        ...fn.data,
        // Optimistically supply ref_summary from the known item so the node
        // doesn't flash as "deleted" before the next full board reload.
        ref_summary: refSummary ?? fn.data.ref_summary ?? null,
        onOpenEntity,
        onUpdate: (patch) => handleNodeUpdate(created.id, patch),
        onDelete: () => handleNodeDelete(created.id),
      };
      setNodes((ns) => [...ns, fn]);
      return created;
    } catch (e) {
      return null;
    }
  }, [boardId, onOpenEntity, handleNodeUpdate, handleNodeDelete]);

  const onAddCard = useCallback(() => {
    const { x, y } = viewportCenter();
    insertNode({ kind: 'card', x, y, title: 'New card', body: '' });
  }, [insertNode, viewportCenter]);

  const onAddList = useCallback((item) => {
    const { x, y } = viewportCenter();
    const refSummary = {
      id: item.id,
      name: item.name || 'Untitled list',
      icon: item.icon || '📋',
      color: item.color || '',
      item_count: item.item_count ?? 0,
      completed_count: item.completed_count ?? 0,
    };
    insertNode({ kind: 'list', ref_id: item.id, x, y }, refSummary);
  }, [insertNode, viewportCenter]);

  const onAddNote = useCallback((item) => {
    const { x, y } = viewportCenter();
    const refSummary = {
      id: item.id,
      title: item.title || 'Untitled note',
      icon: item.icon || '📝',
      body_preview: (item.body || '').slice(0, 400),
    };
    insertNode({ kind: 'note', ref_id: item.id, x, y }, refSummary);
  }, [insertNode, viewportCenter]);

  // ─ Drag & drop: toolbar / sidebar → canvas ───────────────
  const DND_TYPE = 'application/x-ha-lists-board-node';

  const handleToolbarDragStart = useCallback((e, payload) => {
    try {
      e.dataTransfer.setData(DND_TYPE, JSON.stringify(payload));
      e.dataTransfer.setData('text/plain', payload.kind);
      e.dataTransfer.effectAllowed = 'copy';
    } catch (err) { /* ignore */ }
  }, []);

  const onCanvasDragOver = useCallback((e) => {
    const types = e.dataTransfer?.types;
    if (!types) return;
    const has = Array.from(types).some((t) => t === DND_TYPE || t === 'text/plain');
    if (!has) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  const onCanvasDrop = useCallback((e) => {
    let raw = '';
    try { raw = e.dataTransfer.getData(DND_TYPE) || ''; } catch (err) { /* ignore */ }
    if (!raw) {
      // fall back to text/plain (sidebar drags)
      let fallback = '';
      try { fallback = e.dataTransfer.getData('text/plain') || ''; } catch (err) { /* ignore */ }
      if (!fallback) return;
      try { raw = fallback.startsWith('{') ? fallback : ''; } catch (err) { /* ignore */ }
      if (!raw) return;
    }
    e.preventDefault();
    let payload;
    try { payload = JSON.parse(raw); } catch (err) { return; }
    if (!payload?.kind) return;
    const pos = projectClient(e.clientX, e.clientY);
    if (payload.kind === 'card') {
      insertNode({ kind: 'card', x: pos.x, y: pos.y, title: payload.item?.title || 'New card', body: payload.item?.body || '' });
    } else if (payload.kind === 'list' && payload.item?.id) {
      const refSummary = {
        id: payload.item.id,
        name: payload.item.name || 'Untitled list',
        icon: payload.item.icon || '📋',
        color: payload.item.color || '',
        item_count: payload.item.item_count ?? 0,
        completed_count: payload.item.completed_count ?? 0,
      };
      insertNode({ kind: 'list', ref_id: payload.item.id, x: pos.x, y: pos.y }, refSummary);
    } else if (payload.kind === 'note' && payload.item?.id) {
      const refSummary = {
        id: payload.item.id,
        title: payload.item.title || 'Untitled note',
        icon: payload.item.icon || '📝',
        body_preview: (payload.item.body || '').slice(0, 400),
      };
      insertNode({ kind: 'note', ref_id: payload.item.id, x: pos.x, y: pos.y }, refSummary);
    }
  }, [insertNode, projectClient]);

  // ─ Keyboard: guard Delete/Backspace when focused in input ─
  const isEditableFocused = () => {
    const el = document.activeElement;
    if (!el) return false;
    const tag = el.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
    if (el.isContentEditable) return true;
    return false;
  };
  const [deleteKeys, setDeleteKeys] = useState(['Backspace', 'Delete']);
  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== 'Backspace' && e.key !== 'Delete') return;
      if (isEditableFocused()) setDeleteKeys(null);
      else setDeleteKeys(['Backspace', 'Delete']);
    };
    const onKeyUp = () => setDeleteKeys(['Backspace', 'Delete']);
    window.addEventListener('keydown', onKey, true);
    window.addEventListener('keyup', onKeyUp, true);
    return () => {
      window.removeEventListener('keydown', onKey, true);
      window.removeEventListener('keyup', onKeyUp, true);
    };
  }, []);

  // ─ Context menu ──────────────────────────────────────────
  const closeCtx = useCallback(() => setCtxMenu(null), []);
  useEffect(() => {
    if (!ctxMenu) return undefined;
    const onDown = () => closeCtx();
    window.addEventListener('mousedown', onDown);
    window.addEventListener('scroll', onDown, true);
    return () => {
      window.removeEventListener('mousedown', onDown);
      window.removeEventListener('scroll', onDown, true);
    };
  }, [ctxMenu, closeCtx]);

  const onNodeContextMenu = useCallback((e, node) => {
    e.preventDefault();
    setCtxMenu({ type: 'node', x: e.clientX, y: e.clientY, target: node });
  }, []);
  const onEdgeContextMenu = useCallback((e, edge) => {
    e.preventDefault();
    setCtxMenu({ type: 'edge', x: e.clientX, y: e.clientY, target: edge });
  }, []);

  const duplicateNode = useCallback(async (node) => {
    const base = node.data || {};
    const payload = {
      kind: base.kind,
      x: (node.position?.x || 0) + 40,
      y: (node.position?.y || 0) + 40,
      ref_id: base.ref_id ?? undefined,
      title: base.title ?? undefined,
      body: base.body ?? undefined,
      color: base.color ?? undefined,
    };
    await insertNode(payload);
  }, [insertNode]);

  const renameCard = useCallback(async (node) => {
    const current = node.data?.title || '';
    // eslint-disable-next-line no-alert
    const next = window.prompt('Rename card', current);
    if (next != null && next !== current) {
      await handleNodeUpdate(node.id, { title: next });
    }
  }, [handleNodeUpdate]);

  const changeColor = useCallback(async (node) => {
    // eslint-disable-next-line no-alert
    const next = window.prompt('Colour (CSS value or preset name)', node.data?.color || '');
    if (next != null) await handleNodeUpdate(node.id, { color: next || null });
  }, [handleNodeUpdate]);

  const renameEdgeLabel = useCallback(async (edge) => {
    const current = edge.data?.label || edge.label || '';
    // eslint-disable-next-line no-alert
    const next = window.prompt('Edge label', current);
    if (next == null) return;
    setEdges((es) => es.map((e) => (e.id === edge.id ? { ...e, label: next || undefined, data: { ...e.data, label: next } } : e)));
    try { await import('../../api').then((m) => m.updateBoardEdge(boardId, edge.id, { label: next || null })); }
    catch (err) { /* ignore */ }
  }, [boardId]);

  const deleteEdgeNow = useCallback(async (edge) => {
    setEdges((es) => es.filter((e) => e.id !== edge.id));
    try { await deleteBoardEdge(boardId, edge.id); } catch (err) { /* ignore */ }
  }, [boardId]);

  if (loading) return <div className="board-loading">Loading board…</div>;
  if (error) return <div className="board-error">Error: {error}</div>;

  return (
    <div
      ref={wrapperRef}
      className="board-canvas"
      style={{ position: 'relative', height: '100%' }}
      onDragOver={onCanvasDragOver}
      onDrop={onCanvasDrop}
    >
      <NodeToolbar
        onAddCard={onAddCard}
        onAddList={onAddList}
        onAddNote={onAddNote}
        onDragStartNew={handleToolbarDragStart}
      />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeDragStop={onNodeDragStop}
        onConnect={onConnect}
        onEdgesDelete={onEdgesDelete}
        onNodesDelete={onNodesDelete}
        onMove={onMove}
        onNodeContextMenu={onNodeContextMenu}
        onEdgeContextMenu={onEdgeContextMenu}
        connectionMode="strict"
        deleteKeyCode={deleteKeys}
        fitView={!viewport}
        defaultViewport={viewport || undefined}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="var(--line-2)" gap={16} />
        <Controls />
        <MiniMap
          nodeColor={(n) => n.data?.color || 'var(--brand-cobalt)'}
          maskColor="rgba(10, 13, 20, 0.6)"
        />
      </ReactFlow>
      {ctxMenu && (
        <div
          className="board-ctx-menu"
          style={{ left: ctxMenu.x, top: ctxMenu.y }}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
        >
          {ctxMenu.type === 'node' ? (
            <>
              {ctxMenu.target.data?.kind === 'card' && (
                <button onClick={() => { renameCard(ctxMenu.target); closeCtx(); }}>Rename…</button>
              )}
              <button onClick={() => { duplicateNode(ctxMenu.target); closeCtx(); }}>Duplicate</button>
              <button onClick={() => { changeColor(ctxMenu.target); closeCtx(); }}>Change colour…</button>
              <hr />
              <button className="danger" onClick={() => { handleNodeDelete(ctxMenu.target.id); closeCtx(); }}>
                Delete
              </button>
            </>
          ) : (
            <>
              <button onClick={() => { renameEdgeLabel(ctxMenu.target); closeCtx(); }}>Rename label…</button>
              <hr />
              <button className="danger" onClick={() => { deleteEdgeNow(ctxMenu.target); closeCtx(); }}>
                Delete
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function BoardView({ boardId, onOpenEntity }) {
  return (
    <ReactFlowProvider>
      <BoardCanvas boardId={boardId} onOpenEntity={onOpenEntity} />
    </ReactFlowProvider>
  );
}
