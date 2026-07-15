const API = "/api";
const PROYECTO_KEY = "rag-proyecto-slug";

export function getProyectoSlug() {
  try {
    return localStorage.getItem(PROYECTO_KEY) || "ach";
  } catch {
    return "ach";
  }
}

export function setProyectoSlug(slug) {
  try {
    localStorage.setItem(PROYECTO_KEY, slug);
  } catch {
    /* ignore */
  }
}

function headers(extra = {}) {
  return {
    "X-Proyecto-Slug": getProyectoSlug(),
    ...extra,
  };
}

async function parseError(res) {
  const err = await res.json().catch(() => ({}));
  const detail = err.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(", ");
  return `Error ${res.status}`;
}

export async function listarProyectos() {
  const res = await fetch(`${API}/proyectos`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function crearProyecto({ nombre, slug, descripcion }) {
  const res = await fetch(`${API}/proyectos`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ nombre, slug, descripcion }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function listarSesiones() {
  const res = await fetch(`${API}/sessions`, { headers: headers() });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function crearSesion() {
  const res = await fetch(`${API}/sessions`, {
    method: "POST",
    headers: headers(),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function obtenerSesion(sessionId) {
  const res = await fetch(`${API}/sessions/${sessionId}`, { headers: headers() });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function eliminarSesion(sessionId) {
  const res = await fetch(`${API}/sessions/${sessionId}`, {
    method: "DELETE",
    headers: headers(),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function eliminarTodasSesiones() {
  const res = await fetch(`${API}/sessions`, {
    method: "DELETE",
    headers: headers(),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function enviarPregunta(pregunta, sessionId) {
  const body = { pregunta };
  if (sessionId) body.session_id = sessionId;

  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function obtenerConfigUpload() {
  const res = await fetch(`${API}/health`);
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return {
    uploadMaxMb: data.upload_max_mb ?? 50,
    uploadBatchMaxFiles: data.upload_batch_max_files ?? 100,
  };
}

export async function listarDocumentos() {
  const res = await fetch(`${API}/documents`, { headers: headers() });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function obtenerEstadisticasIndice() {
  const res = await fetch(`${API}/documents/index-stats`, { headers: headers() });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function subirDocumento(archivo) {
  const form = new FormData();
  form.append("archivo", archivo);

  const res = await fetch(`${API}/documents/upload`, {
    method: "POST",
    headers: headers(),
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function eliminarDocumento(documentId) {
  const res = await fetch(`${API}/documents/${documentId}`, {
    method: "DELETE",
    headers: headers(),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function eliminarTodosDocumentos() {
  const res = await fetch(`${API}/documents`, {
    method: "DELETE",
    headers: headers(),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

/** @deprecated Usar crearSesion() */
export async function limpiarSesion() {
  return crearSesion();
}
