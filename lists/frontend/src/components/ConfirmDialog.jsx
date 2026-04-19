import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

/**
 * Focus-trapped confirm dialog.
 *
 * Props: open, title, message, confirmLabel?, cancelLabel?, danger?, onConfirm, onCancel
 */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  danger = false,
  onConfirm,
  onCancel,
}) {
  const confirmRef = useRef(null)
  const cancelRef = useRef(null)

  useEffect(() => {
    if (!open) return
    // Default focus on the destructive button is rude; focus Cancel instead
    // so "Enter" needs deliberate arrow-over (or the user can tab).
    cancelRef.current?.focus()
    const onKey = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); onCancel?.() }
      if (e.key === 'Enter' && document.activeElement === confirmRef.current) {
        e.preventDefault(); onConfirm?.()
      }
      if (e.key === 'Tab') {
        // Simple two-button focus trap.
        e.preventDefault()
        const active = document.activeElement
        ;(active === cancelRef.current ? confirmRef : cancelRef).current?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onCancel, onConfirm])

  if (!open) return null

  return createPortal(
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onCancel?.() }}
    >
      <div className="w-[360px] max-w-[90vw] rounded-lg bg-surface-2 border border-line-1 shadow-2xl p-5 animate-slide-up">
        <h3 id="confirm-title" className="text-lg font-semibold font-display tracking-tight mb-2">
          {title}
        </h3>
        <p className="text-sm text-ink-2 mb-5 whitespace-pre-line">{message}</p>
        <div className="flex justify-end gap-2">
          <button
            ref={cancelRef}
            onClick={onCancel}
            className="px-3 py-1.5 text-sm rounded bg-surface-3 hover:bg-surface-4 text-ink-1"
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmRef}
            onClick={onConfirm}
            className={[
              'px-3 py-1.5 text-sm rounded font-medium',
              danger
                ? 'bg-semantic-danger/80 hover:bg-semantic-danger text-white'
                : 'bg-brand-cobalt hover:bg-brand-cobalt-400 text-white',
            ].join(' ')}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
