import { IconChat, IconChevronLeft, IconClose, IconFolder, IconPlus } from "./Icons";

function formatearFecha(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Sidebar({
  abierto,
  oculto,
  onCerrar,
  onOcultar,
  onNueva,
  onSeleccionar,
  sesiones,
  sessionIdActiva,
  cargandoSesiones,
  deshabilitado,
  vista,
  onCambiarVista,
}) {
  return (
    <>
      <div
        className={`sidebar-backdrop ${abierto ? "sidebar-backdrop--visible" : ""}`}
        onClick={onCerrar}
        aria-hidden={!abierto}
      />
      <aside
        className={`sidebar ${abierto ? "sidebar--open" : ""} ${oculto ? "sidebar--hidden" : ""}`}
        aria-label="Panel lateral"
        aria-hidden={oculto}
      >
        <div className="sidebar-header">
          <div className="brand">
            <div className="brand-icon">ACH</div>
            <div>
              <strong>Asistente RAG</strong>
              <span>Documentación técnica</span>
            </div>
          </div>
          <div className="sidebar-header-actions">
            <button
              type="button"
              className="btn-icon sidebar-hide"
              onClick={onOcultar}
              aria-label="Ocultar panel"
              title="Ocultar panel"
            >
              <IconChevronLeft />
            </button>
            <button
              type="button"
              className="btn-icon sidebar-close"
              onClick={onCerrar}
              aria-label="Cerrar menú"
            >
              <IconClose />
            </button>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Navegación principal">
          <button
            type="button"
            className={`sidebar-nav-item ${vista === "chat" ? "sidebar-nav-item--active" : ""}`}
            onClick={() => onCambiarVista("chat")}
          >
            <IconChat />
            Chat
          </button>
          <button
            type="button"
            className={`sidebar-nav-item ${vista === "documents" ? "sidebar-nav-item--active" : ""}`}
            onClick={() => onCambiarVista("documents")}
          >
            <IconFolder />
            Documentos
          </button>
        </nav>

        {vista === "chat" && (
        <button
          type="button"
          className="btn-new-chat"
          onClick={onNueva}
          disabled={deshabilitado}
        >
          <IconPlus />
          Nueva conversación
        </button>
        )}

        {vista === "chat" && (
        <div className="session-list-wrap custom-scroll custom-scroll--dark">
          <p className="session-list-label">Conversaciones</p>
          {cargandoSesiones && <p className="session-list-empty">Cargando…</p>}
          {!cargandoSesiones && sesiones.length === 0 && (
            <p className="session-list-empty">Sin conversaciones aún</p>
          )}
          <ul className="session-list" role="list">
            {sesiones.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  className={`session-item ${s.id === sessionIdActiva ? "session-item--active" : ""}`}
                  onClick={() => onSeleccionar(s.id)}
                  disabled={deshabilitado}
                >
                  <span className="session-item-title">{s.titulo}</span>
                  <span className="session-item-date">{formatearFecha(s.actualizado_en)}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
        )}

        <div className="sidebar-footer">
          <p>
            {vista === "chat"
              ? "Respuestas basadas solo en los documentos indexados."
              : "Subí PDFs, CSV, DOCX o PPT/PPTX para ampliar el conocimiento del asistente."}
          </p>
        </div>
      </aside>
    </>
  );
}
