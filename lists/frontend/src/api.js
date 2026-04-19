import axios from 'axios';

function getIngressPath() {
  const meta = document.querySelector('meta[name="ingress-path"]')?.content;
  if (meta) return meta;
  const match = window.location.pathname.match(/^(\/api\/hassio_ingress\/[^/]+)/);
  return match ? match[1] : '';
}

const INGRESS_PATH = getIngressPath();
const api = axios.create({ baseURL: `${INGRESS_PATH}/api` });

export const getHealth = () => api.get('/health').then(r => r.data);

export const getFolders = (includeArchived = false) =>
  api.get('/folders/', { params: { include_archived: includeArchived } }).then(r => r.data);
export const createFolder = (data) => api.post('/folders/', data).then(r => r.data);
export const updateFolder = (id, data) => api.patch(`/folders/${id}`, data).then(r => r.data);
export const deleteFolder = (id) => api.delete(`/folders/${id}`);

export const getLists = (params = {}) =>
  api.get('/lists/', { params }).then(r => r.data);
export const createList = (data) => api.post('/lists/', data).then(r => r.data);
export const updateList = (id, data) => api.patch(`/lists/${id}`, data).then(r => r.data);
export const deleteList = (id) => api.delete(`/lists/${id}`);

export const getItems = (params = {}) =>
  api.get('/items/', { params }).then(r => r.data);
export const getItem = (id) => api.get(`/items/${id}`).then(r => r.data);
export const createItem = (data) => api.post('/items/', data).then(r => r.data);
export const updateItem = (id, data) => api.patch(`/items/${id}`, data).then(r => r.data);
export const deleteItem = (id) => api.delete(`/items/${id}`);
export const completeItem = (id, completedBy) =>
  api.post(`/items/${id}/complete`, null, { params: completedBy ? { completed_by: completedBy } : {} }).then(r => r.data);
export const reopenItem = (id) => api.post(`/items/${id}/reopen`).then(r => r.data);
export const attachTag = (itemId, name) => api.post(`/items/${itemId}/tags/${name}`).then(r => r.data);
export const detachTag = (itemId, name) => api.delete(`/items/${itemId}/tags/${name}`).then(r => r.data);

export const getSubtasks = (itemId) =>
  api.get('/subtasks/', { params: { item_id: itemId } }).then(r => r.data);
export const createSubtask = (data) => api.post('/subtasks/', data).then(r => r.data);
export const updateSubtask = (id, data) => api.patch(`/subtasks/${id}`, data).then(r => r.data);
export const deleteSubtask = (id) => api.delete(`/subtasks/${id}`);
export const toggleSubtask = (id) => api.post(`/subtasks/${id}/toggle`).then(r => r.data);

export const getTags = () => api.get('/tags/').then(r => r.data);
export const createTag = (data) => api.post('/tags/', data).then(r => r.data);
export const updateTag = (id, data) => api.patch(`/tags/${id}`, data).then(r => r.data);
export const deleteTag = (id) => api.delete(`/tags/${id}`);

export const duplicateFolder = (id) => api.post(`/folders/${id}/duplicate`).then(r => r.data);
export const duplicateList = (id, body) => api.post(`/lists/${id}/duplicate`, body || null).then(r => r.data);
export const duplicateItem = (id, body) => api.post(`/items/${id}/duplicate`, body || null).then(r => r.data);

export const getPersons = (includeInactive = false) =>
  api.get('/persons/', { params: { include_inactive: includeInactive } }).then(r => r.data);
export const getMe = () => api.get('/persons/me').then(r => r.data);
export const syncPersons = () => api.post('/persons/sync').then(r => r.data);

// ── AI (Goblin Tools) ───────────────────────────────────────────────────────
export const aiBreakdown = (itemId, spiciness) =>
  api.post('/ai/breakdown', { item_id: itemId, spiciness }).then(r => r.data);
export const aiEstimate = (itemId) =>
  api.post('/ai/estimate', { item_id: itemId }).then(r => r.data);
export const aiCompile = (listId, brainDump) =>
  api.post('/ai/compile', { list_id: listId, brain_dump: brainDump }).then(r => r.data);
export const aiFormalize = (text, tone) =>
  api.post('/ai/formalize', { text, tone }).then(r => r.data);
export const getAiJob = (taskId) => api.get(`/ai/jobs/${taskId}`).then(r => r.data);

