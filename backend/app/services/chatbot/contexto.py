"""
services/chatbot/contexto.py

Datos REALES de la tienda que se le entregan a la IA en cada turno para
que responda con información verdadera (precios, stock, servicios y, si
el visitante inició sesión, el estado de SUS pedidos) en vez de
depender solo de lo que "sabe" el modelo.

Reglas de seguridad:
  - Los pedidos que se incluyen son SIEMPRE los del usuario autenticado
    (filtro por usuario_id); un visitante sin sesión nunca recibe datos
    de pedidos.
  - Solo productos y servicios ACTIVOS.
  - Todo va como texto plano de "datos": el prompt de sistema le indica
    al modelo que no siga instrucciones que aparezcan dentro de ellos.
"""

from sqlalchemy.orm import Session

from app.models.pedido import Pedido
from app.models.producto import Producto
from app.models.servicio import Servicio
from app.models.usuario import Usuario

MAX_PRODUCTOS_CONTEXTO = 40
MAX_SERVICIOS_CONTEXTO = 15
MAX_PEDIDOS_CONTEXTO = 5

ETIQUETA_ESTADO = {
    "pendiente": "pendiente de pago",
    "pagado": "pagado, en preparación",
    "enviado": "enviado, en camino",
    "entregado": "entregado",
    "cancelado": "cancelado",
}


def precio_cop(valor) -> str:
    return f"${float(valor):,.0f} COP".replace(",", ".")


def _texto_estado(pedido: Pedido) -> str:
    valor = pedido.estado.value if hasattr(pedido.estado, "value") else str(pedido.estado)
    return ETIQUETA_ESTADO.get(valor, valor)


def pedidos_recientes(db: Session, usuario: Usuario, limite: int = MAX_PEDIDOS_CONTEXTO) -> list[Pedido]:
    """Últimos pedidos del usuario (más nuevo primero). Nunca de otra persona."""
    return (
        db.query(Pedido)
        .filter(Pedido.usuario_id == usuario.id)
        .order_by(Pedido.id.desc())
        .limit(limite)
        .all()
    )


def linea_pedido(pedido: Pedido) -> str:
    fecha = ""
    if pedido.creado_en is not None:
        fecha = f" · {pedido.creado_en:%d/%m/%Y}"
    entrega = ""
    if pedido.fecha_entrega_solicitada is not None:
        entrega = f" · entrega pedida para {pedido.fecha_entrega_solicitada:%d/%m/%Y}"
        if pedido.franja_horaria:
            entrega += f" ({pedido.franja_horaria})"
    return f"Pedido #{pedido.id}{fecha} · {_texto_estado(pedido)} · total {precio_cop(pedido.total)}{entrega}"


def construir_contexto(db: Session, usuario: Usuario | None) -> str:
    """Texto con el catálogo, los servicios y (si hay sesión) los pedidos del usuario."""
    partes: list[str] = []

    productos = (
        db.query(Producto)
        .filter(Producto.activo.is_(True))
        .order_by(Producto.orden.asc(), Producto.id.asc())
        .limit(MAX_PRODUCTOS_CONTEXTO)
        .all()
    )
    if productos:
        lineas = []
        for p in productos:
            stock = "agotado" if p.stock <= 0 else f"stock {p.stock}"
            familia = p.familia.value if hasattr(p.familia, "value") else str(p.familia)
            lineas.append(f"- {p.titulo} | {familia} | {precio_cop(p.precio)} | {stock} | {p.descripcion[:90]}")
        partes.append("CATÁLOGO (productos activos):\n" + "\n".join(lineas))

    servicios = (
        db.query(Servicio)
        .filter(Servicio.activo.is_(True))
        .order_by(Servicio.orden.asc(), Servicio.id.asc())
        .limit(MAX_SERVICIOS_CONTEXTO)
        .all()
    )
    if servicios:
        partes.append(
            "SERVICIOS:\n" + "\n".join(f"- {s.nombre} | {precio_cop(s.precio)} | {s.descripcion[:90]}" for s in servicios)
        )

    if usuario is not None:
        nombre = (usuario.nombre or "").strip() or "cliente"
        pedidos = pedidos_recientes(db, usuario)
        if pedidos:
            partes.append(
                f"CLIENTE CON SESIÓN: {nombre}. Sus últimos pedidos:\n" + "\n".join(f"- {linea_pedido(p)}" for p in pedidos)
            )
        else:
            partes.append(f"CLIENTE CON SESIÓN: {nombre}. Todavía no tiene pedidos.")
    else:
        partes.append("VISITANTE SIN SESIÓN: no tienes datos de pedidos; para consultarlos debe iniciar sesión.")

    return "\n\n".join(partes)
