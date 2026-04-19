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
import '@reactflow/node-resizer/dist/style.css';

import {
  getBoard,
  createBoardNode,
  updateBoardNode,
  deleteBoardNode,
  bulkUpdateBoardNodePositions,
  createBoardEdge,
  deleteBoardEdge,
  updateBoardViewport,
  uploadBoardAttachment,
} from '../../api';

import ListNode from './nodes/ListNode';
import NoteNode from './nodes/NoteNode';
import CardNode from './nodes/CardNode';
import ImageNode from './nodes/ImageNode';
import FileNode from './nodes/FileNode';
import GroupNode from './nodes/GroupNode';
import BoardPortalNode from './nodes/BoardPortalNode';
import NodeToolbar from './NodeToolbar';
import BacklinksDrawer from './BacklinksDrawer';
import TemplatePicker from './TemplatePicker';
import './boards.css';

const NODE_TYPES = {
  list: ListNode,
  note: NoteNode,
  card: CardNode,
  image: ImageNode,
  file: FileNode,
  group: GroupNode,
  board: BoardPortalNode,
};

const IMAGE_DEFAULT_SIZE = { width: 260, height: 220 };
const FILE_DEFAULT_SIZE = { width: 240, height: 120 };
const GROUP_DEFAULT_SIZE = { width: 420, height: 280 };
const PORTAL_DEFAULT_SIZE = { width: 260, height: 150 };

function isEditableFocused() {
  const el = document.activeElement;
  if (!el) return false;
  const tag = el.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (el.isContentEditable) return true;
  return false;
}

