"""
Router de /api/reportes (Quinto Avance — requerimientos 4, 5 y 6).

GET /api/reportes/ventas/diario           -> JSON
GET /api/reportes/ventas/diario/pdf       -> PDF
GET /api/reportes/ventas/diario/excel     -> Excel (.xlsx)

Las tres rutas comparten exactamente los mismos datos (ver
app/utils/reportes.py) para la fecha pedida, así que nunca pueden
mostrar totales distintos entre sí.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import requiere_rol
from app.database import get_db
from app.schemas.estadisticas import ReporteDiarioSalida
from app.utils.reportes import (
    construir_reporte_diario,
    generar_excel_reporte_diario,
    generar_pdf_reporte_diario,
    obtener_ventas_del_dia,
)

router = APIRouter(prefix="/api/reportes", tags=["reportes"], dependencies=[Depends(requiere_rol("admin", "empleado"))])


@router.get("/ventas/diario", response_model=ReporteDiarioSalida)
def reporte_diario_ventas(fecha: date = Query(default_factory=date.today), db: Session = Depends(get_db)):
    """Reporte diario de ventas en JSON. Ruta PROTEGIDA: admin/empleado."""
    ventas = obtener_ventas_del_dia(db, fecha)
    return construir_reporte_diario(ventas, fecha)


@router.get("/ventas/diario/pdf")
def reporte_diario_ventas_pdf(fecha: date = Query(default_factory=date.today), db: Session = Depends(get_db)):
    """El mismo reporte diario, exportado en PDF."""
    ventas = obtener_ventas_del_dia(db, fecha)
    reporte = construir_reporte_diario(ventas, fecha)
    buffer = generar_pdf_reporte_diario(reporte)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="reporte-ventas-{fecha}.pdf"'},
    )


@router.get("/ventas/diario/excel")
def reporte_diario_ventas_excel(fecha: date = Query(default_factory=date.today), db: Session = Depends(get_db)):
    """El mismo reporte diario, exportado en Excel (.xlsx)."""
    ventas = obtener_ventas_del_dia(db, fecha)
    reporte = construir_reporte_diario(ventas, fecha)
    buffer = generar_excel_reporte_diario(reporte)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="reporte-ventas-{fecha}.xlsx"'},
    )
