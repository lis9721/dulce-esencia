"""
Reexporta todos los modelos ORM en un solo lugar. Importar este paquete
(por ejemplo desde app/main.py) asegura que Base.metadata conozca todas
las tablas antes de usarse (create_all, Alembic, etc.).
"""

from app.models.carrito import Carrito, CarritoItem
from app.models.chatbot import Conversacion, Mensaje
from app.models.contacto import MensajeContacto
from app.models.cupon import Cupon
from app.models.factura import DetalleFactura, Factura
from app.models.pago import Pago
from app.models.pedido import Pedido, PedidoItem
from app.models.pqr import PQR
from app.models.producto import Producto
from app.models.proveedor import CategoriaProveedor, EstadoProveedor, Proveedor
from app.models.resena import Resena
from app.models.rol import Permiso, Rol, RolPermiso
from app.models.servicio import Servicio
from app.models.usuario import Usuario
from app.models.venta import DetalleVenta, Venta

__all__ = [
    "Usuario",
    "Producto",
    "Proveedor",
    "CategoriaProveedor",
    "EstadoProveedor",
    "Servicio",
    "Carrito",
    "CarritoItem",
    "Pedido",
    "PedidoItem",
    "Cupon",
    "Rol",
    "Permiso",
    "RolPermiso",
    "Resena",
    "MensajeContacto",
    "Pago",
    "Venta",
    "DetalleVenta",
    "Factura",
    "DetalleFactura",
    "PQR",
    "Conversacion",
    "Mensaje",
]
