"""
Capa Repository de `pagos`: toda la aplicación accede a la tabla
`pagos` a través de esta clase — Router → Service → Repository →
Database (punto 3 del alcance del módulo). Ningún router ni servicio
debe hacer `db.query(Pago)` directamente.
"""

from sqlalchemy.orm import Session

from app.models.pago import Pago


class PagoRepository:
    def __init__(self, db: Session):
        self._db = db

    def obtener_por_id(self, pago_id: int) -> Pago | None:
        return self._db.get(Pago, pago_id)

    def obtener_por_referencia(self, referencia: str) -> Pago | None:
        return self._db.query(Pago).filter(Pago.referencia == referencia).first()

    def obtener_por_idempotency_key(self, idempotency_key: str) -> Pago | None:
        return self._db.query(Pago).filter(Pago.idempotency_key == idempotency_key).first()

    def crear(self, pago: Pago) -> Pago:
        self._db.add(pago)
        self._db.flush()  # asigna pago.id sin cerrar la transacción todavía
        return pago

    def guardar(self, pago: Pago) -> Pago:
        self._db.commit()
        self._db.refresh(pago)
        return pago
