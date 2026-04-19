const CALLOUT_TYPES = new Set([
  'note', 'info', 'tip', 'warning', 'danger', 'abstract',
  'quote', 'example', 'question', 'success', 'failure', 'bug',
]);

const MARKER_RE = /^\[!([a-zA-Z]+)\]\s*(.*)$/;

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// Parses GitHub-/Obsidian-style callouts from a blockquote whose first
// paragraph begins with `[!type] optional title`. Emits a div wrapper via
// `data.hName` overrides so react-markdown picks up the className/type.
export default function remarkCallout() {
  return (tree) => {
    if (!tree || !Array.isArray(tree.children)) return;
    walk(tree);
  };
}

function walk(parent) {
  if (!parent || !Array.isArray(parent.children)) return;
  for (let i = 0; i < parent.children.length; i++) {
    const node = parent.children[i];
    walk(node);
    if (node.type !== 'blockquote') continue;
    const first = node.children?.[0];
    if (!first || first.type !== 'paragraph') continue;
    const firstChild = first.children?.[0];
    if (!firstChild || firstChild.type !== 'text') continue;

    const line = firstChild.value.split('\n')[0];
    const m = MARKER_RE.exec(line);
    if (!m) continue;
    const type = m[1].toLowerCase();
    if (!CALLOUT_TYPES.has(type)) continue;
    const title = (m[2] || '').trim();

    // Strip the marker line from the first text node
    const rest = firstChild.value.slice(line.length).replace(/^\n/, '');
    if (rest) {
      firstChild.value = rest;
    } else {
      first.children.shift();
      if (first.children.length === 0) node.children.shift();
    }

    const titleNode = {
      type: 'calloutTitle',
      data: {
        hName: 'div',
        hProperties: { className: 'callout-title', 'data-callout-title': type },
      },
      children: [{ type: 'text', value: title || capitalize(type) }],
    };

    const bodyNode = {
      type: 'calloutBody',
      data: {
        hName: 'div',
        hProperties: { className: 'callout-body' },
      },
      children: node.children,
    };

    const wrapper = {
      type: 'callout',
      data: {
        hName: 'div',
        hProperties: { className: `callout callout-${type}`, 'data-callout': type },
      },
      children: [titleNode, bodyNode],
    };

    parent.children.splice(i, 1, wrapper);
  }
}
