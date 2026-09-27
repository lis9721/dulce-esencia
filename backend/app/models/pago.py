"""
Modelo ORM de la tabla `pagos`.

Sigue exactamente las mismas convenciones que app/models/pedido.py de
este mismo backend (SQLAlchemy 2.x con Mapped/mapped_column, MySQL vía
PyMySQL, PK entero autoincremental) en vez de UUID/PostgreSQL: este
backend ya corre sobre MySQL/XAMPP con sincronizar_esquema() en
app/database.py (no usa Alembic), así que el módulo de pagos se integra
ahí en vez de introducir un motor de base de datos o un sistema de
migraciones nuevo.

`pedido_id` es opcional a propósito: permite asociar un pago a un
pedido real del checkout de Dulce Esencia (app/models/pedido.py) cuando
aplica, pero el módulo también puede usarse para cobros sueltos que no
vienen de un pedido (por eso NO es NOT NULL y no se agrega una
relationship/back_populates en Pedido, para no tocar ese modelo).

Los montos se guardan en CENTAVOS (monto_centavos, BigInteger) en vez
de Numeric/float: es el mismo formato que usa la API de Wompi
(amount_in_cents) y evita errores de redondeo de punto flotante al
comparar el monto que nosotros calculamos contra el que confirma el
proveedor.
"""

import enum

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    BigInteger,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EstadoPago(str, enum.Enum):
    """
    Estados de un pago. Se usan los mismos nombres que la API de Wompi
    (PENDING, APPROVED, DECLINED, VOIDED, ERROR) más EXPIRED, que es un
    estado propio de este backend (no de Wompi) para pagos cuyo enlace
    de checkout nunca se completó dentro de un tiempo razonable.
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    VOIDED = "VOIDED"
    ERROR = "ERROR"
    EXPIRED = "EXPIRED"


# Transiciones de estado permitidas. Es la única fuente de verdad para
# cambiar `Pago.estado` — ver transicionar_estado() en
# app/services/pagos/transiciones.py. Ninguna parte de la aplicación
# debe hacer `pago.estado = ...` directamente fuera de ese módulo.
TRANSICIONES_VALIDAS: dict[EstadoPago, frozenset[EstadoPago]] = {
    EstadoPago.PENDING: frozenset(
        {EstadoPago.APPROVED, EstadoPago.DECLINED, EstadoPago.ERROR, EstadoPago.VOIDED, EstadoPago.EXPIRED}
    ),
    # Un pago APPROVED solo puede pasar a VOIDED (reembolso/anulación de
    # una transacción con tarjeta) — nunca puede "volver" a PENDING.
    EstadoPago.APPROVED: frozenset({EstadoPago.VOIDED}),
    EstadoPago.DECLINED: frozenset(),
    EstadoPago.ERROR: frozenset(),
    EstadoPago.EXPIRED: frozenset(),
    EstadoPago.VOIDED: frozenset(),
}


class Pago(Base):
    __tablename__ = "pagos"
    __table_args__ = (
        UniqueConstraint("referencia", name="uq_pagos_referencia"),
        UniqueConstraint("idempotency_key", name="uq_pagos_idempotency_key"),
        Index("ix_pagos_id_transaccion_proveedor", "id_transaccion_proveedor"),
        Index("ix_pagos_estado", "estado"),
        Index("ix_pagos_creado_en", "creado_en"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Referencia única generada por Dulce Esencia (no por el proveedor),
    # formato ESSENTIA-YYYYMMDD-XXXXXXXX — ver generar_referencia() en
    # app/services/pagos/payment_service.py.
    referencia: Mapped[str] = mapped_column(String(60), nullable=False)

    # Nombre del proveedor de pago ("wompi" por ahora). Ver
    # app/services/pagos/payment_factory.py para cómo se usa este
    # campo para elegir el PaymentProvider correcto en cada operación.
    proveedor: Mapped[str] = mapped_column(String(30), nullable=False, default="wompi")

    # ID de la transacción en el proveedor (p. ej. el `id` que devuelve
    # Wompi). Queda NULL hasta que el webhook o /sync lo confirmen por
    # primera vez, porque en el flujo de Web Checkout de Wompi la
    # transacción se crea del lado de Wompi, no en esta llamada.
    id_transaccion_proveedor: Mapped[str | None] = mapped_column(String(100), nullable=True)

    monto_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="COP")

    estado: Mapped[EstadoPago] = mapped_column(Enum(EstadoPago), nullable=False, default=EstadoPago.PENDING)

    # Se completa con `payment_method_type` de Wompi (CARD, NEQUI,
    # BANCOLOMBIA_TRANSFER, etc.) al sincronizar o recibir el webhook —
    # no se conoce al crear el pago porque el método lo escoge el
    # cliente dentro del Checkout de Wompi.
    metodo_pago: Mapped[str | None] = mapped_column(String(30), nullable=True)

    correo_cliente: Mapped[str] = mapped_column(String(120), nullable=False)
    nombre_cliente: Mapped[str | None] = mapped_column(String(120), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Vínculo opcional con un pedido real del checkout de Dulce Esencia (sin
    # relationship ni cambios en app/models/pedido.py — ver docstring
    # del módulo).
    pedido_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("pedidos.id", ondelete="SET NULL"), nullable=True)

    # Usuario autenticado que llamó a POST /api/pagos (puede ser
    # distinto de `correo_cliente`: un admin/empleado puede generar un
    # enlace de pago a nombre de otro correo). Se usa para autorizar
    # GET/POST de este pago además de `correo_cliente` — ver
    # _verificar_acceso() en app/routes/pagos.py.
    creado_por_usuario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )

    url_redireccion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url_checkout: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Última respuesta cruda relevante del proveedor (creación o
    # /sync) y último payload de webhook recibido, para auditoría y
    # depuración. Nunca deben tener credenciales/tokens (ver
    # WompiProvider, que solo guarda la data pública de la
    # transacción).
    respuesta_cruda: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    payload_webhook: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    creado_en = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    actualizado_en = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
