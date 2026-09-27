"""
Helper compartido para validar un cupón y calcular su descuento.

Se usa tanto en POST /api/cupones/validar (previsualización, sin
gastar un uso) como en POST /api/pedidos (checkout real, donde sí se
incrementa `usos_actuales`) — misma regla en un solo lugar para que
nunca queden desincronizadas.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.cupon import Cupon, TipoCupon


class CuponInvalido(Exception):
    """Se lanza cuando un código de cupón no se puede aplicar, con el motivo en texto para mostrar al usuario."""

    def __init__(self, mensaje: str):
        self.mensaje = mensaje
        super().__init__(mensaje)


def buscar_cupon_aplicable(db: Session, codigo: str, subtotal: float) -> Cupon:
    """
    Busca un cupón por código y valida que sea aplicable a una compra
    de `subtotal`. Lanza CuponInvalido con un mensaje específico si
    no lo es. NO modifica `usos_actuales` — eso lo hace quien haga el
    cobro real (routes/pedidos.py), no este helper de solo lectura.
    """
    cupon = db.query(Cupon).filter(Cupon.codigo == codigo.strip().upper()).first()
    if cupon is None:
        raise CuponInvalido("El código de cupón no existe.")

    if not cupon.activo:
        raise CuponInvalido("Este cupón ya no está activo.")

    ahora = datetime.now(timezone.utc)
    valido_desde = cupon.valido_desde.replace(tzinfo=timezone.utc) if cupon.valido_desde.tzinfo is None else cupon.valido_desde
    valido_hasta = cupon.valido_hasta.replace(tzinfo=timezone.utc) if cupon.valido_hasta.tzinfo is None else cupon.valido_hasta
    if ahora < valido_desde:
        raise CuponInvalido("Este cupón todavía no es válido.")
    if ahora > valido_hasta:
        raise CuponInvalido("Este cupón ya expiró.")

    if cupon.usos_maximos is not None and cupon.usos_actuales >= cupon.usos_maximos:
        raise CuponInvalido("Este cupón ya alcanzó su límite de usos.")

    if subtotal < float(cupon.monto_minimo):
        raise CuponInvalido(f"La compra mínima para este cupón es de {float(cupon.monto_minimo):.2f}.")

    return cupon


def calcular_descuento(cupon: Cupon, subtotal: float) -> float:
    """Calcula el descuento en dinero que aplica un cupón sobre un subtotal dado, sin dejarlo superar el subtotal."""
    if cupon.tipo == TipoCupon.porcentaje:
        descuento = subtotal * (float(cupon.valor) / 100)
    else:
        descuento = float(cupon.valor)
    return round(min(descuento, subtotal), 2)
