const MODOS = [
  { id: "todos", label: "Todos" },
  { id: "documentos", label: "Documentos" },
  { id: "informes", label: "Informes" },
];

export default function ChatScopeFilter({ modo, onCambiarModo, disabled = false }) {
  return (
    <div className="chat-scope" aria-label="Filtro de fuentes">
      <div className="chat-scope-modes" role="group" aria-label="Alcance de búsqueda">
        {MODOS.map((m) => (
          <button
            key={m.id}
            type="button"
            className={`chat-scope-chip${modo === m.id ? " chat-scope-chip--active" : ""}`}
            onClick={() => onCambiarModo(m.id)}
            disabled={disabled}
            aria-pressed={modo === m.id}
          >
            {m.label}
          </button>
        ))}
      </div>
    </div>
  );
}