// ── Notes ──────────────────────────────────────────────────────────────────
export const getNotes = (params = {}) =>
  api.get('/notes/', { params }).then(r => r.data);
export const getNote = (id) => api.get(`/notes/${id}`).then(r => r.data);
export const createNote = (data) => api.post('/notes/', data).then(r => r.data);
export const updateNote = (id, data) => api.patch(`/notes/${id}`, data).then(r => r.data);
export const deleteNote = (id) => api.delete(`/notes/${id}`);
export const duplicateNote = (id) => api.post(`/notes/${id}/duplicate`).then(r => r.data);
export const getBacklinks = (id) => api.get(`/notes/${id}/backlinks`).then(r => r.data);
export const resolveNote = (title) =>
  api.get('/notes/resolve', { params: { title } }).then(r => r.data).catch(e => {
    if (e.response?.status === 404) return null;
    throw e;
  });

// ── AI note actions ────────────────────────────────────────────────────────
export const aiNoteSummarize    = (noteId) =>
  api.post('/ai/notes/summarize', { note_id: noteId }).then(r => r.data);
export const aiNoteContinue     = (noteId, prompt = '') =>
  api.post('/ai/notes/continue', { note_id: noteId, prompt }).then(r => r.data);
export const aiNoteRewrite      = (noteId, tone) =>
  api.post('/ai/notes/rewrite', { note_id: noteId, tone }).then(r => r.data);
export const aiNoteExtractTasks = (noteId, targetListId) =>
  api.post('/ai/notes/extract-tasks', { note_id: noteId, target_list_id: targetListId }).then(r => r.data);
export const aiNoteOutline      = (noteId) =>
  api.post('/ai/notes/outline', { note_id: noteId }).then(r => r.data);

// ── Boards ─────────────────────────────────────────────────────────────────
export const listBoards = (params = {}) =>
  api.get('/boards/', { params }).then(r => r.data);
export const getBoard = (id) => api.get(`/boards/${id}`).then(r => r.data);
export const createBoard = (payload) => api.post('/boards/', payload).then(r => r.data);
export const updateBoard = (id, patch) => api.patch(`/boards/${id}`, patch).then(r => r.data);
export const deleteBoard = (id) => api.delete(`/boards/${id}`);
export const duplicateBoard = (id) => api.post(`/boards/${id}/duplicate`).then(r => r.data);
export const updateBoardViewport = (id, viewport) =>
  api.patch(`/boards/${id}/viewport`, viewport).then(r => r.data);

// ── Board nodes ────────────────────────────────────────────────────────────
export const createBoardNode = (boardId, payload) =>
  api.post(`/boards/${boardId}/nodes`, payload).then(r => r.data);
export const updateBoardNode = (boardId, nodeId, patch) =>
  api.patch(`/boards/${boardId}/nodes/${nodeId}`, patch).then(r => r.data);
export const deleteBoardNode = (boardId, nodeId) =>
  api.delete(`/boards/${boardId}/nodes/${nodeId}`);
export const bulkUpdateBoardNodePositions = (boardId, positions) =>
  api.post(`/boards/${boardId}/nodes/bulk-positions`, { positions }).then(r => r.data);
export const translateBoardGroup = (boardId, groupId, dx, dy) =>
  api.post(`/boards/${boardId}/nodes/${groupId}/translate`, { dx, dy }).then(r => r.data);

// ── Board edges ────────────────────────────────────────────────────────────
export const createBoardEdge = (boardId, payload) =>
  api.post(`/boards/${boardId}/edges`, payload).then(r => r.data);
export const updateBoardEdge = (boardId, edgeId, patch) =>
  api.patch(`/boards/${boardId}/edges/${edgeId}`, patch).then(r => r.data);
export const deleteBoardEdge = (boardId, edgeId) =>
  api.delete(`/boards/${boardId}/edges/${edgeId}`);

// ── Board attachments ──────────────────────────────────────────────────────
export const uploadBoardAttachment = (boardId, file) => {
  const form = new FormData();
  form.append('file', file, file.name || 'upload.bin');
  return api.post(`/boards/${boardId}/attachments`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
};
export const attachmentUrl = (boardId, filename) =>
  `${INGRESS_PATH}/api/boards/${boardId}/attachments/${encodeURIComponent(filename)}`;
