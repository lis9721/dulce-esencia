"""
Router de /api/estadisticas (Quinto Avance — Dashboards, requerimientos
10-13). Todo lo que consumen los Dashboards del frontend se calcula acá
contra la base de datos real (requerimiento 15: nada de números fijos
escritos en el frontend).
"""

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import requiere_rol
from app.database import get_db
from app.models.factura import Factura
from app.models.pqr import PQR, EstadoPQR
from app.models.producto import Producto
from app.models.servicio import Servicio
from app.models.usuario import Usuario
from app.models.venta import DetalleVenta, EstadoVenta, Venta
from app.schemas.estadisticas import EstadisticasAdminSalida, EstadisticasVentasSalida, PuntoSerieVentas

router = APIRouter(prefix="/api/estadisticas", tags=["estadisticas"])


@router.get(
    "/admin",
    response_model=EstadisticasAdminSalida,
    dependencies=[Depends(requiere_rol("admin"))],
)
def estadisticas_admin(db: Session = Depends(get_db)):
    """Cards del dashboard administrativo (requerimiento 10). Ruta PROTEGIDA: admin."""
    total_facturado = (
        db.query(func.coalesce(func.sum(Factura.total), 0)).filter(Factura.estado == "emitida").scalar()
    )
    return EstadisticasAdminSalida(
        total_usuarios=db.query(func.count(Usuario.id)).scalar(),
        total_productos=db.query(func.count(Producto.id)).filter(Producto.activo.is_(True)).scalar(),
        total_servicios=db.query(func.count(Servicio.id)).filter(Servicio.activo.is_(True)).scalar(),
        total_ventas=db.query(func.count(Venta.id)).filter(Venta.estado == EstadoVenta.completada).scalar(),
        total_facturado=float(total_facturado or 0),
        pqr_pendientes=db.query(func.count(PQR.id)).filter(PQR.estado == EstadoPQR.pendiente).scalar(),
        pqr_recibidas=db.query(func.count(PQR.id)).scalar(),
    )


def _clave_periodo(fecha: datetime, agrupacion: str) -> str:
    if agrupacion == "semana":
        inicio_semana = fecha.date() - timedelta(days=fecha.weekday())
        return inicio_semana.isoformat()
    if agrupacion == "mes":
        return fecha.strftime("%Y-%m")
    return fecha.date().isoformat()


@router.get(
    "/ventas",
    response_model=EstadisticasVentasSalida,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def estadisticas_ventas(
    agrupacion: str = Query(default="dia", pattern="^(dia|semana|mes)$"),
    fecha_inicio: date | None = Query(default=None),
    fecha_fin: date | None = Query(default=None),
    producto_id: int | None = Query(default=None),
    servicio_id: int | None = Query(default=None),
    estado: EstadoVenta | None = Query(default=None),
    cliente_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Serie de ventas (por día/semana/mes) para gráfico de barras y
    lineal, con los filtros del requerimiento 13. Ruta PROTEGIDA:
    admin/empleado.
    """
    if fecha_fin is None:
        fecha_fin = date.today()
    if fecha_inicio is None:
        fecha_inicio = fecha_fin - timedelta(days=29)

    consulta = db.query(Venta).filter(
        Venta.creado_en >= datetime.combine(fecha_inicio, time.min),
        Venta.creado_en <= datetime.combine(fecha_fin, time.max),
    )
    if estado is not None:
        consulta = consulta.filter(Venta.estado == estado)
    else:
        consulta = consulta.filter(Venta.estado == EstadoVenta.completada)
    if cliente_id is not None:
        consulta = consulta.filter(Venta.cliente_id == cliente_id)
    if producto_id is not None:
        consulta = consulta.filter(
            Venta.id.in_(db.query(DetalleVenta.venta_id).filter(DetalleVenta.producto_id == producto_id))
        )
    if servicio_id is not None:
        consulta = consulta.filter(
            Venta.id.in_(db.query(DetalleVenta.venta_id).filter(DetalleVenta.servicio_id == servicio_id))
        )

    ventas = consulta.all()

    acumulado: dict[str, dict] = {}
    for venta in ventas:
        clave = _clave_periodo(venta.creado_en or datetime.now(), agrupacion)
        punto = acumulado.setdefault(clave, {"cantidad_ventas": 0, "total": 0.0})
        punto["cantidad_ventas"] += 1
        punto["total"] += float(venta.total)

    serie = [
        PuntoSerieVentas(periodo=clave, cantidad_ventas=valor["cantidad_ventas"], total=round(valor["total"], 2))
        for clave, valor in sorted(acumulado.items())
    ]

    return EstadisticasVentasSalida(
        agrupacion=agrupacion,
        serie=serie,
        total_periodo=round(sum(p.total for p in serie), 2),
        cantidad_ventas_periodo=sum(p.cantidad_ventas for p in serie),
    )
