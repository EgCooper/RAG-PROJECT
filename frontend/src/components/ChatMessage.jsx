import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { IconBot, IconUser } from "./Icons";
import SourcePanel from "./SourcePanel";
import { formatearRespuesta } from "../utils/formatRespuesta";

export default function ChatMessage({ mensaje }) {
  const esUsuario = mensaje.rol === "user";
  const streaming = Boolean(mensaje.streaming);
  const texto = mensaje.texto || "";
  const contenido = esUsuario ? texto : formatearRespuesta(texto);

  return (
    <article
      className={`message ${esUsuario ? "message--user" : "message--bot"}${streaming ? " message--streaming" : ""}`}
    >
      <div className="message-avatar" aria-hidden>
        {esUsuario ? <IconUser /> : <IconBot />}
      </div>
      <div className="message-body">
        <div className={`message-content ${esUsuario ? "" : "message-content--prose"}`}>
          {esUsuario ? (
            contenido
          ) : texto ? (
            <>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{contenido}</ReactMarkdown>
              {streaming && <span className="stream-cursor" aria-hidden />}
            </>
          ) : (
            streaming && (
              <span className="stream-waiting" aria-live="polite">
                Generando respuesta…
              </span>
            )
          )}
        </div>
        {!esUsuario && !streaming && mensaje.chunks?.length > 0 && (
          <SourcePanel chunks={mensaje.chunks} />
        )}
      </div>
    </article>
  );
}
