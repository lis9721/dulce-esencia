"""
Esquemas Pydantic de entrada/salida para /api/pedidos.

El pedido se arma en el backend a partir del carrito actual del
usuario (nunca a partir de una lista de ítems que mande el cliente
HTTP): así el precio y el stock que se cobran son siempre los reales
del servidor en el momento del checkout, no los que el navegador
"crea" tener. Por eso PedidoCrear solo pide los datos de envío/pago,
no los productos.
"""

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.pedido import EstadoPedido, MetodoPago, TipoEntrega

REGEX_SOLO_NUMEROS = re.compile(r"^[0-9]+$")
REGEX_FRANJA_HORARIA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d$")

MAX_DECIMAL_10_2 = 99999999.99


def validar_direccion_envio(valor: str) -> str:
    """pedidos.direccion_envio es VARCHAR(150) (más holgada que usuarios.direccion, VARCHAR(100))."""
    valor = (valor or "").strip()
    if not valor:
        raise ValueError("La dirección de envío es obligatoria.")
    if len(valor) < 5:
        raise ValueError("Debe tener al menos 5 caracteres.")
    if len(valor) > 150:
        raise ValueError("Debe tener máximo 150 caracteres.")
    return valor


def validar_telefono_contacto(valor: str) -> str:
    """pedidos.telefono_contacto es VARCHAR(15), misma regla que usuarios.telefono."""
    valor = (valor or "").strip()
    if not valor:
        raise ValueError("El teléfono de contacto es obligatorio.")
    if not REGEX_SOLO_NUMEROS.match(valor):
        raise ValueError("El teléfono solo debe contener números.")
    if len(valor) < 7 or len(valor) > 15:
        raise ValueError("Debe tener entre 7 y 15 dígitos.")
    return valor


class PedidoCrear(BaseModel):
    """
    Body de POST /api/pedidos (checkout). `cupon_codigo` es opcional
    (compra sin cupón). `idempotency_key` es opcional pero
    recomendado: si el cliente reenvía la misma petición (doble clic,
    reintento de red) con la misma clave, el backend devuelve el
    pedido ya creado en vez de cobrar dos veces — respaldado por el
    UniqueConstraint(usuario_id, idempotency_key) del modelo.

    `direccion_envio` es obligatoria solo cuando `tipo_entrega` es
    "domicilio" (validado en `_valida_combinacion_entrega` más abajo);
    para "recoger_tienda" se ignora lo que mande el cliente y el
    backend guarda un texto fijo (ver app/routes/pedidos.py) — así no
    hay forma de que un pedido para recoger en tienda quede con una
    dirección de otro pedido pegada por error del frontend.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    direccion_envio: str | None = None
    telefono_contacto: str
    metodo_pago: MetodoPago
    tipo_entrega: TipoEntrega = TipoEntrega.domicilio
    fecha_entrega_solicitada: date | None = None
    franja_horaria: str | None = None
    cupon_codigo: str | None = None
    idempotency_key: str | None = None

    @field_validator("telefono_contacto")
    @classmethod
    def _valida_telefono(cls, v: str) -> str:
        return validar_telefono_contacto(v)

    @field_validator("fecha_entrega_solicitada")
    @classmethod
    def _valida_fecha_entrega(cls, v: date | None) -> date | None:
        if v is not None and v < date.today():
            raise ValueError("La fecha de entrega solicitada no puede ser en el pasado.")
        return v

    @field_validator("franja_horaria")
    @classmethod
    def _valida_franja_horaria(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not REGEX_FRANJA_HORARIA.match(v):
            raise ValueError('La franja horaria debe tener el formato "HH:MM-HH:MM", p. ej. "10:00-12:00".')
        inicio, fin = v.split("-")
        if inicio >= fin:
            raise ValueError("La hora de inicio de la franja debe ser anterior a la hora de fin.")
        return v

    @field_validator("cupon_codigo")
    @classmethod
    def _valida_cupon_codigo(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v.upper() if v else None

    @field_validator("idempotency_key")
    @classmethod
    def _valida_idempotency_key(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if len(v) > 100:
            raise ValueError("La idempotency_key debe tener máximo 100 caracteres.")
        return v

    @model_validator(mode="after")
    def _valida_combinacion_entrega(self) -> "PedidoCrear":
        """
        `direccion_envio` es obligatoria SOLO para `domicilio` — se
        valida aquí (no con un `field_validator` normal) porque la
        regla depende de otro campo (`tipo_entrega`). Para
        `recoger_tienda` se limpia lo que haya llegado: el router es
        quien decide qué texto fijo guardar, no el cliente HTTP.
        """
        if self.tipo_entrega == TipoEntrega.domicilio:
            self.direccion_envio = validar_direccion_envio(self.direccion_envio or "")
        else:
            self.direccion_envio = None
        return self


class PedidoEstadoEntrada(BaseModel):
    """Body de PATCH /api/pedidos/{id}/estado — cambia el estado del pedido (solo admin/empleado)."""

    estado: EstadoPedido


class PedidoItemSalida(BaseModel):
    """Un ítem de pedido tal como quedó congelado al momento de la compra."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    titulo: str
    precio_unitario: float
    cantidad: int


class PedidoSalida(BaseModel):
    """Forma de un pedido en las respuestas de la API, con sus ítems incluidos."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    estado: EstadoPedido
    subtotal: float
    descuento: float
    cupon_codigo: str | None = None
    total: float
    direccion_envio: str
    telefono_contacto: str
    metodo_pago: MetodoPago
    tipo_entrega: TipoEntrega
    fecha_entrega_solicitada: date | None = None
    franja_horaria: str | None = None
    creado_en: datetime | None = None
    items: list[PedidoItemSalida] = []
