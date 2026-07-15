import { IconDoc } from "./Icons";

function fuentesUnicas(chunks) {
  const vistas = new Map();
  for (const c of chunks) {
    const clave = `${c.fuente}|${c.pagina}`;
    const prev = vistas.get(clave);
    if (!prev) {
      vistas.set(clave, {
        fuente: c.fuente,
        pagina: c.pagina,
        usada: Boolean(c.usada),
      });
      continue;
    }
    if (c.usada) prev.usada = true;
  }
  const unicas = Array.from(vistas.values());
  unicas.sort((a, b) => Number(b.usada) - Number(a.usada));
  return unicas;
}

export default function SourcePanel({ chunks }) {
  const fuentes = fuentesUnicas(chunks || []);
  if (!fuentes.length) return null;

  const n = fuentes.length;
  const usadas = fuentes.filter((c) => c.usada).length;
  const etiqueta =
    usadas > 0
      ? `${usadas} usada${usadas !== 1 ? "s" : ""} · ${n} consultada${n !== 1 ? "s" : ""}`
      : `${n} fuente${n !== 1 ? "s" : ""} consultada${n !== 1 ? "s" : ""}`;

  return (
    <details className="sources">
      <summary>
        <IconDoc />
        <span>{etiqueta}</span>
      </summary>
      <ul className="sources-list">
        {fuentes.map((c) => (
          <li
            key={`${c.fuente}-${c.pagina}`}
            className={`source-item${c.usada ? " source-item--usada" : ""}`}
          >
            <span className="source-item-label">
              {c.pagina > 0 ? `${c.fuente}, p. ${c.pagina}` : c.fuente}
            </span>
            {c.usada && (
              <span className="source-badge" title="Fuente que respalda la respuesta">
                Usada
              </span>
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}
