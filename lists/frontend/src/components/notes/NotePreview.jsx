import { useEffect, useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkBreaks from 'remark-breaks';
import rehypeKatex from 'rehype-katex';
import rehypeHighlight from 'rehype-highlight';
import 'katex/dist/katex.min.css';
import 'highlight.js/styles/github-dark-dimmed.css';

import remarkWikilink from './remarkWikilink';
import remarkEmbed from './remarkEmbed';
import remarkCallout from './remarkCallout';
import MermaidBlock from './MermaidBlock';
import PropertiesPanel from './PropertiesPanel';
import Wikilink from './Wikilink';
import { parseFrontmatter } from './frontmatter';

function slugify(text) {
  return String(text || '')
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');
}

function flattenText(children) {
  if (!children) return '';
  if (typeof children === 'string') return children;
  if (Array.isArray(children)) return children.map(flattenText).join('');
  if (children.props && children.props.children) return flattenText(children.props.children);
  return '';
}

function extractSection(body, anchor) {
  if (!anchor) return body;
  const lines = String(body || '').split('\n');
  const slug = (s) => String(s || '')
    .toLowerCase().trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');
  const targetSlug = slug(anchor);
  let startLine = -1;
  let startLevel = 0;
  for (let i = 0; i < lines.length; i++) {
    const m = /^(#{1,6})\s+(.+?)\s*#*\s*$/.exec(lines[i]);
    if (m && slug(m[2]) === targetSlug) {
      startLine = i;
      startLevel = m[1].length;
      break;
    }
  }
  if (startLine === -1) return null;
  let endLine = lines.length;
  for (let i = startLine + 1; i < lines.length; i++) {
    const m = /^(#{1,6})\s+/.exec(lines[i]);
    if (m && m[1].length <= startLevel) { endLine = i; break; }
  }
  return lines.slice(startLine, endLine).join('\n');
}

function Embed({ title, anchor, onEmbedResolve, onWikilinkClick, onToggleChecklist, visitedEmbeds }) {
  const [state, setState] = useState({ loading: true, note: null });
  useEffect(() => {
    let cancelled = false;
    if (!onEmbedResolve) {
      setState({ loading: false, note: null });
      return;
    }
    setState({ loading: true, note: null });
    Promise.resolve(onEmbedResolve(title))
      .then((note) => !cancelled && setState({ loading: false, note }))
      .catch(() => !cancelled && setState({ loading: false, note: null }));
    return () => { cancelled = true; };
  }, [title, onEmbedResolve]);

  if (state.loading) {
    return (
      <div className="note-embed note-embed-loading my-2 rounded-lg border border-line-1 bg-surface-2 px-3 py-2 text-xs text-ink-3">
        Loading embed: {title}{anchor ? `#${anchor}` : ''}…
      </div>
    );
  }
  if (!state.note) {
    return (
      <div className="note-embed note-embed-missing my-2 rounded-lg border border-dashed border-semantic-warning bg-surface-2 px-3 py-2 text-xs text-ink-3">
        Embedded note not found: <span className="font-mono">{title}{anchor ? `#${anchor}` : ''}</span>
      </div>
    );
  }
  let sectionBody = state.note.body || '';
  let sectionMissing = false;
  if (anchor) {
    const sec = extractSection(sectionBody, anchor);
    if (sec === null) sectionMissing = true;
    else sectionBody = sec;
  }
  if (sectionMissing) {
    return (
      <div className="note-embed note-embed-missing my-2 rounded-lg border border-dashed border-semantic-warning bg-surface-2 px-3 py-2 text-xs text-ink-3">
        Heading not found in <span className="font-mono">{title}</span>: <span className="font-mono">#{anchor}</span>
      </div>
    );
  }
  const nextVisited = new Set(visitedEmbeds || []);
  if (state.note.id != null) {
    if (nextVisited.has(state.note.id)) {
      return (
        <div className="note-embed note-embed-cycle my-2 rounded-lg border border-semantic-warning bg-surface-2 px-3 py-2 text-xs text-semantic-warning">
          ↺ Embed cycle detected for <span className="font-mono">{title}</span>
        </div>
      );
    }
    nextVisited.add(state.note.id);
  }
  return (
    <div className="note-embed my-2 rounded-lg border-l-2 border-brand-cobalt-400 bg-surface-2 px-3 py-2">
      {state.note.title && (
        <div className="note-embed-title mb-1 text-xs font-semibold text-ink-3">
          ↪ {state.note.title}{anchor ? ` # ${anchor}` : ''}
        </div>
      )}
      <NotePreview
        body={sectionBody}
        onWikilinkClick={onWikilinkClick}
        onEmbedResolve={onEmbedResolve}
        onToggleChecklist={onToggleChecklist}
        visitedEmbeds={nextVisited}
        isEmbed
      />
    </div>
  );
}

export default function NotePreview({
  body,
  onWikilinkClick,
  onWikilinkOpenInBackground,
  onEmbedResolve,
  onToggleChecklist,
  onBodyChange,
  visitedEmbeds,
  isEmbed = false,
  simplified = false,
  lightBg = false,
}) {
  const remarkPlugins = useMemo(
    () => [remarkGfm, remarkBreaks, remarkMath, remarkEmbed, remarkWikilink, remarkCallout],
    [],
  );
  const rehypePlugins = useMemo(() => [rehypeKatex, rehypeHighlight], []);

  const components = useMemo(() => ({
    a({ node, href, children, ...props }) {
      const wl = props['data-wikilink'] || node?.properties?.['dataWikilink'];
      const anchor = props['data-wikilink-anchor'] || node?.properties?.['dataWikilinkAnchor'] || '';
      if (wl) {
        return (
          <Wikilink
            title={wl}
            anchor={anchor}
            onClick={onWikilinkClick}
            onOpenInBackground={onWikilinkOpenInBackground}
            onResolve={onEmbedResolve}
          >
            {children}
          </Wikilink>
        );
      }
      return (
        <a href={href} target="_blank" rel="noreferrer noopener" {...props}>
          {children}
        </a>
      );
    },
    code({ node, inline, className, children, ...props }) {
      const lang = /language-(\w+)/.exec(className || '');
      const text = String(children).replace(/\n$/, '');
      if (!inline && lang && lang[1] === 'mermaid') {
        if (simplified) {
          return <span className="text-xs text-ink-3 italic">📊 Diagram</span>;
        }
        return <MermaidBlock code={text} />;
      }
      if (inline) {
        return <code className={className} {...props}>{children}</code>;
      }
      return (
        <code className={className} {...props}>{children}</code>
      );
    },
    input({ node, ...props }) {
      if (props.type !== 'checkbox') return <input {...props} />;
      const { checked, ...inputProps } = props;
      const offset = node?.position?.start?.offset;
      return (
        <input
          {...inputProps}
          disabled={false}
          readOnly={false}
          onChange={(e) => {
            if (onToggleChecklist && typeof offset === 'number') {
              onToggleChecklist(offset);
            }
          }}
        />
      );
    },
    div({ node, className, children, ...props }) {
      const embedTitle = props['data-embed'];
      const embedAnchor = props['data-embed-anchor'] || node?.properties?.['dataEmbedAnchor'] || '';
      if (embedTitle) {
        return (
          <Embed
            title={embedTitle}
            anchor={embedAnchor}
            onEmbedResolve={onEmbedResolve}
            onWikilinkClick={onWikilinkClick}
            onToggleChecklist={onToggleChecklist}
            visitedEmbeds={visitedEmbeds}
          />
        );
      }
      return (
        <div className={className} {...props}>
          {children}
        </div>
      );
    },
    h1: makeHeading('h1'),
    h2: makeHeading('h2'),
    h3: makeHeading('h3'),
    h4: makeHeading('h4'),
    h5: makeHeading('h5'),
    h6: makeHeading('h6'),
  }), [onWikilinkClick, onWikilinkOpenInBackground, onEmbedResolve, onToggleChecklist, visitedEmbeds]);

  const { props, body: cleanBody } = useMemo(() => parseFrontmatter(body || ''), [body]);

  return (
    <div className={`note-preview ${lightBg ? 'prose-neutral' : 'prose prose-invert'} max-w-none text-ink-1 ${isEmbed ? 'note-preview-embed' : ''}`}>
      {!isEmbed && (
        <PropertiesPanel
          props={props}
          body={body || ''}
          onBodyChange={onBodyChange}
        />
      )}
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={rehypePlugins}
        components={components}
      >
        {cleanBody}
      </ReactMarkdown>
    </div>
  );
}

function makeHeading(Tag) {
  return function Heading({ node, children, ...props }) {
    const text = flattenText(children);
    const id = slugify(text);
    return (
      <Tag id={id} data-heading-slug={id} {...props}>
        {children}
      </Tag>
    );
  };
}
