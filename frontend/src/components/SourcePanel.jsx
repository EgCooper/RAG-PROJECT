import { IconDoc } from "./Icons";

function fuentesUnicas(chunks) {
  const vistas = new Set();
  const unicas = [];
  for (const c of chunks) {
    const clave = `${c.fuente}|${c.pagina}`;
    if (vistas.has(clave)) continue;
    vistas.add(clave);
    unicas.push(c);
  }
  return unicas;
}

export default function SourcePanel({ chunks }) {
  const fuentes = fuentesUnicas(chunks || []);
  if (!fuentes.length) return null;

  const n = fuentes.length;
  const etiqueta = `${n} fuente${n !== 1 ? "s" : ""} consultada${n !== 1 ? "s" : ""}`;

  return (
    <details className="sources">
      <summary>
        <IconDoc />
        <span>{etiqueta}</span>
      </summary>
      <ul className="sources-list">
        {fuentes.map((c) => (
          <li key={`${c.fuente}-${c.pagina}`} className="source-item">
            {c.fuente}, p. {c.pagina}
          </li>
        ))}
      </ul>
    </details>
  );
}
