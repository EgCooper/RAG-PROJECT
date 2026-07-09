import { useEffect, useRef } from "react";
import { IconClose, IconTrash } from "./Icons";

export default function ConfirmDialog({
  open,
  title,
  message,
  detail,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  variant = "default",
  loading = false,
  onConfirm,
  onCancel,
}) {
  const confirmRef = useRef(null);

  useEffect(() => {
    if (!open) return;

    confirmRef.current?.focus();

    function onKeyDown(e) {
      if (e.key === "Escape" && !loading) onCancel();
    }

    document.addEventListener("keydown", onKeyDown);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = prev;
    };
  }, [open, loading, onCancel]);

  if (!open) return null;

  return (
    <div className="confirm-overlay" onClick={loading ? undefined : onCancel}>
      <div
        className={`confirm-dialog confirm-dialog--${variant}`}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-message"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="confirm-dialog-header">
          {variant === "danger" && (
            <div className="confirm-dialog-icon" aria-hidden>
              <IconTrash />
            </div>
          )}
          <div className="confirm-dialog-titles">
            <h2 id="confirm-title">{title}</h2>
            {detail && <p className="confirm-dialog-detail">{detail}</p>}
          </div>
          <button
            type="button"
            className="btn-icon confirm-dialog-close"
            onClick={onCancel}
            disabled={loading}
            aria-label="Cerrar"
          >
            <IconClose />
          </button>
        </div>

        <p id="confirm-message" className="confirm-dialog-message">
          {message}
        </p>

        <div className="confirm-dialog-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmRef}
            type="button"
            className={variant === "danger" ? "btn-danger" : "btn-primary"}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? "Eliminando…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
