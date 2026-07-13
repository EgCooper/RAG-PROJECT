import { useCallback, useEffect, useRef, useState } from "react";
import {
  eliminarDocumento,
  eliminarTodosDocumentos,
  listarDocumentos,
  obtenerConfigUpload,
  obtenerEstadisticasIndice,
  subirDocumento,
} from "../api";
import ConfirmDialog from "./ConfirmDialog";
import { IconDoc, IconTrash, IconUpload } from "./Icons";

const EXTENSIONES = [".pdf", ".csv", ".docx", ".md", ".ppt", ".pptx"];
const MAX_ARCHIVOS_DEFAULT = 100;
const POLL_MS = 2500;

function extensionDe(nombre) {
  const i = nombre.lastIndexOf(".");
  return i >= 0 ? nombre.slice(i).toLowerCase() : "";
}

function formatearTamano(bytes) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatearFecha(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function etiquetaEstado(estado) {
  const map = {
    indexado: "Indexado",
    indexando: "Indexando…",
    pendiente: "Pendiente",
    error: "Error",
  };
  return map[estado] || estado;
}

function etiquetaCola(estado) {
  const map = {
    pendiente: "En cola",
    subiendo: "Subiendo…",
    subido: "En cola de indexación",
    ok: "Listo",
    error: "Error",
    omitido: "Omitido",
  };
  return map[estado] || estado;
}

function hayIndexacionActiva(lista) {
  return lista.some((d) => d.estado === "pendiente" || d.estado === "indexando");
}

function ordenPendientes(a, b) {
  const peso = { indexando: 0, pendiente: 1 };
  const pa = peso[a.estado] ?? 2;
  const pb = peso[b.estado] ?? 2;
  if (pa !== pb) return pa - pb;
  return new Date(a.creado_en) - new Date(b.creado_en);
}

export default function DocumentsView() {
  const [documentos, setDocumentos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [subiendoArchivos, setSubiendoArchivos] = useState(false);
  const [colaSubida, setColaSubida] = useState([]);
  const [eliminandoId, setEliminandoId] = useState(null);
  const [docAEliminar, setDocAEliminar] = useState(null);
  const [confirmarEliminarTodos, setConfirmarEliminarTodos] = useState(false);
  const [eliminandoTodos, setEliminandoTodos] = useState(false);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [indexStats, setIndexStats] = useState(null);
  const [maxArchivos, setMaxArchivos] = useState(MAX_ARCHIVOS_DEFAULT);
  const inputRef = useRef(null);

  const recargarStats = useCallback(async () => {
    try {
      const stats = await obtenerEstadisticasIndice();
      setIndexStats(stats);
    } catch {
      setIndexStats(null);
    }
  }, []);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      const lista = await listarDocumentos();
      setDocumentos(lista);
      await recargarStats();
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  }, [recargarStats]);

  const recargarSilencioso = useCallback(async () => {
    try {
      const lista = await listarDocumentos();
      setDocumentos(lista);
      await recargarStats();
    } catch {
      // Polling silencioso: no pisar errores visibles del usuario
    }
  }, [recargarStats]);

  useEffect(() => {
    recargar();
  }, [recargar]);

  useEffect(() => {
    obtenerConfigUpload()
      .then((cfg) => setMaxArchivos(cfg.uploadBatchMaxFiles))
      .catch(() => setMaxArchivos(MAX_ARCHIVOS_DEFAULT));
  }, []);

  const indexacionActiva = hayIndexacionActiva(documentos);
  const pendientes = documentos
    .filter((d) => d.estado === "pendiente" || d.estado === "indexando")
    .sort(ordenPendientes);
  const ocupado = subiendoArchivos || eliminandoId !== null || eliminandoTodos;

  useEffect(() => {
    if (!indexacionActiva) return undefined;
    const id = setInterval(recargarSilencioso, POLL_MS);
    return () => clearInterval(id);
  }, [indexacionActiva, recargarSilencioso]);

  function actualizarItemCola(nombre, cambios) {
    setColaSubida((prev) =>
      prev.map((item) => (item.nombre === nombre ? { ...item, ...cambios } : item))
    );
  }

  async function handleSubir(e) {
    const archivos = Array.from(e.target.files || []);
    e.target.value = "";
    if (!archivos.length || subiendoArchivos) return;

    setError("");
    setMensaje("");

    if (archivos.length > maxArchivos) {
      setError(`Máximo ${maxArchivos} archivos por lote. Seleccionaste ${archivos.length}.`);
      return;
    }

    const cola = archivos.map((archivo) => {
      const ext = extensionDe(archivo.name);
      const valido = EXTENSIONES.includes(ext);
      return {
        nombre: archivo.name,
        archivo,
        estado: valido ? "pendiente" : "omitido",
        mensaje: valido ? "" : `Formato no permitido (${ext || "sin extensión"})`,
      };
    });

    const validos = cola.filter((item) => item.estado === "pendiente");
    if (!validos.length) {
      setError("Ningún archivo válido. Usá PDF, CSV, DOCX, Markdown o PPT/PPTX.");
      setColaSubida(cola);
      return;
    }

    setColaSubida(cola);
    setSubiendoArchivos(true);

    validos.forEach((item) => {
      actualizarItemCola(item.nombre, { estado: "subiendo", mensaje: "" });
    });

    const resultados = await Promise.allSettled(
      validos.map(async (item) => {
        try {
          const data = await subirDocumento(item.archivo);
          actualizarItemCola(item.nombre, {
            estado: "subido",
            mensaje: data.mensaje,
          });
          return { ok: true };
        } catch (err) {
          actualizarItemCola(item.nombre, { estado: "error", mensaje: err.message });
          return { ok: false };
        }
      })
    );

    await recargarSilencioso();
    setSubiendoArchivos(false);

    const ok = resultados.filter((r) => r.status === "fulfilled" && r.value.ok).length;
    const fail = validos.length - ok;
    const omitidos = cola.length - validos.length;

    const partes = [];
    if (ok) partes.push(`${ok} en cola de indexación`);
    if (fail) partes.push(`${fail} con error al subir`);
    if (omitidos) partes.push(`${omitidos} omitido${omitidos > 1 ? "s" : ""}`);
    setMensaje(
      partes.length
        ? `${partes.join(", ")}. El progreso se actualiza automáticamente.`
        : "Lote procesado"
    );
  }

  function solicitarEliminar(doc) {
    setDocAEliminar(doc);
  }

  async function confirmarEliminar() {
    const doc = docAEliminar;
    if (!doc) return;

    setEliminandoId(doc.id);
    setError("");
    setMensaje("");
    try {
      await eliminarDocumento(doc.id);
      setMensaje(`"${doc.nombre}" eliminado`);
      setDocAEliminar(null);
      await recargarSilencioso();
    } catch (err) {
      setError(err.message);
    } finally {
      setEliminandoId(null);
    }
  }

  async function ejecutarEliminarTodos() {
    setEliminandoTodos(true);
    setError("");
    setMensaje("");
    try {
      const data = await eliminarTodosDocumentos();
      setConfirmarEliminarTodos(false);
      setColaSubida([]);
      setMensaje(
        data.eliminados
          ? `${data.eliminados} documento${data.eliminados === 1 ? "" : "s"} eliminado${data.eliminados === 1 ? "" : "s"}`
          : "No había documentos para eliminar"
      );
      await recargarSilencioso();
    } catch (err) {
      setError(err.message);
    } finally {
      setEliminandoTodos(false);
    }
  }

  return (
    <div className="documents-view">
      <div className="documents-toolbar">
        <div>
          <h2>Documentos del índice</h2>
          <p className="documents-sub">
            PDFs, CSV, DOCX, Markdown y presentaciones (PPT/PPTX) que el asistente usa para responder. Podés subir varios archivos a la vez.
          </p>
          {indexStats && (
            <div className="documents-index-stats" role="status">
              <span>
                Índice Weaviate:{" "}
                <strong>{indexStats.total_chunks.toLocaleString()}</strong> chunk
                {indexStats.total_chunks === 1 ? "" : "s"}
                {indexStats.fuentes > 0 && (
                  <> · {indexStats.fuentes} fuente{indexStats.fuentes === 1 ? "" : "s"}</>
                )}
              </span>
              {indexStats.total_chunks === 0 && (
                <span className="index-stats-badge index-stats-badge--ok">Vacío</span>
              )}
              {indexStats.huerfanos_chunks > 0 && (
                <span
                  className="index-stats-badge index-stats-badge--warn"
                  title={indexStats.huerfanos.map((h) => `${h.fuente} (${h.chunks})`).join("\n")}
                >
                  {indexStats.huerfanos_chunks} huérfano{indexStats.huerfanos_chunks === 1 ? "" : "s"}
                </span>
              )}
            </div>
          )}
        </div>
        <div className="documents-actions">
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.csv,.docx,.md,.ppt,.pptx"
            multiple
            className="documents-file-input"
            onChange={handleSubir}
            disabled={ocupado}
            aria-label="Seleccionar archivos"
          />
          <button
            type="button"
            className="btn-primary"
            onClick={() => inputRef.current?.click()}
            disabled={ocupado}
          >
            <IconUpload />
            {subiendoArchivos ? "Subiendo…" : "Subir archivos"}
          </button>
        </div>
      </div>

      {pendientes.length > 0 && (
        <div className="documents-pending" aria-live="polite">
          <div className="documents-pending-header">
            <strong>Pendientes de indexación ({pendientes.length})</strong>
            <span className="documents-pending-hint">
              El proceso continúa en el servidor aunque cambies de vista o actualices la página.
            </span>
          </div>
          <ul className="documents-pending-list">
            {pendientes.map((doc) => (
              <li key={doc.id} className={`documents-pending-item documents-pending-item--${doc.estado}`}>
                <IconDoc />
                <span className="documents-pending-name" title={doc.nombre}>
                  {doc.nombre}
                </span>
                <span className="documents-pending-meta">{formatearTamano(doc.tamano_bytes)}</span>
                <span className={`doc-badge doc-badge--${doc.estado}`}>
                  {etiquetaEstado(doc.estado)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {indexacionActiva && !subiendoArchivos && pendientes.length === 0 && (
        <div className="alert alert--info" role="status">
          Indexación en curso. Podés cambiar de vista o actualizar la página; el proceso continúa en el servidor.
        </div>
      )}

      {colaSubida.length > 0 && (
        <div className="upload-queue" aria-live="polite">
          <div className="upload-queue-header">
            <strong>Última subida</strong>
            {!subiendoArchivos && (
              <button
                type="button"
                className="btn-ghost-sm"
                onClick={() => setColaSubida([])}
              >
                Ocultar
              </button>
            )}
          </div>
          <ul className="upload-queue-list">
            {colaSubida.map((item) => (
              <li key={item.nombre} className={`upload-queue-item upload-queue-item--${item.estado}`}>
                <span className="upload-queue-name" title={item.nombre}>
                  {item.nombre}
                </span>
                <span className={`upload-queue-badge upload-queue-badge--${item.estado}`}>
                  {etiquetaCola(item.estado)}
                </span>
                {item.mensaje && (
                  <span className="upload-queue-msg" title={item.mensaje}>
                    {item.mensaje}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {mensaje && (
        <div className="alert alert--success" role="status">
          {mensaje}
        </div>
      )}
      {error && (
        <div className="alert alert--error" role="alert">
          {error}
        </div>
      )}

      {cargando ? (
        <p className="documents-empty">Cargando documentos…</p>
      ) : documentos.length === 0 ? (
        <div className="documents-empty-card">
          <IconDoc />
          <p>No hay documentos indexados.</p>
          <p className="documents-sub">Subí PDFs, CSV, DOCX, Markdown o PPT/PPTX para empezar.</p>
        </div>
      ) : (
        <div className="documents-table-wrap">
          <table className="documents-table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Tamaño</th>
                <th>Perfil</th>
                <th>Chunks</th>
                <th>Estado</th>
                <th>Actualizado</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {documentos.map((doc) => (
                <tr key={doc.id}>
                  <td className="documents-name">
                    <IconDoc />
                    <span title={doc.nombre}>{doc.nombre}</span>
                  </td>
                  <td>{formatearTamano(doc.tamano_bytes)}</td>
                  <td>{doc.perfil || "—"}</td>
                  <td>{doc.chunks || "—"}</td>
                  <td>
                    <span
                      className={`doc-badge doc-badge--${doc.estado}`}
                      title={doc.error || undefined}
                    >
                      {etiquetaEstado(doc.estado)}
                    </span>
                  </td>
                  <td className="documents-date">{formatearFecha(doc.actualizado_en)}</td>
                  <td>
                    <button
                      type="button"
                      className="btn-icon btn-danger-ghost"
                      onClick={() => solicitarEliminar(doc)}
                      disabled={
                        ocupado || doc.estado === "indexando" || doc.estado === "pendiente"
                      }
                      aria-label={`Eliminar ${doc.nombre}`}
                    >
                      <IconTrash />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!cargando && documentos.length > 0 && (
        <div className="documents-footer-actions">
          <button
            type="button"
            className="btn-danger-outline"
            onClick={() => setConfirmarEliminarTodos(true)}
            disabled={ocupado}
          >
            <IconTrash />
            Eliminar todos
          </button>
        </div>
      )}

      <ConfirmDialog
        open={!!docAEliminar}
        title="Eliminar documento"
        detail={docAEliminar?.nombre}
        message="Se borrará del índice vectorial y el asistente dejará de usar este archivo en las respuestas. Esta acción no se puede deshacer."
        confirmLabel="Eliminar"
        cancelLabel="Cancelar"
        variant="danger"
        loading={eliminandoId !== null}
        onConfirm={confirmarEliminar}
        onCancel={() => !eliminandoId && setDocAEliminar(null)}
      />

      <ConfirmDialog
        open={confirmarEliminarTodos}
        title="Eliminar todos los documentos"
        detail={`${documentos.length} documento${documentos.length === 1 ? "" : "s"}`}
        message="Se borrarán todos los archivos del índice vectorial y del catálogo, incluidos los que estén en cola o indexándose. Esta acción no se puede deshacer."
        confirmLabel="Eliminar todos"
        cancelLabel="Cancelar"
        variant="danger"
        loading={eliminandoTodos}
        onConfirm={ejecutarEliminarTodos}
        onCancel={() => !eliminandoTodos && setConfirmarEliminarTodos(false)}
      />
    </div>
  );
}
