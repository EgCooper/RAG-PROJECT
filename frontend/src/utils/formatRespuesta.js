/**
 * Limpia ruido de la respuesta del LLM y deja el Markdown usable en el chat.
 * Solo elimina thinking/citas; no strippea negritas, tablas ni encabezados.
 */

/** Separa filas de tabla pegadas en una sola línea (común en salidas del LLM). */
function normalizarTablasMarkdown(texto) {
  return texto
    .split("\n")
    .map((line) => {
      const pipes = (line.match(/\|/g) || []).length;
      if (pipes < 6) return line;
      return line
        .replace(/\|\s*\|(?=\s*-{2,})/g, "|\n|")
        .replace(/\|\s*\|(?=\s*[^\s|\n-])/g, "|\n|");
    })
    .join("\n");
}

export function formatearRespuesta(texto) {
  if (!texto) return "";

  let t = texto
    .replace(/<think>[\s\S]*?<\/think>/gi, "")
    .replace(/<\/?think>/gi, "");

  // Citas estilo [archivo.pdf, p.N] — las fuentes van en SourcePanel
  t = t.replace(/\[[^\]]+\.(?:pdf|csv|docx|md|ppt|pptx),\s*p\.\d+\]/gi, "");

  t = normalizarTablasMarkdown(t);

  return t.trim();
}
