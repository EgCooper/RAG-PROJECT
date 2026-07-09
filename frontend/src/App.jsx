import { useState, useRef, useEffect, useCallback } from "react";
import {
  enviarPregunta,
  crearSesion,
  listarSesiones,
  obtenerSesion,
} from "./api";
import Sidebar from "./components/Sidebar";
import ChatMessage from "./components/ChatMessage";
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
  const [esDesktop, setEsDesktop] = useState(
    () => window.matchMedia("(min-width: 900px)").matches
  );
  const finRef = useRef(null);
  const inputRef = useRef(null);

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
      setCargandoSesiones(true);
      await recargarSesiones();
      setCargandoSesiones(false);
    })();
  }, [recargarSesiones]);

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
        onOcultar={ocultarSidebar}
        onNueva={handleNueva}
        onSeleccionar={abrirSesion}
        sesiones={sesiones}
        sessionIdActiva={sessionId}
        cargandoSesiones={cargandoSesiones}
        deshabilitado={cargando}
        vista={vista}
        onCambiarVista={(v) => {
          setVista(v);
          setSidebarAbierto(false);
        }}
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
            <h1>Asistente ACH</h1>
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
              disabled={cargando}
            >
              <IconPlus />
              <span>Nueva</span>
            </button>
          )}
        </header>

        {vista === "documents" ? (
          <main className="documents-main">
            <DocumentsView />
          </main>
        ) : (
          <>
        <main className="chat" role="log" aria-live="polite">
          {mensajes.length === 0 && !cargando && (
            <div className="welcome">
              <div className="welcome-card">
                <h2>¿En qué te puedo ayudar?</h2>
                <p>
                  Preguntá por códigos de error, abonabilidad, parámetros o
                  procedimientos de los manuales ACH.
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
    </div>
  );
}
