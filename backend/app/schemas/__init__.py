"""
Reexporta los esquemas Pydantic en un solo lugar, igual que
app/models/__init__.py hace con los modelos ORM.
"""

from app.schemas.auth import (
    LoginEntrada,
    ReenviarVerificacionEntrada,
    RecuperarEntrada,
    RestablecerEntrada,
    TokenSalida,
    VerificarCorreoEntrada,
)
from app.schemas.carrito import (
    CarritoFusionarEntrada,
    CarritoItemActualizar,
    CarritoItemEntrada,
    CarritoItemSalida,
    CarritoSalida,
)
from app.schemas.contacto import ContactoCrear, ContactoSalida
from app.schemas.cupon import (
    CuponActualizar,
    CuponCrear,
    CuponEstadoEntrada,
    CuponSalida,
    CuponValidarEntrada,
    CuponValidarSalida,
)
from app.schemas.chatbot import (
    ChatbotMensajeEntrada,
    ChatbotMensajeSalida,
    ConversacionSalida,
    MensajeSalida,
)
from app.schemas.estadisticas import (
    EstadisticasAdminSalida,
    EstadisticasVentasSalida,
    PuntoSerieVentas,
    ReporteDiarioSalida,
    ReporteVentaFila,
)
from app.schemas.factura import (
    DetalleFacturaSalida,
    FacturaCrear,
    FacturaFiltros,
    FacturaSalida,
)
from app.schemas.pqr import PQRActualizar, PQRCrear, PQRSalida
from app.schemas.pedido import PedidoCrear, PedidoEstadoEntrada, PedidoItemSalida, PedidoSalida
from app.schemas.producto import ProductoActualizar, ProductoCrear, ProductoSalida
from app.schemas.proveedor import (
    ProveedorActualizar,
    ProveedorCrear,
    ProveedorReemplazar,
    ProveedorResumen,
    ProveedorSalida,
    ProveedoresPagina,
    SuspensionCrear,
)
from app.schemas.rol import PermisoSalida, RolSalida
from app.schemas.servicio import ServicioActualizar, ServicioCrear, ServicioSalida
from app.schemas.usuario import (
    CambiarPasswordEntrada,
    RolCambioEntrada,
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioEstadoEntrada,
    UsuarioSalida,
)
from app.schemas.venta import (
    DetalleVentaSalida,
    VentaCrear,
    VentaEstadoEntrada,
    VentaFiltros,
    VentaItemEntrada,
    VentaSalida,
)

__all__ = [
    "UsuarioCrear",
    "UsuarioSalida",
    "UsuarioActualizar",
    "UsuarioEstadoEntrada",
    "CambiarPasswordEntrada",
    "RolCambioEntrada",
    "LoginEntrada",
    "TokenSalida",
    "RecuperarEntrada",
    "RestablecerEntrada",
    "ReenviarVerificacionEntrada",
    "VerificarCorreoEntrada",
    "ProductoCrear",
    "ProductoActualizar",
    "ProductoSalida",
    "ProveedorCrear",
    "ProveedorReemplazar",
    "ProveedorActualizar",
    "ProveedorSalida",
    "ProveedorResumen",
    "ProveedoresPagina",
    "SuspensionCrear",
    "ServicioCrear",
    "ServicioActualizar",
    "ServicioSalida",
    "CarritoItemEntrada",
    "CarritoItemActualizar",
    "CarritoItemSalida",
    "CarritoSalida",
    "CarritoFusionarEntrada",
    "PedidoCrear",
    "PedidoEstadoEntrada",
    "PedidoItemSalida",
    "PedidoSalida",
    "CuponCrear",
    "CuponActualizar",
    "CuponEstadoEntrada",
    "CuponSalida",
    "CuponValidarEntrada",
    "CuponValidarSalida",
    "ContactoCrear",
    "ContactoSalida",
    "RolSalida",
    "PermisoSalida",
    "VentaCrear",
    "VentaItemEntrada",
    "VentaEstadoEntrada",
    "VentaSalida",
    "DetalleVentaSalida",
    "VentaFiltros",
    "FacturaCrear",
    "FacturaSalida",
    "DetalleFacturaSalida",
    "FacturaFiltros",
    "PQRCrear",
    "PQRActualizar",
    "PQRSalida",
    "ChatbotMensajeEntrada",
    "ChatbotMensajeSalida",
    "ConversacionSalida",
    "MensajeSalida",
    "EstadisticasAdminSalida",
    "EstadisticasVentasSalida",
    "PuntoSerieVentas",
    "ReporteDiarioSalida",
    "ReporteVentaFila",
]
