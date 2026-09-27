"""
Esquemas Pydantic de entrada/salida para /api/carrito.

El carrito nunca se "crea" explícitamente desde el cliente HTTP: se
obtiene o se crea de forma perezosa (lazy) la primera vez que un
usuario autenticado agrega un ítem — por eso aquí solo hay esquemas
para los ítems (agregar/actualizar cantidad) y para la salida
completa del carrito (lo que ve el usuario en su vista de carrito).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Mismo tope que products.stock (columna INT), para no dejar pasar un
# valor absurdo desde el body antes siquiera de tocar la base de datos.
MAX_CANTIDAD_POR_ITEM = 1000


class CarritoItemEntrada(BaseModel):
    """Body de POST /api/carrito/items (agregar un producto al carrito)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    producto_id: int = Field(gt=0)
    cantidad: int = Field(default=1, ge=1, le=MAX_CANTIDAD_POR_ITEM)


class CarritoItemActualizar(BaseModel):
    """Body de PUT /api/carrito/items/{producto_id} (fijar una cantidad exacta)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    cantidad: int = Field(ge=1, le=MAX_CANTIDAD_POR_ITEM)


class CarritoFusionarEntrada(BaseModel):
    """
    Body de POST /api/carrito/fusionar: fusiona el carrito de invitado
    (guardado en localStorage antes de iniciar sesión) con el que el
    usuario ya tuviera en la BD. Reutiliza CarritoItemEntrada para cada
    ítem — misma forma que agregar un producto individual, solo que
    aquí llegan varios de una vez.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    items: list[CarritoItemEntrada]


class CarritoItemSalida(BaseModel):
    """Un ítem del carrito, ya enriquecido con los datos actuales del producto."""

    model_config = ConfigDict(from_attributes=True)

    producto_id: int
    titulo: str
    imagen: str
    precio: float
    stock_disponible: int
    cantidad: int
    subtotal: float
    agregado_en: datetime | None = None


class CarritoSalida(BaseModel):
    """
    Forma completa del carrito en las respuestas de la API: los
    ítems más el total ya calculado, para que el frontend no tenga
    que sumar nada por su cuenta.
    """

    items: list[CarritoItemSalida]
    total: float
    cantidad_items: int
