import { IconClose, IconPlus } from "./Icons";

export default function Sidebar({ abierto, onCerrar, onNueva, deshabilitado }) {
  return (
    <>
      <div
        className={`sidebar-backdrop ${abierto ? "sidebar-backdrop--visible" : ""}`}
        onClick={onCerrar}
        aria-hidden={!abierto}
      />
      <aside className={`sidebar ${abierto ? "sidebar--open" : ""}`} aria-label="Panel lateral">
        <div className="sidebar-header">
          <div className="brand">
            <div className="brand-icon">ACH</div>
            <div>
              <strong>Asistente RAG</strong>
              <span>Documentación técnica</span>
            </div>
          </div>
          <button
            type="button"
            className="btn-icon sidebar-close"
            onClick={onCerrar}
            aria-label="Cerrar menú"
          >
            <IconClose />
          </button>
        </div>

        <button
          type="button"
          className="btn-new-chat"
          onClick={onNueva}
          disabled={deshabilitado}
        >
          <IconPlus />
          Nueva conversación
        </button>

        <div className="sidebar-footer">
          <p>Respuestas basadas solo en los PDFs indexados. Citá siempre la fuente al final.</p>
        </div>
      </aside>
    </>
  );
}
