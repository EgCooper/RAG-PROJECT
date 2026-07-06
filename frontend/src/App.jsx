import { useState, useRef, useEffect, useCallback } from "react";
import { enviarPregunta, limpiarSesion } from "./api";
import Sidebar from "./components/Sidebar";
import ChatMessage from "./components/ChatMessage";
import TypingIndicator from "./components/TypingIndicator";
import { IconMenu, IconPlus, IconSend } from "./components/Icons";

function generarSessionId() {
  return crypto.randomUUID();
}

export default function App() {
  const [sessionId, setSessionId] = useState(generarSessionId);
  const [mensajes, setMensajes] = useState([]);
  const [input, setInput] = useState("");
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");
  const [sidebarAbierto, setSidebarAbierto] = useState(false);
  const finRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensajes, cargando]);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 900px)");
    const handler = (e) => {
      if (e.matches) setSidebarAbierto(false);
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

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
        setMensajes((prev) => [
          ...prev,
          {
            rol: "assistant",
            texto: data.respuesta,
            chunks: data.chunks || [],
          },
        ]);
      } catch (err) {
        setError(err.message);
      } finally {
        setCargando(false);
        inputRef.current?.focus();
      }
    },
    [cargando, sessionId]
  );

  async function handleNueva() {
    try {
      await limpiarSesion(sessionId);
      setSessionId(generarSessionId());
      setMensajes([]);
      setError("");
      setSidebarAbierto(false);
    } catch (err) {
      setError(err.message);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    enviar(input);
  }

  return (
    <div className="shell">
      <Sidebar
        abierto={sidebarAbierto}
        onCerrar={() => setSidebarAbierto(false)}
        onNueva={handleNueva}
        deshabilitado={cargando}
      />

      <div className="main">
        <header className="topbar">
          <button
            type="button"
            className="btn-icon topbar-menu"
            onClick={() => setSidebarAbierto(true)}
            aria-label="Abrir menú"
          >
            <IconMenu />
          </button>
          <div className="topbar-title">
            <h1>Asistente ACH</h1>
            <span className="topbar-sub">Consultas sobre documentación indexada</span>
          </div>
          <button
            type="button"
            className="btn-ghost topbar-new"
            onClick={handleNueva}
            disabled={cargando}
          >
            <IconPlus />
            <span>Nueva</span>
          </button>
        </header>

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
      </div>
    </div>
  );
}
