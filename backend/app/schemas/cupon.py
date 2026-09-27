"""
Esquemas Pydantic de entrada/salida para /api/cupones.
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.cupon import TipoCupon

REGEX_CODIGO_CUPON = re.compile(r"^[A-Z0-9_-]+$")

MAX_DECIMAL_10_2 = 99999999.99
MAX_ENTERO_MYSQL = 2147483647


def validar_codigo_cupon(valor: str) -> str:
    """cupones.codigo es VARCHAR(30); se normaliza siempre a mayúsculas para evitar duplicados por casing."""
    valor = (valor or "").strip().upper()
    if not valor:
        raise ValueError("El código del cupón es obligatorio.")
    if len(valor) < 3:
        raise ValueError("Debe tener al menos 3 caracteres.")
    if len(valor) > 30:
        raise ValueError("Debe tener máximo 30 caracteres.")
    if not REGEX_CODIGO_CUPON.match(valor):
        raise ValueError("Solo puede contener letras, números, guiones y guiones bajos.")
    return valor


class CuponCrear(BaseModel):
    """
    Body de POST /api/cupones y de PUT /api/cupones/{id} (reemplazo
    completo, mismo criterio que ProductoActualizar/ServicioActualizar).

    Si `tipo` es "porcentaje", `valor` se limita a 0-100 (no tiene
    sentido un descuento de "150%"); si es "monto_fijo", `valor` es
    cualquier monto no negativo dentro del rango de un DECIMAL(10,2).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    codigo: str
    tipo: TipoCupon
    valor: float
    monto_minimo: float = 0
    usos_maximos: int | None = None
    valido_desde: datetime
    valido_hasta: datetime
    activo: bool = True

    @field_validator("codigo")
    @classmethod
    def _valida_codigo(cls, v: str) -> str:
        return validar_codigo_cupon(v)

    @field_validator("monto_minimo")
    @classmethod
    def _valida_monto_minimo(cls, v: float) -> float:
        if v < 0 or v > MAX_DECIMAL_10_2:
            raise ValueError("El monto mínimo debe ser un valor no negativo válido.")
        return v

    @field_validator("usos_maximos")
    @classmethod
    def _valida_usos_maximos(cls, v: int | None) -> int | None:
        if v is None:
            return v
        if v < 1 or v > MAX_ENTERO_MYSQL:
            raise ValueError("Los usos máximos deben ser un entero positivo válido.")
        return v

    @model_validator(mode="after")
    def _valida_valor_y_vigencia(self) -> "CuponCrear":
        if self.tipo == TipoCupon.porcentaje:
            if self.valor <= 0 or self.valor > 100:
                raise ValueError("Un cupón de porcentaje debe tener un valor entre 0 y 100.")
        else:
            if self.valor <= 0 or self.valor > MAX_DECIMAL_10_2:
                raise ValueError("El valor del cupón debe ser un monto positivo válido.")

        if self.valido_hasta < self.valido_desde:
            raise ValueError("La fecha de vencimiento no puede ser anterior a la fecha de inicio.")

        return self


class CuponActualizar(CuponCrear):
    """Alias explícito de CuponCrear para PUT /api/cupones/{id}."""


class CuponEstadoEntrada(BaseModel):
    """Body de PATCH /api/cupones/{id}/estado — activa o desactiva un cupón sin tocar el resto de sus datos."""

    activo: bool


class CuponSalida(BaseModel):
    """Forma de un cupón en las respuestas de la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    tipo: TipoCupon
    valor: float
    monto_minimo: float
    usos_maximos: int | None = None
    usos_actuales: int
    valido_desde: datetime
    valido_hasta: datetime
    activo: bool
    creado_en: datetime | None = None


class CuponValidarEntrada(BaseModel):
    """
    Body de POST /api/cupones/validar: permite previsualizar el
    descuento de un cupón (ej. en el resumen del carrito) ANTES de
    confirmar el pedido, sin gastar uno de sus usos.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    codigo: str
    subtotal: float

    @field_validator("codigo")
    @classmethod
    def _valida_codigo(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if not v:
            raise ValueError("El código del cupón es obligatorio.")
        return v

    @field_validator("subtotal")
    @classmethod
    def _valida_subtotal(cls, v: float) -> float:
        if v < 0:
            raise ValueError("El subtotal no puede ser negativo.")
        return v


class CuponValidarSalida(BaseModel):
    """Respuesta de POST /api/cupones/validar."""

    valido: bool
    codigo: str
    descuento: float
    total: float
    mensaje: str
