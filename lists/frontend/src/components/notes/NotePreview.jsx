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

function Embed({ title, onEmbedResolve, onWikilinkClick, onToggleChecklist, visitedEmbeds }) {
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
        Loading embed: {title}…
      </div>
    );
  }
  if (!state.note) {
    return (
      <div className="note-embed note-embed-missing my-2 rounded-lg border border-dashed border-semantic-warning bg-surface-2 px-3 py-2 text-xs text-ink-3">
        Embedded note not found: <span className="font-mono">{title}</span>
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
          ↪ {state.note.title}
        </div>
      )}
      <NotePreview
        body={state.note.body || ''}
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
  onEmbedResolve,
  onToggleChecklist,
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
      if (wl) {
        return (
          <span
            className="wikilink"
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onWikilinkClick && onWikilinkClick(wl);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onWikilinkClick && onWikilinkClick(wl);
              }
            }}
          >
            {children}
          </span>
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
      if (embedTitle) {
        return (
          <Embed
            title={embedTitle}
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
  }), [onWikilinkClick, onEmbedResolve, onToggleChecklist, visitedEmbeds]);

  return (
    <div className={`note-preview prose ${lightBg ? '' : 'prose-invert'} max-w-none text-ink-1 ${isEmbed ? 'note-preview-embed' : ''}`}>
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={rehypePlugins}
        components={components}
      >
        {body || ''}
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
