"""Esquemas Pydantic de entrada/salida para /api/chatbot."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.chatbot import RolMensaje


class ChatbotMensajeEntrada(BaseModel):
    """Body de POST /api/chatbot/mensaje."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"mensaje": "¿Qué tortas tienen?"}]})

    mensaje: str
    conversacion_id: int | None = None
    # Solo se usa cuando el visitante no tiene sesión iniciada, para
    # poder mantener el mismo hilo de conversación entre mensajes.
    sesion_id: str | None = None

    @field_validator("mensaje")
    @classmethod
    def _valida_mensaje(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("El mensaje no puede estar vacío.")
        if len(v) > 1000:
            raise ValueError("El mensaje debe tener máximo 1000 caracteres.")
        return v


class MensajeSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rol: RolMensaje
    contenido: str
    creado_en: datetime | None = None


class ProductoChat(BaseModel):
    """Tarjeta de producto que el chat muestra con botón «Añadir al carrito»."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    precio: float
    stock: int
    imagen: str | None = None


class ChatbotMensajeSalida(BaseModel):
    conversacion_id: int
    respuesta: str
    pqr_creada_id: int | None = None
    # Productos sugeridos (máx. 3) para mostrar como tarjetas en el chat.
    productos: list[ProductoChat] = []
    # "ia" = respondió el proveedor de IA; "local" = chatbot gratuito por reglas.
    origen: str = "ia"


class ConversacionSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int | None = None
    creado_en: datetime | None = None
    mensajes: list[MensajeSalida] = []
