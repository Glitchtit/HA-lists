import { useEffect, useRef, useState } from 'react'

/**
 * Toggles a label between display and inline <input>. Commits on Enter or
 * blur (unless empty or unchanged). Cancels on Escape.
 *
 * Props: value, editing, onCommit(newValue), onCancel, className?, inputClassName?
 */
export default function InlineEditLabel({
  value,
  editing,
  onCommit,
  onCancel,
  className,
  inputClassName,
  placeholder,
}) {
  const [draft, setDraft] = useState(value)
  const ref = useRef(null)

  useEffect(() => {
    if (editing) {
      setDraft(value)
      requestAnimationFrame(() => {
        ref.current?.focus()
        ref.current?.select()
      })
    }
  }, [editing, value])

  if (!editing) {
    return <span className={className}>{value}</span>
  }

  function commit() {
    const next = draft.trim()
    if (!next || next === value) { onCancel?.(); return }
    onCommit?.(next)
  }

  return (
    <input
      ref={ref}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') { e.preventDefault(); commit() }
        if (e.key === 'Escape') { e.preventDefault(); onCancel?.() }
      }}
      onClick={(e) => e.stopPropagation()}
      placeholder={placeholder}
      className={inputClassName || 'px-1 py-0 bg-surface-3 border border-brand-cobalt rounded outline-none text-sm'}
    />
  )
}