function toFlowNode(bn, handlers) {
  const isGroup = bn.kind === 'group';
  return {
    id: String(bn.id),
    type: bn.kind,
    position: { x: Number(bn.x ?? 0), y: Number(bn.y ?? 0) },
    width: bn.width || undefined,
    height: bn.height || undefined,
    // Groups paint behind everything so children remain clickable.
    zIndex: isGroup ? -10 : 0,
    style: isGroup && bn.width && bn.height
      ? { width: bn.width, height: bn.height }
      : undefined,
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
  const [backlinksOpen, setBacklinksOpen] = useState(false);
  const [templatePicker, setTemplatePicker] = useState(null); // {x,y,flow:{x,y}} | null
  const cursorRef = useRef({ clientX: null, clientY: null });

  const rf = useReactFlow();
  const wrapperRef = useRef(null);

  // Position autosave
  const pendingPositionsRef = useRef(new Map());
  const positionTimerRef = useRef(null);

  // Group drag tracking — when a group node is being dragged, capture the
  // start position + child snapshot so we can cascade the delta to children
  // and call /translate once on drag stop.
  const groupDragRef = useRef(null);

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

  const onNodeDragStart = useCallback((_e, node) => {
    if (node.data?.kind !== 'group') {
      groupDragRef.current = null;
      return;
    }
    const childSnapshot = nodes
      .filter((n) => n.data?.parent_group_id === Number(node.id))
      .map((n) => ({ id: n.id, startPos: { ...n.position } }));
    groupDragRef.current = {
      id: node.id,
      startPos: { ...node.position },
      children: childSnapshot,
    };
  }, [nodes]);

  const onNodeDrag = useCallback((_e, node) => {
    const ref = groupDragRef.current;
    if (!ref || ref.id !== node.id) return;
    const dx = node.position.x - ref.startPos.x;
    const dy = node.position.y - ref.startPos.y;
    if (!ref.children.length) return;
    setNodes((ns) => ns.map((n) => {
      const snap = ref.children.find((c) => c.id === n.id);
      if (!snap) return n;
      return { ...n, position: { x: snap.startPos.x + dx, y: snap.startPos.y + dy } };
    }));
  }, []);

  const _findContainingGroup = useCallback((node) => {
    // Returns the smallest group whose bbox contains node's center, or null.
    if (!node || node.data?.kind === 'group') return null;
    const cx = node.position.x + (node.width || 240) / 2;
    const cy = node.position.y + (node.height || 160) / 2;
    let hit = null;
    let hitArea = Infinity;
    for (const n of nodes) {
      if (n.data?.kind !== 'group') continue;
      if (n.id === node.id) continue;
      const w = n.width || n.data?.width || 0;
      const h = n.height || n.data?.height || 0;
      const x0 = n.position.x;
      const y0 = n.position.y;
      if (cx >= x0 && cx <= x0 + w && cy >= y0 && cy <= y0 + h) {
        const area = w * h;
        if (area < hitArea) { hit = n; hitArea = area; }
      }
    }
    return hit;
  }, [nodes]);

  const onNodeDragStop = useCallback((_e, node) => {
    pendingPositionsRef.current.set(node.id, node.position);
    const ref = groupDragRef.current;
    if (ref && ref.id === node.id) {
      const dx = node.position.x - ref.startPos.x;
      const dy = node.position.y - ref.startPos.y;
      // Persist children's new positions so a refresh sees them.
      for (const snap of ref.children) {
        pendingPositionsRef.current.set(snap.id, {
          x: snap.startPos.x + dx,
          y: snap.startPos.y + dy,
        });
      }
      groupDragRef.current = null;
    } else {
      // Drop-to-group: a non-group node may have landed inside a group.
      const target = _findContainingGroup(node);
      const currentParent = node.data?.parent_group_id ?? null;
      const targetId = target ? Number(target.id) : null;
      if (target && targetId !== currentParent) {
        handleNodeUpdate(node.id, { parent_group_id: targetId });
      }
    }
    flushPositions();
  }, [flushPositions, _findContainingGroup, handleNodeUpdate, boardId]);

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

  const onAddBoard = useCallback((item) => {
    if (!item?.id || item.id === boardId) return;
    const { x, y } = viewportCenter();
    const refSummary = {
      id: item.id,
      name: item.name || 'Untitled board',
      icon: item.icon || '🗂️',
      color: item.color || '',
      node_count: item.node_count ?? 0,
      edge_count: item.edge_count ?? 0,
      last_modified: item.updated_at || null,
    };
    insertNode({
      kind: 'board',
      ref_id: item.id,
      x: x - PORTAL_DEFAULT_SIZE.width / 2,
      y: y - PORTAL_DEFAULT_SIZE.height / 2,
      width: PORTAL_DEFAULT_SIZE.width,
      height: PORTAL_DEFAULT_SIZE.height,
    }, refSummary);
  }, [insertNode, viewportCenter, boardId]);

  const onAddGroup = useCallback(() => {
    const { x, y } = viewportCenter();
    insertNode({
      kind: 'group',
      title: 'Group',
      x: x - GROUP_DEFAULT_SIZE.width / 2,
      y: y - GROUP_DEFAULT_SIZE.height / 2,
      width: GROUP_DEFAULT_SIZE.width,
      height: GROUP_DEFAULT_SIZE.height,
      color: 'var(--brand-cobalt)',
    });
  }, [insertNode, viewportCenter]);

  // ─ Uploads: file → image/file node ───────────────────────
  const uploadAndInsert = useCallback(async (files, originX, originY) => {
    const list = Array.from(files || []);
    if (!list.length) return;
    let offset = 0;
    for (const file of list) {
      try {
        const meta = await uploadBoardAttachment(boardId, file);
        const isImage = (meta.mime || '').startsWith('image/');
        const size = isImage ? IMAGE_DEFAULT_SIZE : FILE_DEFAULT_SIZE;
        await insertNode({
          kind: isImage ? 'image' : 'file',
          x: originX + offset,
          y: originY + offset,
          width: size.width,
          height: size.height,
          title: meta.original_name || '',
          media_filename: meta.filename,
          media_mime: meta.mime,
          media_size: meta.size,
          media_alt: isImage ? (meta.original_name || '') : '',
        });
        offset += 24;
      } catch (err) {
        // best-effort; skip failed files
      }
    }
  }, [boardId, insertNode]);

  const onToolbarUpload = useCallback((files) => {
    const { x, y } = viewportCenter();
    uploadAndInsert(files, x, y);
  }, [uploadAndInsert, viewportCenter]);

  const onCanvasPaste = useCallback((e) => {
    if (isEditableFocused()) return;
    const items = e.clipboardData?.items;
    if (!items) return;
    const files = [];
    for (const it of items) {
      if (it.kind === 'file') {
        const f = it.getAsFile();
        if (f) files.push(f);
      }
    }
    if (!files.length) return;
    e.preventDefault();
    const { x, y } = viewportCenter();
    uploadAndInsert(files, x, y);
  }, [uploadAndInsert, viewportCenter]);

  useEffect(() => {
    const handler = (e) => onCanvasPaste(e);
    window.addEventListener('paste', handler);
    return () => window.removeEventListener('paste', handler);
  }, [onCanvasPaste]);

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
    const has = Array.from(types).some((t) => t === DND_TYPE || t === 'text/plain' || t === 'Files');
    if (!has) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  const onCanvasDrop = useCallback((e) => {
    // OS file drop: upload each file.
    const files = e.dataTransfer?.files;
    if (files && files.length) {
      e.preventDefault();
      const pos = projectClient(e.clientX, e.clientY);
      uploadAndInsert(files, pos.x, pos.y);
      return;
    }
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
    } else if (payload.kind === 'group') {
      insertNode({
        kind: 'group',
        title: payload.item?.title || 'Group',
        x: pos.x - GROUP_DEFAULT_SIZE.width / 2,
        y: pos.y - GROUP_DEFAULT_SIZE.height / 2,
        width: GROUP_DEFAULT_SIZE.width,
        height: GROUP_DEFAULT_SIZE.height,
        color: 'var(--brand-cobalt)',
      });
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
    } else if (payload.kind === 'board' && payload.item?.id) {
      if (payload.item.id === boardId) {
        // Client-side cycle protection: a board cannot portal to itself.
        return;
      }
      const refSummary = {
        id: payload.item.id,
        name: payload.item.name || 'Untitled board',
        icon: payload.item.icon || '🗂️',
        color: payload.item.color || '',
        node_count: payload.item.node_count ?? 0,
        edge_count: payload.item.edge_count ?? 0,
        last_modified: payload.item.updated_at || null,
      };
      insertNode({
        kind: 'board',
        ref_id: payload.item.id,
        x: pos.x - PORTAL_DEFAULT_SIZE.width / 2,
        y: pos.y - PORTAL_DEFAULT_SIZE.height / 2,
        width: PORTAL_DEFAULT_SIZE.width,
        height: PORTAL_DEFAULT_SIZE.height,
      }, refSummary);
    }
  }, [insertNode, projectClient, uploadAndInsert, boardId]);

  // ─ Keyboard: guard Delete/Backspace when focused in input ─
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

  // ─ Quick capture: `t` opens template picker, `c` drops a blank card ─
  const insertFromTemplate = useCallback((tpl, flowPos = null) => {
    const pos = flowPos || viewportCenter();
    return insertNode({
      kind: 'card',
      x: pos.x - 120,
      y: pos.y - 60,
      width: tpl.width || null,
      height: tpl.height || null,
      title: tpl.title || tpl.name || 'New card',
      body: tpl.body_md || '',
      color: tpl.color || null,
    });
  }, [insertNode, viewportCenter]);

  useEffect(() => {
    const onMove = (e) => {
      cursorRef.current = { clientX: e.clientX, clientY: e.clientY };
    };
    const el = wrapperRef.current;
    if (!el) return undefined;
    el.addEventListener('mousemove', onMove);
    return () => el.removeEventListener('mousemove', onMove);
  }, []);

  useEffect(() => {
    const onShortcut = (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (isEditableFocused()) return;
      if (e.key !== 't' && e.key !== 'T' && e.key !== 'c' && e.key !== 'C') return;
      const el = wrapperRef.current;
      if (!el) return;
      const { clientX, clientY } = cursorRef.current;
      let flowPos = null;
      if (clientX != null && clientY != null) {
        const rect = el.getBoundingClientRect();
        if (clientX >= rect.left && clientX <= rect.right
            && clientY >= rect.top && clientY <= rect.bottom) {
          flowPos = projectClient(clientX, clientY);
        }
      }
      if (e.key === 't' || e.key === 'T') {
        e.preventDefault();
        const rect = el.getBoundingClientRect();
        const localX = (clientX ?? rect.left + 100) - rect.left;
        const localY = (clientY ?? rect.top + 100) - rect.top;
        setTemplatePicker({ x: localX, y: localY, flow: flowPos });
      } else if (e.key === 'c' || e.key === 'C') {
        e.preventDefault();
        const pos = flowPos || viewportCenter();
        insertNode({ kind: 'card', x: pos.x - 120, y: pos.y - 60, title: '', body: '' });
      }
    };
    window.addEventListener('keydown', onShortcut);
    return () => window.removeEventListener('keydown', onShortcut);
  }, [insertNode, projectClient, viewportCenter]);

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

  // ─ Group / Ungroup actions ───────────────────────────────
  const groupSelection = useCallback(async () => {
    const selected = nodes.filter((n) => n.selected && n.data?.kind !== 'group');
    if (selected.length < 1) return;
    const PADDING = 32;
    const HEADER = 36;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of selected) {
      const w = n.width || n.data?.width || 240;
      const h = n.height || n.data?.height || 160;
      minX = Math.min(minX, n.position.x);
      minY = Math.min(minY, n.position.y);
      maxX = Math.max(maxX, n.position.x + w);
      maxY = Math.max(maxY, n.position.y + h);
    }
    const x = minX - PADDING;
    const y = minY - PADDING - HEADER;
    const width = (maxX - minX) + PADDING * 2;
    const height = (maxY - minY) + PADDING * 2 + HEADER;
    const created = await insertNode({
      kind: 'group',
      title: 'Group',
      x, y, width, height,
      color: 'var(--brand-cobalt)',
    });
    if (!created) return;
    for (const n of selected) {
      handleNodeUpdate(n.id, { parent_group_id: Number(created.id) });
    }
  }, [nodes, insertNode, handleNodeUpdate]);

  const ungroup = useCallback(async (groupNode) => {
    const gid = Number(groupNode.id);
    const children = nodes.filter((n) => n.data?.parent_group_id === gid);
    for (const c of children) {
      handleNodeUpdate(c.id, { parent_group_id: null });
    }
    await handleNodeDelete(groupNode.id);
  }, [nodes, handleNodeUpdate, handleNodeDelete]);

  const removeFromGroup = useCallback(async (node) => {
    handleNodeUpdate(node.id, { parent_group_id: null });
  }, [handleNodeUpdate]);

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
        onAddBoard={onAddBoard}
        onAddGroup={onAddGroup}
        currentBoardId={boardId}
        onUploadFiles={onToolbarUpload}
        onDragStartNew={handleToolbarDragStart}
        onOpenTemplates={() => setTemplatePicker({ x: 80, y: 60, flow: null })}
      />
      <button
        className="board-backlinks-toggle"
        onClick={() => setBacklinksOpen((v) => !v)}
        title="Show boards and cards that link to this board"
      >
        <span>🔗</span>
        <span>Backlinks</span>
      </button>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeDragStart={onNodeDragStart}
        onNodeDrag={onNodeDrag}
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
              {ctxMenu.target.data?.kind === 'group' && (
                <button onClick={() => { ungroup(ctxMenu.target); closeCtx(); }}>
                  Ungroup
                </button>
              )}
              {ctxMenu.target.data?.kind !== 'group'
                && nodes.filter((n) => n.selected && n.data?.kind !== 'group').length >= 1 && (
                <button onClick={() => { groupSelection(); closeCtx(); }}>
                  Group selection
                </button>
              )}
              {ctxMenu.target.data?.kind !== 'group' && ctxMenu.target.data?.parent_group_id != null && (
                <button onClick={() => { removeFromGroup(ctxMenu.target); closeCtx(); }}>
                  Remove from group
                </button>
              )}
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
      {backlinksOpen && (
        <BacklinksDrawer
          boardId={boardId}
          onJump={(e) => { setBacklinksOpen(false); onOpenEntity?.(e); }}
          onClose={() => setBacklinksOpen(false)}
        />
      )}
      <TemplatePicker
        open={!!templatePicker}
        anchor={templatePicker}
        onPick={(tpl) => insertFromTemplate(tpl, templatePicker?.flow)}
        onClose={() => setTemplatePicker(null)}
      />
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
