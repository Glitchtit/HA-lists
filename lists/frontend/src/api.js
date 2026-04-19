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
