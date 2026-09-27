"""
Router de /api/pagos.

Sigue el mismo patrón de autorización que app/routes/pedidos.py: el
usuario autenticado solo puede ver SUS propios pagos — dueño si
`creado_por_usuario_id` coincide con su id (el pago lo generó él,
sin importar a qué correo se lo esté cobrando) o si `correo_cliente`
coincide con su propio correo (le están cobrando a él). Admin/empleado
pueden ver cualquier pago, igual que en pedidos.
"""

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.database import get_db
from app.exceptions.pagos import PagoNoEncontradoException
from app.models.pago import Pago
from app.models.usuario import Usuario
from app.schemas.pago import PagoCrear, PagoCrearRespuesta, PagoSalida
from app.services.pagos.payment_service import PaymentService

router = APIRouter(prefix="/api/pagos", tags=["pagos"])


def get_payment_service(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> PaymentService:
    return PaymentService(db, settings)


def _verificar_acceso(pago: Pago, usuario: Usuario) -> None:
    if usuario.rol in ("admin", "empleado"):
        return
    es_dueno = pago.creado_por_usuario_id == usuario.id
    es_destinatario = pago.correo_cliente.lower() == usuario.correo.lower()
    if not (es_dueno or es_destinatario):
        # Se responde igual que "no encontrado" (no 403) para no
        # confirmarle a un usuario que una referencia/id de pago ajeno
        # sí existe.
        raise PagoNoEncontradoException("No existe un pago con esos datos.")


@router.post("", response_model=PagoCrearRespuesta, status_code=status.HTTP_201_CREATED)
def crear_pago(
    datos: PagoCrear,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    servicio: PaymentService = Depends(get_payment_service),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Crea un pago y genera el enlace de Checkout de Wompi (Sandbox).
    Ruta PROTEGIDA (cualquier usuario logueado). Envía opcionalmente el
    header `Idempotency-Key` para evitar crear dos pagos si el cliente
    reintenta la misma petición (doble clic, reintento de red).
    """
    pago = servicio.crear_pago(datos, idempotency_key, creado_por_usuario_id=usuario.id, usuario=usuario)
    return PagoCrearRespuesta(
        payment_id=pago.id,
        reference=pago.referencia,
        status=pago.estado,
        checkout_url=pago.url_checkout,
        provider=pago.proveedor,
    )


@router.get("/{pago_id}", response_model=PagoSalida)
def obtener_pago(
    pago_id: int,
    servicio: PaymentService = Depends(get_payment_service),
    usuario: Usuario = Depends(get_current_user),
):
    """Detalle de un pago. Nunca incluye llaves/API keys del proveedor."""
    pago = servicio.obtener_pago(pago_id)
    _verificar_acceso(pago, usuario)
    return PagoSalida.desde_modelo(pago)


@router.get("/referencia/{referencia}", response_model=PagoSalida)
def obtener_pago_por_referencia(
    referencia: str,
    servicio: PaymentService = Depends(get_payment_service),
    usuario: Usuario = Depends(get_current_user),
):
    pago = servicio.obtener_pago_por_referencia(referencia)
    _verificar_acceso(pago, usuario)
    return PagoSalida.desde_modelo(pago)


@router.post("/{pago_id}/sync", response_model=PagoSalida)
def sincronizar_pago(
    pago_id: int,
    transaction_id: str | None = Query(
        default=None,
        max_length=100,
        description="`id` que Wompi agrega a la URL de retorno. Se verifica contra Wompi antes de usarlo.",
    ),
    servicio: PaymentService = Depends(get_payment_service),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Consulta directamente a Wompi el estado actual de la transacción y
    actualiza el registro local. Si Wompi todavía no conoce esta
    transacción (el pago sigue PENDING sin `id_transaccion_proveedor`),
    devuelve el pago sin cambios.
    """
    pago = servicio.obtener_pago(pago_id)
    _verificar_acceso(pago, usuario)
    pago = servicio.sincronizar_pago(pago_id, transaction_id)
    return PagoSalida.desde_modelo(pago)
