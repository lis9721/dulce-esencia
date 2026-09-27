"""Esquemas Pydantic de salida para /api/estadisticas (Dashboards)."""

from datetime import date

from pydantic import BaseModel

from app.models.venta import EstadoVenta


class EstadisticasAdminSalida(BaseModel):
    """GET /api/estadisticas/admin — Cards del dashboard administrativo."""

    total_usuarios: int
    total_productos: int
    total_servicios: int
    total_ventas: int
    total_facturado: float
    pqr_pendientes: int
    pqr_recibidas: int


class PuntoSerieVentas(BaseModel):
    """Un punto (día/semana/mes) de la serie de ventas para gráfico de barras/líneas."""

    periodo: str
    cantidad_ventas: int
    total: float


class EstadisticasVentasSalida(BaseModel):
    """GET /api/estadisticas/ventas — Dashboard de ventas (gráficos + indicadores)."""

    agrupacion: str
    serie: list[PuntoSerieVentas]
    total_periodo: float
    cantidad_ventas_periodo: int


class ReporteVentaFila(BaseModel):
    """Una fila del reporte diario de ventas."""

    venta_id: int
    hora: str
    cliente: str
    items: str
    cantidad_total: int
    total: float
    estado: EstadoVenta


class ReporteDiarioSalida(BaseModel):
    fecha: date
    filas: list[ReporteVentaFila]
    total_dia: float
    cantidad_ventas: int
