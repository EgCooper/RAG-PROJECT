import { useEffect, useRef, useState } from "react";
import {
  IconChat,
  IconCheck,
  IconChevronDown,
  IconClose,
  IconFolder,
  IconMore,
  IconPlus,
  IconTrash,
} from "./Icons";

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

function iniciales(nombre) {
  if (!nombre) return "?";
  const partes = nombre.trim().split(/\s+/);
  if (partes.length === 1) return partes[0].slice(0, 3).toUpperCase();
  return (partes[0][0] + partes[1][0]).toUpperCase();
}

function tonoProyecto(slug) {
  const s = (slug || "").toLowerCase();
  if (s === "ach") return "ach";
  if (s.includes("feel")) return "feel"; // feel-banca → azul
  if (s === "banca" || s.includes("banca")) return "banca"; // morado
  return "default";
}

export default function Sidebar({
  abierto,
  oculto,
  onCerrar,
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
  proyectos = [],
  proyectoActivo = null,
  onCambiarProyecto,
}) {
  const [menuAbiertoId, setMenuAbiertoId] = useState(null);
  const [pickerAbierto, setPickerAbierto] = useState(false);
  const menuRef = useRef(null);
  const pickerRef = useRef(null);

  useEffect(() => {
    if (!menuAbiertoId && !pickerAbierto) return undefined;

    function cerrarSiFuera(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuAbiertoId(null);
      }
      if (pickerRef.current && !pickerRef.current.contains(e.target)) {
        setPickerAbierto(false);
      }
    }

    document.addEventListener("pointerdown", cerrarSiFuera);
    return () => document.removeEventListener("pointerdown", cerrarSiFuera);
  }, [menuAbiertoId, pickerAbierto]);

  function toggleMenu(sessionId, e) {
    e.stopPropagation();
    setMenuAbiertoId((prev) => (prev === sessionId ? null : sessionId));
  }

  function handleEliminar(sesion, e) {
    e.stopPropagation();
    setMenuAbiertoId(null);
    onSolicitarEliminar(sesion);
  }

  function elegirProyecto(slug) {
    setPickerAbierto(false);
    if (slug && slug !== proyectoActivo?.slug) {
      onCambiarProyecto?.(slug);
    }
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
          <div className="project-picker" ref={pickerRef}>
            <button
              type="button"
              className={`project-picker-trigger ${pickerAbierto ? "project-picker-trigger--open" : ""}`}
              onClick={() => setPickerAbierto((v) => !v)}
              disabled={deshabilitado || !proyectos.length}
              aria-expanded={pickerAbierto}
              aria-haspopup="listbox"
              aria-label="Seleccionar proyecto"
            >
              <span
                className={`project-picker-avatar project-picker-avatar--${tonoProyecto(proyectoActivo?.slug)}`}
                aria-hidden
              >
                {iniciales(proyectoActivo?.nombre || proyectoActivo?.slug || "RAG")}
              </span>
              <span className="project-picker-meta">
                <span className="project-picker-kicker">Proyecto</span>
                <span className="project-picker-name">
                  {proyectoActivo?.nombre || "Sin proyecto"}
                </span>
                {proyectoActivo?.descripcion && (
                  <span className="project-picker-desc">{proyectoActivo.descripcion}</span>
                )}
              </span>
              <span className="project-picker-chevron" aria-hidden>
                <IconChevronDown />
              </span>
            </button>

            {pickerAbierto && (
              <ul className="project-picker-menu" role="listbox" aria-label="Proyectos">
                {proyectos.map((p) => {
                  const activo = p.slug === proyectoActivo?.slug;
                  return (
                    <li key={p.slug} role="option" aria-selected={activo}>
                      <button
                        type="button"
                        className={`project-picker-option ${activo ? "project-picker-option--active" : ""}`}
                        onClick={() => elegirProyecto(p.slug)}
                      >
                        <span
                          className={`project-picker-option-avatar project-picker-avatar--${tonoProyecto(p.slug)}`}
                          aria-hidden
                        >
                          {iniciales(p.nombre || p.slug)}
                        </span>
                        <span className="project-picker-option-text">
                          <span className="project-picker-option-name">{p.nombre}</span>
                          {p.descripcion && (
                            <span className="project-picker-option-desc">{p.descripcion}</span>
                          )}
                        </span>
                        {activo && (
                          <span className="project-picker-check" aria-hidden>
                            <IconCheck />
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
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
              {sesiones.length > 0 && (
                <button
                  type="button"
                  className="session-list-clear"
                  onClick={onSolicitarEliminarTodas}
                  disabled={deshabilitado || eliminandoTodasSesiones}
                  title="Borrar todas las conversaciones"
                  aria-label="Borrar todas las conversaciones"
                >
                  <IconTrash />
                </button>
              )}
            </div>
            {cargandoSesiones && <p className="session-list-empty">Cargando…</p>}
            {!cargandoSesiones && sesiones.length === 0 && (
              <p className="session-list-empty">No hay conversaciones aún</p>
            )}
            <ul className="session-list">
              {sesiones.map((s) => {
                const activa = s.id === sessionIdActiva;
                return (
                  <li
                    key={s.id}
                    className={`session-row ${activa ? "session-row--active" : ""}`}
                  >
                    <button
                      type="button"
                      className="session-item"
                      onClick={() => onSeleccionar(s.id)}
                      disabled={deshabilitado}
                    >
                      <span className="session-item-title">{s.titulo}</span>
                      <span className="session-item-date">
                        {formatearFecha(s.actualizado_en)}
                      </span>
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
                            Eliminar
                          </button>
                        </div>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </aside>
    </>
  );
}
