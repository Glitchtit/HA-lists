import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

/**
 * PC-style context menu rendered via portal.
 *
 * Props:
 *   open, x, y, onClose, items, onLeave?
 * Items: { label, icon?, onClick?, danger?, disabled?, separator?, children?, hint? }
 *   - separator: { separator: true }
 *   - children: nested item array → rendered as a submenu (hover or ▸ click)
 *
 * Only one submenu is open at a time per menu level: hovering any row sets this
 * menu's `openIndex`, so moving to a sibling closes the previous submenu instead
 * of leaving it stranded behind the new one.
 */
export default function ContextMenu({ open, x, y, items, onClose, onLeave, _depth = 0 }) {
  const ref = useRef(null)
  const [pos, setPos] = useState({ x, y })
  const [openIndex, setOpenIndex] = useState(null)

  useLayoutEffect(() => {
    if (!open || !ref.current) return
    const rect = ref.current.getBoundingClientRect()
    let nx = x
    let ny = y
    if (nx + rect.width > window.innerWidth - 4) nx = Math.max(4, window.innerWidth - rect.width - 4)
    if (ny + rect.height > window.innerHeight - 4) ny = Math.max(4, window.innerHeight - rect.height - 4)
    setPos({ x: nx, y: ny })
  }, [open, x, y, items])

  // Drop any open submenu whenever this menu closes/reopens.
  useEffect(() => { if (!open) setOpenIndex(null) }, [open])

  useEffect(() => {
    if (!open) return
    const onDocDown = (e) => {
      // Allow clicks anywhere inside any context menu (including portaled submenus)
      if (e.target.closest?.('[data-ctx-menu]')) return
      onClose()
    }
    const onKey = (e) => {
      if (e.key === 'Escape') { e.stopPropagation(); onClose() }
    }
    document.addEventListener('mousedown', onDocDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div
      ref={ref}
      data-ctx-menu="true"
      role="menu"
      className="fixed z-[100] min-w-[200px] py-1 rounded-md bg-surface-3 border border-line-1 shadow-xl animate-slide-up text-sm"
      style={{ left: pos.x, top: pos.y }}
      onContextMenu={(e) => e.preventDefault()}
      onMouseLeave={(e) => {
        // Leaving to a non-context-menu target (e.g. dragging away): collapse any
        // open submenu and notify our parent so it can hide us. Moving into our
        // own submenu keeps relatedTarget inside a [data-ctx-menu], so we skip.
        if (!e.relatedTarget?.closest?.('[data-ctx-menu]')) {
          setOpenIndex(null)
          onLeave?.()
        }
      }}
    >
      {items.map((it, i) => (
        <MenuItem
          key={i}
          item={it}
          index={i}
          isOpen={openIndex === i}
          onHover={setOpenIndex}
          onClose={onClose}
          _depth={_depth}
        />
      ))}
    </div>,
    document.body,
  )
}

function MenuItem({ item, index, isOpen, onHover, onClose, _depth = 0 }) {
  const rowRef = useRef(null)
  const [subPos, setSubPos] = useState({ x: 0, y: 0 })

  if (item.separator) {
    return <div className="my-1 border-t border-line-1" role="separator" />
  }

  const hasChildren = Array.isArray(item.children) && item.children.length > 0

  function click(e) {
    if (item.disabled || hasChildren) return
    e.stopPropagation()
    onClose()
    item.onClick?.()
  }

  function enter() {
    if (hasChildren && !item.disabled) {
      const rect = rowRef.current?.getBoundingClientRect()
      if (rect) setSubPos({ x: rect.right - 2, y: rect.top })
      onHover(index)
    } else {
      // Hovering a leaf (or disabled) row closes any sibling submenu.
      onHover(null)
    }
  }

  return (
    <div
      ref={rowRef}
      role="menuitem"
      aria-disabled={item.disabled || undefined}
      aria-haspopup={hasChildren || undefined}
      aria-expanded={hasChildren ? isOpen : undefined}
      onMouseEnter={enter}
      onClick={click}
      className={[
        'relative flex items-center gap-2 px-3 py-1.5 cursor-pointer select-none',
        item.disabled ? 'opacity-40 cursor-not-allowed' : 'hover:bg-surface-4',
        item.danger ? 'text-semantic-danger' : 'text-ink-1',
      ].join(' ')}
    >
      <span className="w-4 text-center text-ink-3">{item.icon || ''}</span>
      <span className="flex-1 truncate">{item.label}</span>
      {item.hint && <span className="text-xs text-ink-4 ml-2">{item.hint}</span>}
      {hasChildren && <span className="text-ink-4 ml-1">▸</span>}
      {hasChildren && isOpen && (
        <ContextMenu
          open
          x={subPos.x}
          y={subPos.y}
          items={item.children}
          onClose={onClose}
          onLeave={() => onHover(null)}
          _depth={_depth + 1}
        />
      )}
    </div>
  )
}
