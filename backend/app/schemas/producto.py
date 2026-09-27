"""
Esquemas Pydantic de entrada/salida para /api/productos.

Réplica en Pydantic de backend-node/utils/validadores.js (fuente de
verdad original) para los campos de `productos`. El formulario de
React (GestionProductos.jsx + frontend/src/utils/validators.js) ya
aplica una versión de estas mismas reglas, pero solo por UX — un
cliente HTTP directo (Postman, curl, un script) puede saltársela por
completo, así que estas son las que de verdad protegen la base de
datos.

Nota de auditoría frontend vs. backend (punto explícito del
enunciado: el backend debe revalidar aunque el frontend ya haya
validado): en un par de campos el frontend es deliberadamente más
laxo que el backend real —
- `validarOrden` en el frontend no valida un tope superior; aquí sí
  (2147483647, el máximo de un INT de MySQL) igual que en
  validadores.js.
- `validarImagen`/`validarImagenServicio` en el frontend no valida el
  largo máximo (120, columna VARCHAR(120)); aquí sí.
Estos esquemas siguen siempre la versión de validadores.js (backend),
no la del frontend, cuando difieren.
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.producto import FamiliaProducto
from app.schemas.proveedor import ProveedorResumen

REGEX_EXTENSION_IMAGEN = re.compile(r"\.(jpg|jpeg|png|webp)$", re.IGNORECASE)
REGEX_SKU = re.compile(r"^[A-Za-z0-9_-]+$")
REGEX_SOLO_DIGITOS = re.compile(r"^\d+$")

MAX_ENTERO_MYSQL = 2147483647
MAX_DECIMAL_10_2 = 99999999.99


def validar_titulo(valor: str) -> str:
    """Regla de validarTitulo() en validadores.js."""
    valor = (valor or "").strip()
    if not valor:
        raise ValueError("El título es obligatorio.")
    if len(valor) < 3:
        raise ValueError("Debe tener al menos 3 caracteres.")
    if len(valor) > 60:
        raise ValueError("Debe tener máximo 60 caracteres.")
    return valor


def validar_descripcion_producto(valor: str) -> str:
    """Regla de validarDescripcionProducto() en validadores.js (también reutilizada por servicios)."""
    valor = (valor or "").strip()
    if not valor:
        raise ValueError("La descripción es obligatoria.")
    if len(valor) < 10:
        raise ValueError("Debe tener al menos 10 caracteres.")
    if len(valor) > 180:
        raise ValueError("Debe tener máximo 180 caracteres.")
    return valor


def _validar_extension_imagen(valor: str) -> None:
    if not REGEX_EXTENSION_IMAGEN.search(valor):
        raise ValueError("Debe terminar en .jpg, .jpeg, .png o .webp.")


def validar_imagen(valor: str) -> str:
    """
    Regla de validarImagen() en validadores.js. productos.imagen es
    VARCHAR(120) y OBLIGATORIA (a diferencia de servicios.imagen).
    """
    valor = (valor or "").strip()
    if not valor:
        raise ValueError("El nombre del archivo de imagen es obligatorio.")
    if len(valor) > 120:
        raise ValueError("Debe tener máximo 120 caracteres.")
    _validar_extension_imagen(valor)
    return valor


def validar_orden(valor: int | None) -> int | None:
    """
    Regla de validarOrden() en validadores.js: opcional (el backend lo
    pone en 0 por defecto); si se envía, entero no negativo hasta el
    máximo de un INT de MySQL.
    """
    if valor is None:
        return valor
    if valor < 0 or valor > MAX_ENTERO_MYSQL:
        raise ValueError("El orden debe ser un número entero válido.")
    return valor


def validar_precio(valor: float) -> float:
    """
    Regla de validarPrecio() en validadores.js: obligatorio, no
    negativo, dentro del rango de un DECIMAL(10,2).
    """
    if valor < 0:
        raise ValueError("El precio no puede ser negativo.")
    if valor > MAX_DECIMAL_10_2:
        raise ValueError("El precio es demasiado grande.")
    return valor


def validar_stock(valor: int | None) -> int | None:
    """Regla de validarStock() en validadores.js: opcional (default 0), entero no negativo."""
    if valor is None:
        return valor
    if valor < 0 or valor > MAX_ENTERO_MYSQL:
        raise ValueError("El stock debe ser un número entero no negativo.")
    return valor


def validar_sku(valor: str | None) -> str | None:
    """Regla de validarSku() en validadores.js: opcional."""
    if valor is None:
        return valor
    valor = valor.strip()
    if not valor:
        return None
    if len(valor) > 20:
        raise ValueError("El SKU debe tener máximo 20 caracteres.")
    if not REGEX_SKU.match(valor):
        raise ValueError("El SKU solo puede contener letras, números, guiones y guiones bajos.")
    return valor


def validar_peso_g(valor: int | None) -> int | None:
    """Regla de validarPesoG() en validators.js: opcional, 1-10000 g."""
    if valor is None:
        return valor
    if valor < 1:
        raise ValueError("El peso debe ser mayor a 0 g.")
    if valor > 10000:
        raise ValueError("El peso es demasiado grande para un producto de pastelería (máximo 10000 g).")
    return valor


class ProductoCrear(BaseModel):
    """
    Body de POST /api/productos y (al ser PUT un reemplazo completo,
    no un parche) también de PUT /api/productos/{id} — mismos campos y
    reglas que el formulario de GestionProductos.jsx.

    `precio`, `familia` (y `titulo`, `descripcion`, `imagen`, heredados
    de las columnas NOT NULL sin default útil) son obligatorios;
    `stock` es obligatorio a nivel de esquema pero con default 0 igual
    que la columna, así que un cliente puede omitirlo; `orden`, `sku` y
    `peso_g` son opcionales.
    """

    model_config = ConfigDict(str_strip_whitespace=True, json_schema_extra={"examples": [{"titulo": "Torta de Chocolate Intenso", "descripcion": "Bizcocho húmedo de cacao con ganache de chocolate semiamargo.", "imagen": "torta-chocolate.jpg", "precio": 85000, "stock": 12, "sku": "TOR-001", "familia": "tortas", "peso_g": 1200, "activo": True}]})

    titulo: str
    descripcion: str
    imagen: str
    orden: int = 0
    precio: float
    stock: int = 0
    sku: str | None = None
    familia: FamiliaProducto
    peso_g: int | None = None
    activo: bool = True
    # Proveedor que surte el producto (módulo de proveedores). Es
    # opcional porque el catálogo ya existía antes que esa tabla: los
    # productos cargados antes siguen siendo válidos sin proveedor.
    proveedor_id: int | None = Field(
        default=None, ge=1, description="Id del proveedor que surte este producto."
    )

    @field_validator("titulo")
    @classmethod
    def _valida_titulo(cls, v: str) -> str:
        return validar_titulo(v)

    @field_validator("descripcion")
    @classmethod
    def _valida_descripcion(cls, v: str) -> str:
        return validar_descripcion_producto(v)

    @field_validator("imagen")
    @classmethod
    def _valida_imagen(cls, v: str) -> str:
        return validar_imagen(v)

    @field_validator("orden")
    @classmethod
    def _valida_orden(cls, v: int) -> int:
        return validar_orden(v)

    @field_validator("precio")
    @classmethod
    def _valida_precio(cls, v: float) -> float:
        return validar_precio(v)

    @field_validator("stock")
    @classmethod
    def _valida_stock(cls, v: int) -> int:
        return validar_stock(v)

    @field_validator("sku")
    @classmethod
    def _valida_sku(cls, v: str | None) -> str | None:
        return validar_sku(v)

    @field_validator("peso_g")
    @classmethod
    def _valida_peso(cls, v: int | None) -> int | None:
        return validar_peso_g(v)


class ProductoActualizar(ProductoCrear):
    """
    Alias explícito de ProductoCrear para PUT /api/productos/{id}: el
    frontend precarga el formulario con el producto completo y siempre
    reenvía todos los campos (no es una actualización parcial tipo
    PATCH), así que las mismas reglas de obligatoriedad aplican.
    """


class ProductoSalida(BaseModel):
    """Forma de un producto en las respuestas de la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descripcion: str
    imagen: str
    orden: int
    precio: float
    stock: int
    sku: str | None = None
    familia: FamiliaProducto
    peso_g: int | None = None
    activo: bool
    calificacion_promedio: float = 0
    total_resenas: int = 0
    proveedor_id: int | None = None
    # Esquema RESUMEN para la relación (criterio 53): el detalle del
    # producto muestra quién lo surte sin arrastrar las condiciones
    # comerciales del proveedor (cupo, plazo de pago) a una respuesta
    # que también consume la tienda pública.
    proveedor: ProveedorResumen | None = None
