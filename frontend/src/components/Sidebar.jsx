import { useEffect, useRef, useState } from "react";
import { IconChat, IconChevronLeft, IconClose, IconFolder, IconMore, IconPlus, IconTrash } from "./Icons";

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
  onSolicitarEliminar,
  onSolicitarEliminarTodas,
  sesiones,
  sessionIdActiva,
  cargandoSesiones,
  deshabilitado,
  nuevaDeshabilitada,
  eliminandoSesionId,
  eliminandoTodasSesiones,
  vista,
  onCambiarVista,
}) {
  const [menuAbiertoId, setMenuAbiertoId] = useState(null);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!menuAbiertoId) return undefined;

    function cerrarSiFuera(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuAbiertoId(null);
      }
    }

    document.addEventListener("pointerdown", cerrarSiFuera);
    return () => document.removeEventListener("pointerdown", cerrarSiFuera);
  }, [menuAbiertoId]);

  function toggleMenu(sessionId, e) {
    e.stopPropagation();
    setMenuAbiertoId((prev) => (prev === sessionId ? null : sessionId));
  }

  function handleEliminar(sesion, e) {
    e.stopPropagation();
    setMenuAbiertoId(null);
    onSolicitarEliminar(sesion);
  }

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
          disabled={deshabilitado || nuevaDeshabilitada}
          title={nuevaDeshabilitada ? "Ya tenés una conversación vacía abierta" : "Nueva conversación"}
        >
          <IconPlus />
          Nueva conversación
        </button>
        )}

        {vista === "chat" && (
        <div className="session-list-wrap custom-scroll custom-scroll--dark">
          <div className="session-list-header">
            <p className="session-list-label">Conversaciones</p>
            <button
              type="button"
              className="session-list-clear"
              onClick={onSolicitarEliminarTodas}
              disabled={
                deshabilitado ||
                eliminandoTodasSesiones ||
                eliminandoSesionId !== null ||
                sesiones.length === 0
              }
              title="Eliminar todas las conversaciones"
              aria-label="Eliminar todas las conversaciones"
            >
              <IconTrash />
            </button>
          </div>
          {cargandoSesiones && <p className="session-list-empty">Cargando…</p>}
          {!cargandoSesiones && sesiones.length === 0 && (
            <p className="session-list-empty">Sin conversaciones aún</p>
          )}
          <ul className="session-list" role="list">
            {sesiones.map((s) => (
              <li
                key={s.id}
                className={`session-row ${s.id === sessionIdActiva ? "session-row--active" : ""}`}
              >
                <button
                  type="button"
                  className="session-item"
                  onClick={() => onSeleccionar(s.id)}
                  disabled={deshabilitado || eliminandoSesionId === s.id}
                >
                  <span className="session-item-title">{s.titulo}</span>
                  <span className="session-item-date">{formatearFecha(s.actualizado_en)}</span>
                </button>
                <div
                  className="session-row-menu"
                  ref={menuAbiertoId === s.id ? menuRef : null}
                >
                  <button
                    type="button"
                    className={`session-menu-trigger ${menuAbiertoId === s.id ? "session-menu-trigger--open" : ""}`}
                    onClick={(e) => toggleMenu(s.id, e)}
                    disabled={deshabilitado || eliminandoSesionId === s.id}
                    aria-label={`Opciones de ${s.titulo}`}
                    aria-expanded={menuAbiertoId === s.id}
                    aria-haspopup="menu"
                  >
                    <IconMore />
                  </button>
                  {menuAbiertoId === s.id && (
                    <div className="session-menu-dropdown" role="menu">
                      <button
                        type="button"
                        className="session-menu-item session-menu-item--danger"
                        role="menuitem"
                        onClick={(e) => handleEliminar(s, e)}
                      >
                        <IconTrash />
                        Eliminar chat
                      </button>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
        )}

        <div className="sidebar-footer">
          <p>
            {vista === "chat"
              ? "Respuestas basadas solo en los documentos indexados."
              : "Subí PDFs, CSV, DOCX, Markdown o PPT/PPTX para ampliar el conocimiento del asistente."}
          </p>
        </div>
      </aside>
    </>
  );
}
