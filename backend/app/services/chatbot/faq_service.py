"""
services/chatbot/faq_service.py

Chatbot GRATUITO y LOCAL (sin API de pago, sin internet): responde por
reglas de palabras clave y consulta el catálogo real de la base de datos
(productos y servicios activos). Se usa en dos casos:

  1. No hay OPENAI_API_KEY configurada  -> el chatbot sigue funcionando.
  2. El proveedor de IA falla (sin saldo, sin red, límite excedido).

Nunca inventa precios, stock ni políticas: los precios salen de la BD y
todo lo demás se limita a lo que la aplicación realmente hace (carrito,
checkout, métodos de pago, cupones, PQR). Si no entiende, lo dice y
ofrece las opciones disponibles, o deriva a una PQR.

Es un enfoque de "sistema experto" sencillo: normalizar el texto ->
detectar la intención -> armar la respuesta. Se puede combinar con un
proveedor de IA gratuito (Groq, Gemini, OpenRouter, Ollama) apuntando
OPENAI_BASE_URL — ver docs/CHATBOT-GRATUITO.md.
"""

import re
import unicodedata

from sqlalchemy.orm import Session

from app.models.producto import FamiliaProducto, Producto
from app.models.servicio import Servicio
from app.utils.busqueda import CARACTER_ESCAPE, escapar_like

MAX_RESULTADOS = 3

MENU = (
    "Puedo ayudarte con: productos del catálogo (por ejemplo «tortas», «cupcakes» o «cuánto cuesta…»), "
    "servicios, métodos de pago, cupones, seguimiento de pedidos y PQR."
)


