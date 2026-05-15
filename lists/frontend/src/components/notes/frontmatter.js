// Minimal YAML frontmatter parser — handles the subset Obsidian users
// actually write: scalars, simple flow lists, and block lists. No anchors,
// no flow maps, no multi-line strings. Returns { props, body } where
// `body` is the note body with the frontmatter block stripped, or
// `{ props: null, body: original }` if no frontmatter block is present.

const FENCE = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/;

function parseScalar(raw) {
  const v = raw.trim();
  if (v === '') return '';
  if (v === 'true') return true;
  if (v === 'false') return false;
  if (v === 'null' || v === '~') return null;
  if (/^-?\d+$/.test(v)) return Number(v);
  if (/^-?\d+\.\d+$/.test(v)) return Number(v);
  if (
    (v.startsWith('"') && v.endsWith('"')) ||
    (v.startsWith("'") && v.endsWith("'"))
  ) return v.slice(1, -1);
  return v;
}

function parseFlowList(raw) {
  const inner = raw.trim().slice(1, -1).trim();
  if (!inner) return [];
  return inner.split(',').map((s) => parseScalar(s));
}

export function parseFrontmatter(body) {
  if (typeof body !== 'string') return { props: null, body: '' };
  const match = body.match(FENCE);
  if (!match) return { props: null, body };
  const yaml = match[1];
  const rest = body.slice(match[0].length);
  const props = {};
  const lines = yaml.split(/\r?\n/);
  let currentKey = null;
  for (const line of lines) {
    if (!line.trim() || line.trim().startsWith('#')) continue;
    const blockItem = line.match(/^\s+-\s+(.*)$/);
    if (blockItem && currentKey) {
      if (!Array.isArray(props[currentKey])) props[currentKey] = [];
      props[currentKey].push(parseScalar(blockItem[1]));
      continue;
    }
    const kv = line.match(/^([A-Za-z0-9_.\-]+):\s*(.*)$/);
    if (!kv) continue;
    const key = kv[1];
    const rawVal = kv[2];
    if (rawVal === '') {
      // Could be a block list starting; mark and continue.
      props[key] = [];
      currentKey = key;
      continue;
    }
    currentKey = key;
    if (rawVal.startsWith('[') && rawVal.endsWith(']')) {
      props[key] = parseFlowList(rawVal);
    } else {
      props[key] = parseScalar(rawVal);
    }
  }
  return { props, body: rest };
}
