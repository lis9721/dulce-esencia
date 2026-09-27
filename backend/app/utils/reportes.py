"""
utils/reportes.py

Construye el reporte diario de ventas (requerimientos 4-6 del quinto
avance) en tres formas: datos planos (JSON, vía schemas/estadisticas.py
ReporteDiarioSalida), PDF (reportlab) y Excel (openpyxl).

Las tres se calculan a partir de la MISMA función `_filas_reporte`, así
que el PDF, el Excel y el JSON de la API nunca pueden mostrar números
distintos entre sí para la misma fecha.
"""

from datetime import date, datetime, time
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session, joinedload

from app.models.venta import Venta
from app.utils.factura import formatear_moneda


def _nombre_cliente(venta: Venta) -> str:
    if venta.cliente is None:
        return "—"
    return f"{venta.cliente.nombre} {venta.cliente.apellido}"


def _resumen_items(venta: Venta) -> str:
    return ", ".join(f"{item.nombre} x{item.cantidad}" for item in venta.items)


def obtener_ventas_del_dia(db: Session, fecha: date) -> list[Venta]:
    """Todas las ventas COMPLETADAS creadas entre 00:00:00 y 23:59:59 de `fecha`."""
    inicio = datetime.combine(fecha, time.min)
    fin = datetime.combine(fecha, time.max)
    return (
        db.query(Venta)
        .options(joinedload(Venta.items), joinedload(Venta.cliente))
        .filter(Venta.creado_en >= inicio, Venta.creado_en <= fin)
        .order_by(Venta.creado_en.asc())
        .all()
    )


def construir_reporte_diario(ventas: list[Venta], fecha: date) -> dict:
    """Arma el dict base (fecha, filas, total_dia, cantidad_ventas) que alimenta JSON/PDF/Excel."""
    filas = []
    total_dia = 0.0
    for venta in ventas:
        filas.append(
            {
                "venta_id": venta.id,
                "hora": venta.creado_en.strftime("%H:%M") if venta.creado_en else "—",
                "cliente": _nombre_cliente(venta),
                "items": _resumen_items(venta),
                "cantidad_total": sum(item.cantidad for item in venta.items),
                "total": float(venta.total),
                "estado": venta.estado,
            }
        )
        if venta.estado.value == "completada":
            total_dia += float(venta.total)
    return {
        "fecha": fecha,
        "filas": filas,
        "total_dia": round(total_dia, 2),
        "cantidad_ventas": len(ventas),
    }


def generar_pdf_reporte_diario(reporte: dict) -> BytesIO:
    """Reporte diario de ventas en PDF — nombre del proyecto, fecha, ventas, totales y pie de generación."""
    buffer = BytesIO()
    estilos = getSampleStyleSheet()
    estilo_pie = ParagraphStyle(
        "Pie", parent=estilos["Normal"], alignment=TA_CENTER, fontSize=9, textColor=colors.HexColor("#777777")
    )
    estilo_subtitulo = ParagraphStyle("Subtitulo", parent=estilos["Normal"], textColor=colors.HexColor("#555555"))
    estilo_total = ParagraphStyle(
        "Total", parent=estilos["Normal"], alignment=TA_RIGHT, fontSize=13, fontName="Helvetica-Bold"
    )

    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        title=f"Reporte diario de ventas — {reporte['fecha']}",
    )

    elementos = [
        Paragraph("<b>Dulce Esencia Pastelería</b>", ParagraphStyle("Titulo", parent=estilos["Title"], fontSize=18, alignment=0)),
        Paragraph("Reporte diario de ventas", estilo_subtitulo),
        Spacer(1, 10),
        Paragraph(f"Fecha del reporte: {reporte['fecha'].strftime('%d/%m/%Y')}", estilos["Normal"]),
        Paragraph(f"Ventas registradas: {reporte['cantidad_ventas']}", estilos["Normal"]),
        Spacer(1, 10),
    ]

    estilo_celda = ParagraphStyle("Celda", parent=estilos["Normal"], fontSize=9)
    filas_tabla = [["N.º venta", "Hora", "Cliente", "Productos/Servicios", "Cant.", "Total", "Estado"]]
    for fila in reporte["filas"]:
        filas_tabla.append(
            [
                str(fila["venta_id"]),
                fila["hora"],
                Paragraph(fila["cliente"], estilo_celda),
                Paragraph(fila["items"], estilo_celda),
                str(fila["cantidad_total"]),
                formatear_moneda(fila["total"]),
                fila["estado"].value,
            ]
        )

    tabla = Table(
        filas_tabla,
        colWidths=[20 * mm, 18 * mm, 45 * mm, 95 * mm, 15 * mm, 28 * mm, 25 * mm],
        repeatRows=1,
    )
    tabla.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (4, 0), (5, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#cccccc")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elementos.append(tabla)
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph(f"Total del día: {formatear_moneda(reporte['total_dia'])}", estilo_total))
    elementos.append(Spacer(1, 26))
    elementos.append(
        Paragraph(
            f"Reporte generado automáticamente por Dulce Esencia Pastelería el "
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')}.",
            estilo_pie,
        )
    )

    documento.build(elementos)
    buffer.seek(0)
    return buffer


def generar_excel_reporte_diario(reporte: dict) -> BytesIO:
    """Mismo reporte diario, en .xlsx — columnas listas para filtrar/analizar en Excel."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Reporte diario"

    encabezado_titulo = Font(bold=True, size=14)
    encabezado_columnas = Font(bold=True, color="FFFFFF")
    relleno_columnas = PatternFill(start_color="6B21A8", end_color="6B21A8", fill_type="solid")

    hoja["A1"] = "Dulce Esencia Pastelería — Reporte diario de ventas"
    hoja["A1"].font = encabezado_titulo
    hoja["A2"] = f"Fecha: {reporte['fecha'].strftime('%d/%m/%Y')}"
    hoja["A3"] = f"Ventas registradas: {reporte['cantidad_ventas']}"
    hoja["A4"] = f"Total del día: {reporte['total_dia']}"

    columnas = ["N.º venta", "Hora", "Cliente", "Productos/Servicios", "Cantidad", "Total", "Estado"]
    fila_encabezado = 6
    for indice, titulo in enumerate(columnas, start=1):
        celda = hoja.cell(row=fila_encabezado, column=indice, value=titulo)
        celda.font = encabezado_columnas
        celda.fill = relleno_columnas
        celda.alignment = Alignment(horizontal="center")

    for offset, fila in enumerate(reporte["filas"], start=1):
        hoja.cell(row=fila_encabezado + offset, column=1, value=fila["venta_id"])
        hoja.cell(row=fila_encabezado + offset, column=2, value=fila["hora"])
        hoja.cell(row=fila_encabezado + offset, column=3, value=fila["cliente"])
        hoja.cell(row=fila_encabezado + offset, column=4, value=fila["items"])
        hoja.cell(row=fila_encabezado + offset, column=5, value=fila["cantidad_total"])
        hoja.cell(row=fila_encabezado + offset, column=6, value=fila["total"])
        hoja.cell(row=fila_encabezado + offset, column=7, value=fila["estado"].value)

    anchos = [10, 8, 26, 45, 10, 14, 14]
    for indice, ancho in enumerate(anchos, start=1):
        hoja.column_dimensions[get_column_letter(indice)].width = ancho

    buffer = BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer
