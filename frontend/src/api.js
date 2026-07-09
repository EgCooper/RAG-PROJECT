const API = "/api";

async function parseError(res) {
  const err = await res.json().catch(() => ({}));
  const detail = err.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(", ");
  return `Error ${res.status}`;
}

export async function listarSesiones() {
  const res = await fetch(`${API}/sessions`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function crearSesion() {
  const res = await fetch(`${API}/sessions`, { method: "POST" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function obtenerSesion(sessionId) {
  const res = await fetch(`${API}/sessions/${sessionId}`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function eliminarSesion(sessionId) {
  const res = await fetch(`${API}/sessions/${sessionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function enviarPregunta(pregunta, sessionId) {
  const body = { pregunta };
  if (sessionId) body.session_id = sessionId;

  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function listarDocumentos() {
  const res = await fetch(`${API}/documents`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function subirDocumento(archivo) {
  const form = new FormData();
  form.append("archivo", archivo);

  const res = await fetch(`${API}/documents/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function eliminarDocumento(documentId) {
  const res = await fetch(`${API}/documents/${documentId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

/** @deprecated Usar crearSesion() */
export async function limpiarSesion() {
  return crearSesion();
}
