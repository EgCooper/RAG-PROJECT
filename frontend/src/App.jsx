import { useState, useRef, useEffect, useCallback } from "react";
import {
  enviarPregunta,
  crearSesion,
  eliminarSesion,
  eliminarTodasSesiones,
  getProyectoSlug,
  listarProyectos,
  listarSesiones,
  obtenerSesion,
  setProyectoSlug,
} from "./api";
import Sidebar from "./components/Sidebar";
import ChatMessage from "./components/ChatMessage";
import ConfirmDialog from "./components/ConfirmDialog";
import DocumentsView from "./components/DocumentsView";
import TypingIndicator from "./components/TypingIndicator";
import { IconChevronLeft, IconMenu, IconPlus, IconSend } from "./components/Icons";

const SIDEBAR_OCULTO_KEY = "ach-sidebar-oculto";

function leerSidebarOculto() {
  try {
    return localStorage.getItem(SIDEBAR_OCULTO_KEY) === "true";
  } catch {
    return false;
  }
}

function mensajesDesdeApi(data) {
  return (data.mensajes || []).map((m) => ({
    rol: m.rol,
    texto: m.texto,
    chunks: m.chunks || [],
  }));
}

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [sesiones, setSesiones] = useState([]);
  const [mensajes, setMensajes] = useState([]);
  const [input, setInput] = useState("");
  const [cargando, setCargando] = useState(false);
  const [cargandoSesiones, setCargandoSesiones] = useState(true);
  const [error, setError] = useState("");
  const [sidebarAbierto, setSidebarAbierto] = useState(false);
  const [sidebarOculto, setSidebarOculto] = useState(leerSidebarOculto);
  const [vista, setVista] = useState("chat");
  const [sesionAEliminar, setSesionAEliminar] = useState(null);
  const [confirmarEliminarTodas, setConfirmarEliminarTodas] = useState(false);
  const [eliminandoSesionId, setEliminandoSesionId] = useState(null);
  const [eliminandoTodasSesiones, setEliminandoTodasSesiones] = useState(false);
  const [proyectos, setProyectos] = useState([]);
  const [proyectoSlug, setProyectoSlugState] = useState(getProyectoSlug);
  const [docsKey, setDocsKey] = useState(0);
  const [esDesktop, setEsDesktop] = useState(
    () => window.matchMedia("(min-width: 900px)").matches
  );
  const finRef = useRef(null);
  const inputRef = useRef(null);

  const proyectoActivo =
    proyectos.find((p) => p.slug === proyectoSlug) || proyectos[0] || null;

  const recargarSesiones = useCallback(async () => {
    try {
      const lista = await listarSesiones();
      setSesiones(lista);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const lista = await listarProyectos();
        setProyectos(lista);
        const slugGuardado = getProyectoSlug();
        const existe = lista.some((p) => p.slug === slugGuardado);
        if (!existe && lista[0]) {
          setProyectoSlug(lista[0].slug);
          setProyectoSlugState(lista[0].slug);
        }
      } catch (err) {
        console.error(err);
        setError(err.message);
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      setCargandoSesiones(true);
      setSessionId(null);
      setMensajes([]);
      await recargarSesiones();
      setCargandoSesiones(false);
      setDocsKey((k) => k + 1);
    })();
  }, [proyectoSlug, recargarSesiones]);

  async function handleCambiarProyecto(slug) {
    if (!slug || slug === proyectoSlug) return;
    setProyectoSlug(slug);
    setProyectoSlugState(slug);
    setVista("chat");
    setError("");
  }

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensajes, cargando]);

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_OCULTO_KEY, String(sidebarOculto));
    } catch {
      /* ignore */
    }
  }, [sidebarOculto]);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 900px)");
    const handler = (e) => {
      setEsDesktop(e.matches);
      if (e.matches) setSidebarAbierto(false);
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  function toggleSidebar() {
    if (esDesktop) {
      setSidebarOculto((prev) => !prev);
      setSidebarAbierto(false);
    } else {
      setSidebarAbierto((prev) => !prev);
    }
  }

  function ocultarSidebar() {
    if (esDesktop) {
      setSidebarOculto(true);
    }
    setSidebarAbierto(false);
  }

  const sidebarVisible = esDesktop ? !sidebarOculto : sidebarAbierto;
  const chatLimpio = mensajes.length === 0 && sessionId !== null;

  const abrirSesion = useCallback(
    async (id) => {
      if (cargando || id === sessionId) return;
      setError("");
      setCargando(true);
      setSidebarAbierto(false);
      try {
        const data = await obtenerSesion(id);
        setSessionId(data.id);
        setMensajes(mensajesDesdeApi(data));
      } catch (err) {
        setError(err.message);
      } finally {
        setCargando(false);
        inputRef.current?.focus();
      }
    },
    [cargando, sessionId]
  );

  const enviar = useCallback(
    async (pregunta) => {
      const texto = pregunta.trim();
      if (!texto || cargando) return;

      setInput("");
      setError("");
      setSidebarAbierto(false);
      setMensajes((prev) => [...prev, { rol: "user", texto }]);
      setCargando(true);

      try {
        const data = await enviarPregunta(texto, sessionId);
        if (!sessionId) setSessionId(data.session_id);
        setMensajes((prev) => [
          ...prev,
          {
            rol: "assistant",
            texto: data.respuesta,
            chunks: data.chunks || [],
          },
        ]);
        await recargarSesiones();
      } catch (err) {
        setError(err.message);
      } finally {
        setCargando(false);
        inputRef.current?.focus();
      }
    },
    [cargando, sessionId, recargarSesiones]
  );

  async function handleNueva() {
    if (chatLimpio) {
      inputRef.current?.focus();
      return;
    }

    try {
      const data = await crearSesion();
      setSessionId(data.id);
      setMensajes([]);
      setError("");
      setSidebarAbierto(false);
      await recargarSesiones();
      inputRef.current?.focus();
    } catch (err) {
      setError(err.message);
    }
  }

  function solicitarEliminarSesion(sesion) {
    setSesionAEliminar(sesion);
  }

  async function confirmarEliminarSesion() {
    const sesion = sesionAEliminar;
    if (!sesion) return;

    setEliminandoSesionId(sesion.id);
    setError("");
    try {
      await eliminarSesion(sesion.id);
      if (sessionId === sesion.id) {
        setSessionId(null);
        setMensajes([]);
      }
      setSesionAEliminar(null);
      await recargarSesiones();
    } catch (err) {
      setError(err.message);
    } finally {
      setEliminandoSesionId(null);
    }
  }

  async function confirmarEliminarTodasSesiones() {
    setEliminandoTodasSesiones(true);
    setError("");
    try {
      await eliminarTodasSesiones();
      setSessionId(null);
      setMensajes([]);
      setConfirmarEliminarTodas(false);
      await recargarSesiones();
    } catch (err) {
      setError(err.message);
    } finally {
      setEliminandoTodasSesiones(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    enviar(input);
  }

  return (
    <div className={`shell ${sidebarOculto ? "shell--sidebar-hidden" : ""}`}>
      <Sidebar
        abierto={sidebarAbierto}
        oculto={sidebarOculto}
        onCerrar={() => setSidebarAbierto(false)}
        onNueva={handleNueva}
        onSeleccionar={abrirSesion}
        onSolicitarEliminar={solicitarEliminarSesion}
        onSolicitarEliminarTodas={() => setConfirmarEliminarTodas(true)}
        sesiones={sesiones}
        sessionIdActiva={sessionId}
        cargandoSesiones={cargandoSesiones}
        deshabilitado={cargando}
        nuevaDeshabilitada={chatLimpio}
        eliminandoSesionId={eliminandoSesionId}
        eliminandoTodasSesiones={eliminandoTodasSesiones}
        vista={vista}
        onCambiarVista={(v) => {
          setVista(v);
          setSidebarAbierto(false);
        }}
        proyectos={proyectos}
        proyectoActivo={proyectoActivo}
        onCambiarProyecto={handleCambiarProyecto}
      />

      <div className="main">
        <header className="topbar">
          <button
            type="button"
            className="btn-icon topbar-sidebar-toggle"
            onClick={toggleSidebar}
            aria-label={sidebarVisible ? "Ocultar panel" : "Mostrar panel"}
            title={sidebarVisible ? "Ocultar panel" : "Mostrar panel"}
          >
            {sidebarVisible ? <IconChevronLeft /> : <IconMenu />}
          </button>
          <div className="topbar-title">
            <h1>Asistente {proyectoActivo?.nombre || "RAG"}</h1>
            <span className="topbar-sub">
              {vista === "chat"
                ? "Consultas sobre documentación indexada"
                : "Gestión de documentos del índice"}
            </span>
          </div>
          {vista === "chat" && (
            <button
              type="button"
              className="btn-ghost topbar-new"
              onClick={handleNueva}
              disabled={cargando || chatLimpio}
              title={chatLimpio ? "Ya tenés una conversación vacía abierta" : "Nueva conversación"}
            >
              <IconPlus />
              <span>Nueva</span>
            </button>
          )}
        </header>

        {vista === "documents" ? (
          <main className="documents-main">
            <DocumentsView key={docsKey} />
          </main>
        ) : (
          <>
        <main className="chat" role="log" aria-live="polite">
          {mensajes.length === 0 && !cargando && (
            <div className="welcome">
              <div className="welcome-card">
                <h2>¿En qué te puedo ayudar?</h2>
                <p>
                  Preguntá sobre la documentación indexada de{" "}
                  <strong>{proyectoActivo?.nombre || "este proyecto"}</strong>.
                  Los chats y documentos están aislados por proyecto.
                </p>
              </div>
            </div>
          )}

          <div className="messages">
            {mensajes.map((m, i) => (
              <ChatMessage key={i} mensaje={m} />
            ))}
            {cargando && <TypingIndicator />}
            {error && (
              <div className="alert alert--error" role="alert">
                {error}
              </div>
            )}
            <div ref={finRef} />
          </div>
        </main>

        <footer className="composer-wrap">
          <form className="composer" onSubmit={handleSubmit}>
            <textarea
              ref={inputRef}
              rows={1}
              placeholder="Escribe tu pregunta… (Enter para enviar)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              disabled={cargando}
              aria-label="Pregunta"
            />
            <button
              type="submit"
              className="btn-send"
              disabled={cargando || !input.trim()}
              aria-label="Enviar"
            >
              <IconSend />
            </button>
          </form>
          <p className="composer-hint">Enter para enviar</p>
        </footer>
          </>
        )}
      </div>

      <ConfirmDialog
        open={!!sesionAEliminar}
        title="Eliminar conversación"
        detail={sesionAEliminar?.titulo}
        message="Se borrarán todos los mensajes de este chat. Esta acción no se puede deshacer."
        confirmLabel="Eliminar"
        cancelLabel="Cancelar"
        variant="danger"
        loading={eliminandoSesionId !== null}
        onConfirm={confirmarEliminarSesion}
        onCancel={() => !eliminandoSesionId && setSesionAEliminar(null)}
      />

      <ConfirmDialog
        open={confirmarEliminarTodas}
        title="Eliminar todas las conversaciones"
        detail={`${sesiones.length} conversación${sesiones.length === 1 ? "" : "es"}`}
        message="Se borrarán todos los chats y sus mensajes. Esta acción no se puede deshacer."
        confirmLabel="Eliminar todas"
        cancelLabel="Cancelar"
        variant="danger"
        loading={eliminandoTodasSesiones}
        onConfirm={confirmarEliminarTodasSesiones}
        onCancel={() => !eliminandoTodasSesiones && setConfirmarEliminarTodas(false)}
      />
    </div>
  );
}
