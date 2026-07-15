import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProyectoOut(BaseModel):
    id: uuid.UUID
    slug: str
    nombre: str
    descripcion: str = ""
    activo: bool = True

    model_config = {"from_attributes": True}


class ProyectoCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=64)
    descripcion: str = Field(default="", max_length=255)


class SessionSummary(BaseModel):
    id: uuid.UUID
    titulo: str
    creado_en: datetime
    actualizado_en: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: uuid.UUID
    rol: str
    texto: str
    chunks: list[dict] | None = None
    creado_en: datetime

    model_config = {"from_attributes": True}


class SessionDetail(BaseModel):
    id: uuid.UUID
    titulo: str
    creado_en: datetime
    actualizado_en: datetime
    mensajes: list[MessageOut]

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    pregunta: str = Field(..., min_length=1)
    session_id: uuid.UUID | None = None


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    respuesta: str
    chunks: list[dict]
    proyecto_slug: str | None = None


class SessionCreateResponse(BaseModel):
    id: uuid.UUID
    titulo: str

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: uuid.UUID
    nombre: str
    extension: str
    tamano_bytes: int
    perfil: str
    chunks: int
    estado: str
    error: str | None = None
    creado_en: datetime
    actualizado_en: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    documento: DocumentOut
    mensaje: str


class FuenteIndexada(BaseModel):
    fuente: str
    chunks: int


class IndexStatsOut(BaseModel):
    coleccion_existe: bool
    total_chunks: int
    fuentes: int
    chunks_en_catalogo: int
    huerfanos_chunks: int
    huerfanos: list[FuenteIndexada]
    tenant: str | None = None
