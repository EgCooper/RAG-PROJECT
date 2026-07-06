import { IconBot, IconUser } from "./Icons";
import SourcePanel from "./SourcePanel";
import { formatearRespuesta } from "../utils/formatRespuesta";

export default function ChatMessage({ mensaje }) {
  const esUsuario = mensaje.rol === "user";
  const contenido = esUsuario ? mensaje.texto : formatearRespuesta(mensaje.texto);

  return (
    <article className={`message ${esUsuario ? "message--user" : "message--bot"}`}>
      <div className="message-avatar" aria-hidden>
        {esUsuario ? <IconUser /> : <IconBot />}
      </div>
      <div className="message-body">
        <div className={`message-content ${esUsuario ? "" : "message-content--prose"}`}>
          {contenido}
        </div>
        {!esUsuario && mensaje.chunks?.length > 0 && (
          <SourcePanel chunks={mensaje.chunks} />
        )}
      </div>
    </article>
  );
}