def _normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para que «envío» y «envio» coincidan."""
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")


def _tokens(texto: str) -> list[str]:
    return re.findall(r"\w+", texto)


def _contiene(texto: str, palabras: tuple[str, ...]) -> bool:
    """
    ¿Aparece alguna de las palabras clave? Las de una sola palabra se
    comparan como PREFIJO de un token (así «pagar» reconoce «pagarle»
    pero «pse» ya no se activa dentro de «repsol»); las frases con
    espacio se buscan tal cual.
    """
    tokens = _tokens(texto)
    for palabra in palabras:
        if " " in palabra:
            if palabra in texto:
                return True
        elif any(t.startswith(palabra) for t in tokens):
            return True
    return False


def _precio(valor) -> str:
    return f"${float(valor):,.0f} COP".replace(",", ".")


def _buscar_productos(db: Session, texto: str) -> list[Producto]:
    consulta = db.query(Producto).filter(Producto.activo.is_(True))

    # Categoría por prefijo de 5 letras: «torta», «tortas» y «tort…» → tortas;
    # «galleta» → galletas; «postre» → postres; «panadería» → panaderia.
    tokens = _tokens(texto)
    familia = next((f for f in FamiliaProducto if any(t.startswith(f.value[:5]) for t in tokens)), None)
    if familia is not None:
        return consulta.filter(Producto.familia == familia).order_by(Producto.orden.asc()).limit(MAX_RESULTADOS).all()

    # Palabras "de contenido" (>3 letras) buscadas contra el título.
    for palabra in (p for p in tokens if len(p) > 3):
        coincidencias = (
            consulta.filter(Producto.titulo.ilike(f"%{escapar_like(palabra)}%", escape=CARACTER_ESCAPE))
            .order_by(Producto.orden.asc())
            .limit(MAX_RESULTADOS)
            .all()
        )
        if coincidencias:
            return coincidencias

    if _contiene(texto, ("producto", "catalogo")):
        return consulta.order_by(Producto.orden.asc()).limit(MAX_RESULTADOS).all()

    return []


def _listar_productos(productos: list[Producto]) -> str:
    lineas = [f"• {p.titulo} — {_precio(p.precio)}" + ("" if p.stock > 0 else " (agotado)") for p in productos]
    return "\n".join(lineas)


PALABRAS_PQR = ("queja", "reclamo", "pqr", "sugerencia", "peticion", "denuncia")


def es_intencion_pqr(texto_normalizado: str) -> bool:
    """
    ¿El mensaje (ya normalizado con `_normalizar`) suena a petición, queja,
    reclamo o sugerencia? La usa `responder_localmente` para su propia
    respuesta y también `routes/chatbot.py` para decidir si el chatbot debe
    escalar la conversación creando una PQR real (ver `models/chatbot.py`).
    """
    return _contiene(texto_normalizado, PALABRAS_PQR)


def tipo_pqr_sugerido(texto_normalizado: str) -> str:
    """Adivina el `TipoPQR` (valor string) más probable a partir de las palabras clave del mensaje."""
    if _contiene(texto_normalizado, ("sugerencia",)):
        return "sugerencia"
    if _contiene(texto_normalizado, ("reclamo",)):
        return "reclamo"
    if _contiene(texto_normalizado, ("peticion", "solicitud")):
        return "peticion"
    return "queja"


def responder_localmente(db: Session, mensaje: str) -> str:
    """Devuelve una respuesta en español para `mensaje` sin usar ninguna API externa."""
    texto = _normalizar(mensaje)

    if es_intencion_pqr(texto):
        return (
            "Lamento el inconveniente. Puedes registrar tu petición, queja, reclamo o sugerencia en tu panel, "
            "sección «PQR» (necesitas iniciar sesión). Un asesor la revisa y te responde; recibirás un correo "
            "con el número de radicado."
        )

    if _contiene(texto, ("pago", "pagar", "tarjeta", "transferencia", "contraentrega", "wompi", "nequi", "pse")):
        return (
            "Al confirmar tu pedido puedes elegir: tarjeta (pago seguro en línea con Wompi, sin que tus datos "
            "de tarjeta pasen por nuestros servidores), transferencia o pago contraentrega."
        )

    if _contiene(texto, ("cupon", "descuento", "promo", "codigo")):
        return (
            "Si tienes un cupón, aplícalo en tu carrito antes de confirmar: el sistema valida su vigencia y "
            "calcula el descuento sobre el subtotal."
        )

    if _contiene(texto, ("pedido", "envio", "entrega", "domicilio", "rastrear", "seguimiento", "factura")):
        return (
            "Después de comprar puedes ver tus pedidos en tu panel, «Mis pedidos». Su estado pasa por "
            "pendiente → pagado → enviado → entregado, y desde allí descargas tu factura en PDF."
        )

    if _contiene(texto, ("servicio", "asesoria", "personaliz", "cita", "encargo", "evento")):
        servicios = db.query(Servicio).filter(Servicio.activo.is_(True)).order_by(Servicio.orden.asc()).limit(MAX_RESULTADOS).all()
        if servicios:
            lineas = "\n".join(f"• {s.nombre} — {_precio(s.precio)}" for s in servicios)
            return f"Estos son algunos de nuestros servicios:\n{lineas}\nEl detalle está en la sección Servicios del sitio."
        return "Puedes ver nuestros servicios en la sección Servicios del sitio."

    if _contiene(texto, ("contacto", "telefono", "whatsapp", "horario", "direccion", "ubicacion")):
        return (
            "Puedes escribirnos por el botón de WhatsApp del sitio o desde la página Contacto. "
            "Para horarios y sedes, un asesor te confirma el dato exacto."
        )

    hay_intencion_catalogo = _contiene(
        texto,
        (
            "torta", "pastel", "postre", "cupcake", "galleta", "panader", "croissant", "dulce",
            "producto", "precio", "cuesta", "vale", "catalogo", "recomiend", "comprar",
        ),
    )
    productos = _buscar_productos(db, texto)
    if productos:
        return f"Encontré estas opciones del catálogo:\n{_listar_productos(productos)}\nPuedes verlas y agregarlas al carrito en la Tienda."
    if hay_intencion_catalogo:
        familias = ", ".join(f.value for f in FamiliaProducto)
        return (
            "No encontré un producto con ese nombre. Puedes explorar por categoría "
            f"({familias}) o ver todo el catálogo en la Tienda."
        )

    if _contiene(texto, ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey")):
        return f"¡Hola! Soy el asistente virtual de Dulce Esencia Pastelería. {MENU}"

    if _contiene(texto, ("gracias", "chao", "adios", "hasta luego")):
        return "¡Con gusto! Si necesitas algo más, aquí estaré."

    return f"No estoy seguro de haber entendido. {MENU} Si prefieres, registra una PQR y un asesor te atenderá."
