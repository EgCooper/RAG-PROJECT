import { useCallback, useEffect, useRef, useState } from "react";
import { eliminarDocumento, listarDocumentos, subirDocumento } from "../api";
import ConfirmDialog from "./ConfirmDialog";
import { IconDoc, IconTrash, IconUpload } from "./Icons";

const EXTENSIONES = [".pdf", ".csv", ".docx", ".ppt", ".pptx"];
const MAX_ARCHIVOS = 30;

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
    indexando: "Indexando…",
    ok: "Listo",
    error: "Error",
    omitido: "Omitido",
  };
  return map[estado] || estado;
}

export default function DocumentsView() {
  const [documentos, setDocumentos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [procesandoLote, setProcesandoLote] = useState(false);
  const [colaSubida, setColaSubida] = useState([]);
  const [eliminandoId, setEliminandoId] = useState(null);
  const [docAEliminar, setDocAEliminar] = useState(null);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");
  const inputRef = useRef(null);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      const lista = await listarDocumentos();
      setDocumentos(lista);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    recargar();
  }, [recargar]);

  function actualizarItemCola(nombre, cambios) {
    setColaSubida((prev) =>
      prev.map((item) => (item.nombre === nombre ? { ...item, ...cambios } : item))
    );
  }

  async function handleSubir(e) {
    const archivos = Array.from(e.target.files || []);
    e.target.value = "";
    if (!archivos.length || procesandoLote) return;

    setError("");
    setMensaje("");

    if (archivos.length > MAX_ARCHIVOS) {
      setError(`Máximo ${MAX_ARCHIVOS} archivos por lote. Seleccionaste ${archivos.length}.`);
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
      setError("Ningún archivo válido. Usá PDF, CSV, DOCX o PPT/PPTX.");
      setColaSubida(cola);
      return;
    }

    setColaSubida(cola);
    setProcesandoLote(true);

    let ok = 0;
    let fail = 0;

    for (const item of validos) {
      actualizarItemCola(item.nombre, { estado: "indexando", mensaje: "" });
      try {
        const data = await subirDocumento(item.archivo);
        ok += 1;
        actualizarItemCola(item.nombre, { estado: "ok", mensaje: data.mensaje });
      } catch (err) {
        fail += 1;
        actualizarItemCola(item.nombre, { estado: "error", mensaje: err.message });
      }
    }

    await recargar();
    setProcesandoLote(false);

    const omitidos = cola.length - validos.length;
    const partes = [];
    if (ok) partes.push(`${ok} indexado${ok > 1 ? "s" : ""}`);
    if (fail) partes.push(`${fail} con error`);
    if (omitidos) partes.push(`${omitidos} omitido${omitidos > 1 ? "s" : ""}`);
    setMensaje(partes.length ? partes.join(", ") : "Lote procesado");
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
      await recargar();
    } catch (err) {
      setError(err.message);
    } finally {
      setEliminandoId(null);
    }
  }

  const ocupado = procesandoLote || eliminandoId !== null;

  return (
    <div className="documents-view">
      <div className="documents-toolbar">
        <div>
          <h2>Documentos del índice</h2>
          <p className="documents-sub">
            PDFs, CSV, DOCX y presentaciones (PPT/PPTX) que el asistente usa para responder. Podés subir varios archivos a la vez.
          </p>
        </div>
        <div className="documents-actions">
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.csv,.docx,.ppt,.pptx"
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
            {procesandoLote ? "Procesando lote…" : "Subir archivos"}
          </button>
        </div>
      </div>

      {colaSubida.length > 0 && (
        <div className="upload-queue" aria-live="polite">
          <div className="upload-queue-header">
            <strong>Cola de subida</strong>
            {!procesandoLote && (
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
          <p className="documents-sub">Subí PDFs, CSV, DOCX o PPT/PPTX para empezar.</p>
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
                      disabled={ocupado || doc.estado === "indexando"}
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
    </div>
  );
}
