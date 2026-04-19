import { useEffect, useRef, useState } from 'react';

let _mermaidPromise = null;
function loadMermaid() {
  if (!_mermaidPromise) {
    _mermaidPromise = import('mermaid').then((m) => {
      const mermaid = m.default;
      mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'strict' });
      return mermaid;
    });
  }
  return _mermaidPromise;
}

let _uid = 0;
function nextId() {
  _uid += 1;
  return `mmd-${Date.now().toString(36)}-${_uid}`;
}

export default function MermaidBlock({ code }) {
  const ref = useRef(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setErr(null);
    loadMermaid()
      .then((mermaid) => mermaid.render(nextId(), code))
      .then(({ svg }) => {
        if (cancelled || !ref.current) return;
        ref.current.innerHTML = svg;
      })
      .catch((e) => {
        if (cancelled) return;
        setErr(e?.message || String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [code]);

  if (err) {
    return (
      <div className="my-3 rounded-lg border border-line-1 bg-surface-2 p-3">
        <div className="text-xs text-semantic-danger mb-1">Mermaid error: {err}</div>
        <pre className="text-xs text-ink-3 whitespace-pre-wrap">{code}</pre>
      </div>
    );
  }

  return <div ref={ref} className="mermaid-block my-3 overflow-x-auto" />;
}
