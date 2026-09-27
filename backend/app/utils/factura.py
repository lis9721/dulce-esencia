"""
utils/factura.py

Equivalente en Python a backend-node/utils/factura.js — genera el PDF
de la factura de un pedido ya confirmado, al vuelo, a partir de un
`Pedido` de SQLAlchemy (con `pedido.items` ya cargados) y del `cliente`
dueño del pedido (`pedido.usuario`). No se guarda nada en disco: cada
descarga se recalcula desde la BD en el momento, así que si el pedido
cambia de estado (ej. se cancela) la factura reflejará eso la próxima
vez que se pida.

Usa reportlab (agregado a requirements.txt) en vez de pdfkit (la
librería que usa Node), porque pdfkit es específico de Node/JS y no
tiene equivalente directo en Python — pero el CONTENIDO y el layout son
los mismos: encabezado, datos del cliente, tabla de items, totales y
pie de página.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Mismas etiquetas que ETIQUETAS_METODO_PAGO en factura.js.
ETIQUETAS_METODO_PAGO = {
    "tarjeta": "Tarjeta",
    "transferencia": "Transferencia",
    "contraentrega": "Pago contraentrega",
}


def _valor_enum(valor):
    """Los Enum de SQLAlchemy (estado, tipo_documento, metodo_pago) ya
    son subclases de `str`, pero `.value` da el texto plano sin el
    prefijo de la clase al interpolarlo en un f-string."""
    return valor.value if hasattr(valor, "value") else valor


def formatear_moneda(valor) -> str:
    """
    Formatea un monto en pesos colombianos, sin decimales — mismo
    criterio que Intl.NumberFormat("es-CO", {style: "currency",
    currency: "COP", maximumFractionDigits: 0}) en Node: separador de
    miles con punto y sin centavos (la plata del proyecto es
    DECIMAL(10,2), pero se muestra como COP entero en toda la app).
    """
    numero = round(float(valor or 0))
    con_puntos = f"{numero:,}".replace(",", ".")
    return f"$ {con_puntos}"


def generar_pdf_factura(pedido, cliente) -> BytesIO:
    """
    Arma el PDF de la factura de `pedido` (cabecera + `pedido.items` +
    subtotal/descuento/total) y de los datos del `cliente` dueño del
    pedido, y lo devuelve como un buffer de bytes en memoria, listo
    para envolver en una StreamingResponse desde la ruta que llama a
    esta función.
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
        title=f"Factura pedido #{pedido.id}",
    )

    elementos = []

    # --- Encabezado ---
    elementos.append(Paragraph("<b>Dulce Esencia Pastelería</b>", ParagraphStyle("Titulo", parent=estilos["Title"], fontSize=20, alignment=0)))
    elementos.append(Paragraph("Factura de venta", estilo_subtitulo))
    elementos.append(Spacer(1, 14))

    numero_factura = str(pedido.id).zfill(6)
    fecha = pedido.creado_en.strftime("%d/%m/%Y %H:%M") if pedido.creado_en else "—"
    elementos.append(Paragraph(f"Factura N.º: {numero_factura}", estilos["Normal"]))
    elementos.append(Paragraph(f"Fecha: {fecha}", estilos["Normal"]))
    elementos.append(Paragraph(f"Estado del pedido: {_valor_enum(pedido.estado)}", estilos["Normal"]))
    elementos.append(Spacer(1, 10))

    # --- Datos del cliente ---
    elementos.append(Paragraph("<u>Datos del cliente</u>", estilos["Heading3"]))
    elementos.append(Paragraph(f"Nombre: {cliente.nombre} {cliente.apellido}", estilos["Normal"]))
    elementos.append(
        Paragraph(f"Documento: {_valor_enum(cliente.tipo_documento)} {cliente.numero_documento}", estilos["Normal"])
    )
    elementos.append(Paragraph(f"Correo: {cliente.correo}", estilos["Normal"]))
    elementos.append(Paragraph(f"Dirección de envío: {pedido.direccion_envio}", estilos["Normal"]))
    elementos.append(Paragraph(f"Teléfono de contacto: {pedido.telefono_contacto}", estilos["Normal"]))
    elementos.append(Spacer(1, 10))

    # --- Tabla de items ---
    elementos.append(Paragraph("<u>Detalle del pedido</u>", estilos["Heading3"]))
    elementos.append(Spacer(1, 6))

    estilo_celda = ParagraphStyle("Celda", parent=estilos["Normal"], fontSize=10)
    filas = [["Producto", "Precio unit.", "Cant.", "Subtotal"]]
    for item in pedido.items:
        subtotal_item = float(item.precio_unitario) * item.cantidad
        filas.append(
            [
                Paragraph(item.titulo, estilo_celda),
                formatear_moneda(item.precio_unitario),
                str(item.cantidad),
                formatear_moneda(subtotal_item),
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

    # --- Totales ---
    elementos.append(Paragraph(f"Subtotal: {formatear_moneda(pedido.subtotal)}", estilo_derecha))
    if float(pedido.descuento or 0) > 0:
        etiqueta_cupon = f" (cupón {pedido.cupon_codigo})" if pedido.cupon_codigo else ""
        elementos.append(
            Paragraph(f"Descuento{etiqueta_cupon}: -{formatear_moneda(pedido.descuento)}", estilo_derecha)
        )
    elementos.append(Paragraph(f"Total: {formatear_moneda(pedido.total)}", estilo_total))
    elementos.append(Spacer(1, 8))

    etiqueta_metodo = ETIQUETAS_METODO_PAGO.get(_valor_enum(pedido.metodo_pago), _valor_enum(pedido.metodo_pago))
    elementos.append(Paragraph(f"Método de pago: {etiqueta_metodo}", estilos["Normal"]))

    elementos.append(Spacer(1, 34))
    elementos.append(
        Paragraph("Este documento es una factura generada automáticamente por Dulce Esencia Pastelería.", estilo_pie)
    )

    documento.build(elementos)
    buffer.seek(0)
    return buffer
