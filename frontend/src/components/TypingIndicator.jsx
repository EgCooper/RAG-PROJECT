export default function TypingIndicator() {
  return (
    <article className="message message--bot message--typing" aria-live="polite" aria-busy="true">
      <div className="message-avatar" aria-hidden>
        <span className="pulse-dot" />
      </div>
      <div className="message-body">
        <span className="message-label">Asistente ACH</span>
        <div className="typing-dots">
          <span /><span /><span />
        </div>
        <span className="typing-text">Buscando en documentos…</span>
      </div>
    </article>
  );
}
