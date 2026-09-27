"""
Esquemas Pydantic de entrada/salida para /api/servicios.

Réplica en Pydantic de backend-node/utils/validadores.js para los
campos de `servicios`. Reutiliza de schemas/producto.py los
validadores que son literalmente la misma regla en validadores.js
(validarDescripcionProducto, validarOrden, validarPrecio) en vez de
duplicarlos.
"""

import re

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.producto import (
    REGEX_SKU,
    validar_descripcion_producto,
    validar_orden,
    validar_precio,
)

REGEX_EXTENSION_IMAGEN = re.compile(r"\.(jpg|jpeg|png|webp)$", re.IGNORECASE)


def validar_nombre_servicio(valor: str) -> str:
    """Regla de validarNombreServicio() en validadores.js (servicios.nombre es VARCHAR(80))."""
    valor = (valor or "").strip()
    if not valor:
        raise ValueError("El nombre es obligatorio.")
    if len(valor) < 3:
        raise ValueError("Debe tener al menos 3 caracteres.")
    if len(valor) > 60:
        raise ValueError("Debe tener máximo 60 caracteres.")
    return valor


def validar_imagen_servicio(valor: str | None) -> str | None:
    """
    Regla de validarImagenServicio() en validadores.js:
    servicios.imagen es VARCHAR(120) NULL — a diferencia de
    productos.imagen, es OPCIONAL (no todos los servicios tienen
    imagen propia).
    """
    if valor is None:
        return valor
    valor = valor.strip()
    if not valor:
        return None
    if len(valor) > 120:
        raise ValueError("Debe tener máximo 120 caracteres.")
    if not REGEX_EXTENSION_IMAGEN.search(valor):
        raise ValueError("Debe terminar en .jpg, .jpeg, .png o .webp.")
    return valor


def validar_duracion_minutos(valor: int | None) -> int | None:
    """Regla de validarDuracionMinutos() en validadores.js: opcional, 1-1440 minutos (24h)."""
    if valor is None:
        return valor
    if valor < 1:
        raise ValueError("La duración debe ser de al menos 1 minuto.")
    if valor > 1440:
        raise ValueError("La duración no puede superar 1440 minutos (24 horas).")
    return valor


def validar_codigo_servicio(valor: str | None) -> str | None:
    """Regla de validarCodigoServicio() en validadores.js: opcional (equivalente a productos.sku)."""
    if valor is None:
        return valor
    valor = valor.strip()
    if not valor:
        return None
    if len(valor) > 20:
        raise ValueError("El código debe tener máximo 20 caracteres.")
    if not REGEX_SKU.match(valor):
        raise ValueError("El código solo puede contener letras, números, guiones y guiones bajos.")
    return valor


class ServicioCrear(BaseModel):
    """
    Body de POST /api/servicios y de PUT /api/servicios/{id} (reemplazo
    completo, igual que ProductoActualizar) — mismos campos y reglas
    que el formulario de GestionServicios.jsx.

    `nombre`, `descripcion` y `precio` son obligatorios (columnas
    NOT NULL sin default útil); `imagen`, `duracion_minutos` y
    `codigo` son opcionales porque no todo servicio los necesita (ej.
    "Envío Express" no tiene una duración cronometrada ni imagen
    propia).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str
    descripcion: str
    precio: float
    duracion_minutos: int | None = None
    imagen: str | None = None
    orden: int = 0
    codigo: str | None = None
    activo: bool = True

    @field_validator("nombre")
    @classmethod
    def _valida_nombre(cls, v: str) -> str:
        return validar_nombre_servicio(v)

    @field_validator("descripcion")
    @classmethod
    def _valida_descripcion(cls, v: str) -> str:
        return validar_descripcion_producto(v)

    @field_validator("precio")
    @classmethod
    def _valida_precio(cls, v: float) -> float:
        return validar_precio(v)

    @field_validator("duracion_minutos")
    @classmethod
    def _valida_duracion(cls, v: int | None) -> int | None:
        return validar_duracion_minutos(v)

    @field_validator("imagen")
    @classmethod
    def _valida_imagen(cls, v: str | None) -> str | None:
        return validar_imagen_servicio(v)

    @field_validator("orden")
    @classmethod
    def _valida_orden(cls, v: int) -> int:
        return validar_orden(v)

    @field_validator("codigo")
    @classmethod
    def _valida_codigo(cls, v: str | None) -> str | None:
        return validar_codigo_servicio(v)


class ServicioActualizar(ServicioCrear):
    """
    Alias explícito de ServicioCrear para PUT /api/servicios/{id}:
    mismo motivo que ProductoActualizar (el frontend siempre reenvía
    el formulario completo, no un parche).
    """


class ServicioSalida(BaseModel):
    """Forma de un servicio en las respuestas de la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str
    precio: float
    duracion_minutos: int | None = None
    imagen: str | None = None
    orden: int
    codigo: str | None = None
    activo: bool
