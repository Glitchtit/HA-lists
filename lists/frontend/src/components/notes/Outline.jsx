import { useMemo } from 'react';

function slugify(text) {
  return String(text || '')
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');
}

function parseHeadings(body) {
  const lines = (body || '').split('\n');
  const out = [];
  let inFence = false;
  for (const raw of lines) {
    const line = raw;
    if (/^```/.test(line.trimStart())) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    const m = /^(#{1,6})\s+(.+?)\s*#*\s*$/.exec(line);
    if (!m) continue;
    const level = m[1].length;
    const text = m[2].trim();
    out.push({ level, text, id: slugify(text) });
  }
  return out;
}

export default function Outline({ body }) {
  const headings = useMemo(() => parseHeadings(body), [body]);

  const handleClick = (id) => (e) => {
    e.preventDefault();
    // Find the heading inside the nearest `.note-preview` on the page.
    const preview = document.querySelector('.note-preview');
    const target = preview?.querySelector(`[data-heading-slug="${CSS.escape(id)}"]`);
    if (target && target.scrollIntoView) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="flex h-full flex-col border-l border-line-1 bg-surface-1">
      <div className="border-b border-line-1 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-ink-3">
        Outline
      </div>
      <div className="flex-1 overflow-auto p-2">
        {headings.length === 0 ? (
          <div className="text-xs text-ink-3">No headings</div>
        ) : (
          <ul className="space-y-0.5">
            {headings.map((h, i) => (
              <li key={`${h.id}-${i}`} style={{ paddingLeft: `${(h.level - 1) * 12}px` }}>
                <a
                  href={`#${h.id}`}
                  onClick={handleClick(h.id)}
                  className="block truncate rounded px-1.5 py-0.5 text-xs text-ink-2 hover:bg-surface-2 hover:text-ink-1"
                >
                  {h.text}
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
