import { visit } from 'unist-util-visit';

const EMBED_RE = /!\[\[([^\]|]+?)(?:\|([^\]]+))?\]\]/g;

// Converts `![[Title]]` in text nodes into a custom mdast node whose
// data.hName = 'div' and data.hProperties carry `data-embed`/`className`,
// so mdast-util-to-hast (used by react-markdown) renders it as:
//   <div class="note-embed" data-embed="Title"></div>
// The NotePreview `components.div` renderer then recursively resolves it.
export default function remarkEmbed() {
  return (tree) => {
    visit(tree, 'text', (node, index, parent) => {
      if (!parent || index == null) return;
      if (parent.type === 'code' || parent.type === 'inlineCode' || parent.type === 'link') return;
      const value = node.value;
      if (!value || value.indexOf('![[') === -1) return;

      const out = [];
      let last = 0;
      let m;
      EMBED_RE.lastIndex = 0;
      while ((m = EMBED_RE.exec(value)) !== null) {
        if (m.index > last) {
          out.push({ type: 'text', value: value.slice(last, m.index) });
        }
        const target = m[1].trim();
        out.push({
          type: 'noteEmbed',
          data: {
            hName: 'div',
            hProperties: { className: 'note-embed', 'data-embed': target },
            hChildren: [],
          },
          children: [],
        });
        last = m.index + m[0].length;
      }
      if (!out.length) return;
      if (last < value.length) out.push({ type: 'text', value: value.slice(last) });
      parent.children.splice(index, 1, ...out);
      return index + out.length;
    });
  };
}
