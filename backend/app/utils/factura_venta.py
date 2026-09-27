"""
utils/factura_venta.py

Genera el PDF de una Factura (app/models/factura.py), generada a partir
de una Venta del módulo de gestión comercial. Mismo estilo/layout que
app/utils/factura.py (la factura de un Pedido del sitio web) para que
las dos se vean consistentes, pero trabajando sobre Factura/
DetalleFactura en vez de Pedido/PedidoItem.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.utils.factura import formatear_moneda


def generar_pdf_factura_venta(factura, cliente) -> BytesIO:
    """
    Arma el PDF de `factura` (cabecera + `factura.items` + totales) y
    de los datos del `cliente`, y lo devuelve como buffer en memoria.
    """
    buffer = BytesIO()
    estilos = getSampleStyleSheet()
    estilo_derecha = ParagraphStyle("Derecha", parent=estilos["Normal"], alignment=TA_RIGHT)
    estilo_total = ParagraphStyle("Total", parent=estilo_derecha, fontSize=13, fontName="Helvetica-Bold")
    estilo_pie = ParagraphStyle(
        "Pie", parent=estilos["Normal"], alignment=TA_CENTER, fontSize=9, textColor=colors.HexColor("#777777")
    )
    estilo_subtitulo = ParagraphStyle("Subtitulo", parent=estilos["Normal"], textColor=colors.HexColor("#555555"))

    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=f"Factura {factura.numero}",
    )

    elementos = []
    elementos.append(
        Paragraph("<b>Dulce Esencia Pastelería</b>", ParagraphStyle("Titulo", parent=estilos["Title"], fontSize=20, alignment=0))
    )
    elementos.append(Paragraph("Factura de venta", estilo_subtitulo))
    elementos.append(Spacer(1, 14))

    fecha = factura.creado_en.strftime("%d/%m/%Y %H:%M") if factura.creado_en else "—"
    elementos.append(Paragraph(f"Factura N.º: {factura.numero}", estilos["Normal"]))
    elementos.append(Paragraph(f"Fecha: {fecha}", estilos["Normal"]))
    elementos.append(Paragraph(f"Estado: {factura.estado.value}", estilos["Normal"]))
    elementos.append(Spacer(1, 10))

    elementos.append(Paragraph("<u>Datos del cliente</u>", estilos["Heading3"]))
    elementos.append(Paragraph(f"Nombre: {cliente.nombre} {cliente.apellido}", estilos["Normal"]))
    elementos.append(
        Paragraph(f"Documento: {cliente.tipo_documento.value} {cliente.numero_documento}", estilos["Normal"])
    )
    elementos.append(Paragraph(f"Correo: {cliente.correo}", estilos["Normal"]))
    elementos.append(Spacer(1, 10))

    elementos.append(Paragraph("<u>Detalle de la venta</u>", estilos["Heading3"]))
    elementos.append(Spacer(1, 6))

    estilo_celda = ParagraphStyle("Celda", parent=estilos["Normal"], fontSize=10)
    filas = [["Producto / Servicio", "Precio unit.", "Cant.", "Subtotal"]]
    for item in factura.items:
        filas.append(
            [
                Paragraph(item.nombre, estilo_celda),
                formatear_moneda(item.precio_unitario),
                str(item.cantidad),
                formatear_moneda(item.subtotal),
            ]
        )

    tabla = Table(filas, colWidths=[75 * mm, 35 * mm, 20 * mm, 35 * mm], repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#cccccc")),
                ("LINEBELOW", (0, -1), (-1, -1), 0.75, colors.HexColor("#cccccc")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elementos.append(tabla)
    elementos.append(Spacer(1, 10))

    elementos.append(Paragraph(f"Subtotal: {formatear_moneda(factura.subtotal)}", estilo_derecha))
    if float(factura.impuestos or 0) > 0:
        elementos.append(Paragraph(f"Impuestos: {formatear_moneda(factura.impuestos)}", estilo_derecha))
    elementos.append(Paragraph(f"Total: {formatear_moneda(factura.total)}", estilo_total))

    elementos.append(Spacer(1, 34))
    elementos.append(
        Paragraph("Este documento es una factura generada automáticamente por Dulce Esencia Pastelería.", estilo_pie)
    )

    documento.build(elementos)
    buffer.seek(0)
    return buffer
