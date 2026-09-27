"""
Esquemas Pydantic de entrada/salida para /api/pagos y /api/webhooks.

Los montos viajan en PESOS (COP) en la API pública (`monto`), igual
que el resto de esta aplicación (pedidos, productos, carrito), y se
convierten a CENTAVOS únicamente al hablar con Wompi y al guardarse en
`Pago.monto_centavos` — ver app/services/pagos/payment_service.py.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.pago import EstadoPago

# Wompi Colombia solo soporta COP por ahora (ver documentación oficial
# de Transacciones). Se deja como lista para no tener que tocar el
# schema si Wompi habilita otra moneda más adelante.
MONEDAS_SOPORTADAS = {"COP"}


class PagoCrear(BaseModel):
    """Body de POST /api/pagos."""

    model_config = ConfigDict(str_strip_whitespace=True, json_schema_extra={"examples": [{"monto": 189000, "moneda": "COP", "correo_cliente": "cliente@ejemplo.com", "nombre_cliente": "Laura Gómez", "descripcion": "Pedido #12", "proveedor": "wompi", "pedido_id": 12, "url_redireccion": "http://localhost:5173/pago/resultado"}]})

    monto: float = Field(gt=0, description="Monto a cobrar, en PESOS (no en centavos).")
    moneda: str = "COP"
    correo_cliente: EmailStr
    nombre_cliente: str | None = None
    descripcion: str | None = Field(default=None, max_length=255)
    proveedor: Literal["wompi"] = "wompi"
    pedido_id: int | None = None
    url_redireccion: str | None = Field(
        default=None,
        description="URL propia a la que Wompi redirige al cliente al terminar el pago (opcional).",
    )

    @field_validator("moneda")
    @classmethod
    def _valida_moneda(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if v not in MONEDAS_SOPORTADAS:
            raise ValueError(f"Moneda no soportada: '{v}'. Soportadas: {', '.join(sorted(MONEDAS_SOPORTADAS))}.")
        return v

    @field_validator("nombre_cliente")
    @classmethod
    def _valida_nombre(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None


class PagoSalida(BaseModel):
    """
    Forma de un pago en las respuestas de la API. Nunca incluye
    `respuesta_cruda` ni `payload_webhook` completos (podrían llegar a
    contener datos que no queremos exponer tal cual al frontend) — solo
    los campos ya explícitamente pedidos en el punto 8 del alcance.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    referencia: str
    proveedor: str
    id_transaccion_proveedor: str | None = None
    # No existe como columna en el modelo ORM (ahí se guarda
    # `monto_centavos`) — por eso lleva un default: así
    # `model_validate(pago)` no falla al no encontrar el atributo
    # `monto`, y `desde_modelo()` lo reemplaza enseguida con el valor
    # real ya convertido a pesos.
    monto: float = 0.0
    moneda: str
    estado: EstadoPago
    metodo_pago: str | None = None
    correo_cliente: str
    nombre_cliente: str | None = None
    pedido_id: int | None = None
    creado_por_usuario_id: int | None = None
    url_checkout: str | None = None
    creado_en: datetime | None = None
    actualizado_en: datetime | None = None

    @classmethod
    def desde_modelo(cls, pago) -> "PagoSalida":
        """`monto` sale en pesos aunque en BD se guarde en centavos."""
        datos = cls.model_validate(pago).model_dump()
        datos["monto"] = pago.monto_centavos / 100
        return cls(**datos)


class PagoCrearRespuesta(BaseModel):
    """Respuesta de POST /api/pagos — forma exacta pedida en el punto 7 del alcance."""

    payment_id: int
    reference: str
    status: EstadoPago
    checkout_url: str | None = None
    provider: str


class WompiFirmaEvento(BaseModel):
    """Objeto `signature` dentro de un evento de Wompi."""

    properties: list[str]
    checksum: str


class WebhookWompiEntrada(BaseModel):
    """
    Forma mínima de un evento de Wompi (ver
    https://docs.wompi.co/docs/colombia/eventos/). `data` se deja como
    dict libre porque su forma cambia según `event`
    (transaction.updated, nequi_token.updated, etc.) y las propiedades
    a validar vienen indicadas dinámicamente en `signature.properties`.
    """

    event: str
    data: dict[str, Any]
    environment: str
    signature: WompiFirmaEvento
    timestamp: int
    sent_at: str | None = None
