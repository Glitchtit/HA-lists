import { visit } from 'unist-util-visit';

const WIKI_RE = /\[\[([^\]|]+?)(?:\|([^\]]+))?\]\]/g;

export default function remarkWikilink() {
  return (tree) => {
    visit(tree, 'text', (node, index, parent) => {
      if (!parent || index == null) return;
      if (parent.type === 'code' || parent.type === 'inlineCode' || parent.type === 'link') return;
      const value = node.value;
      if (!value || value.indexOf('[[') === -1) return;

      const out = [];
      let last = 0;
      let m;
      WIKI_RE.lastIndex = 0;
      while ((m = WIKI_RE.exec(value)) !== null) {
        // skip when preceded by '!' (embed, handled by remarkEmbed)
        if (m.index > 0 && value[m.index - 1] === '!') continue;
        if (m.index > last) {
          out.push({ type: 'text', value: value.slice(last, m.index) });
        }
        const target = m[1].trim();
        const alias = (m[2] || m[1]).trim();
        out.push({
          type: 'link',
          url: '#wikilink',
          title: null,
          data: { hProperties: { 'data-wikilink': target, className: 'wikilink' } },
          children: [{ type: 'text', value: alias }],
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
