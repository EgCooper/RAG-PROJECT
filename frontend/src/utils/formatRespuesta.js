/**
 * Limpia la respuesta del LLM para mostrar solo texto útil en el front.
 */
export function formatearRespuesta(texto) {
  if (!texto) return "";

  let t = texto
    .replace(/[\s\S]*?<\/redacted_thinking>/gi, "")
    .replace(/[\s\S]*?<\/think>/gi, "");

  t = t.replace(/\[[^\]]+\.pdf,\s*p\.\d+\]/gi, "");

  const lineas = t.split("\n");
  const partes = [];

  for (const linea of lineas) {
    const s = linea.trim();
    if (!s) continue;
    if (s.startsWith("#")) continue;
    if (s.includes("|")) continue;
    if (/^[-|:]+$/.test(s.replace(/\|/g, "").trim())) continue;

    const limpia = s
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1")
      .replace(/^[-*]\s+/, "")
      .trim();

    if (limpia) partes.push(limpia);
  }

  if (partes.length === 1) return partes[0];

  return partes.join("\n").trim();
}
