"""
PaymentService: orquesta Repository ↔ PaymentProvider. Es la única
capa que conoce ambas cosas a la vez — los routers (app/routes/pagos.py,
webhooks_pagos.py) solo hablan con PaymentService, nunca con
PagoRepository ni con un PaymentProvider directamente (punto 3 del
alcance: Router → Service → Repository → Database, y
Service → Payment Provider → API externa).
"""

import logging
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.orm import Session

from app.config import Settings
from app.exceptions.pagos import PagoNoEncontradoException, PagoValidacionException, WebhookValidacionException
from app.models.pago import EstadoPago, Pago
from app.models.pedido import EstadoPedido, Pedido
from app.models.usuario import Usuario
from app.repositories.pago_repository import PagoRepository
from app.schemas.pago import PagoCrear
from app.services.pagos.payment_factory import obtener_proveedor
from app.services.pagos.transiciones import transicionar_estado
from app.services.pagos.wompi_provider import generar_referencia

logger = logging.getLogger("app.services.pagos")


def _con_referencia(url: str | None, referencia: str) -> str | None:
    """
    Agrega `?referencia=<REF>` a la URL a la que Wompi devolverá al
    cliente. Wompi solo añade el id de su transacción (`?id=...`); con
    la referencia en la URL, la página de resultado del frontend puede
    consultar NUESTRO pago (GET /api/pagos/referencia/{referencia}) sin
    depender de nada guardado en el navegador.
    """
    if not url:
        return url
    partes = urlparse(url)
    consulta = dict(parse_qsl(partes.query, keep_blank_values=True))
    consulta["referencia"] = referencia
    return urlunparse(partes._replace(query=urlencode(consulta)))



class PaymentService:
    def __init__(self, db: Session, settings: Settings):
        self._db = db
        self._settings = settings
        self._repo = PagoRepository(db)

    # ------------------------------------------------------------------
    # Creación
    # ------------------------------------------------------------------
    def _validar_pedido(self, datos: PagoCrear, usuario: Usuario | None) -> None:
        """
        Si el pago dice pagar un pedido, se valida en el SERVIDOR (el
        navegador nunca es fuente de verdad del dinero):
          1. el pedido existe;
          2. es del usuario que paga (o quien paga es admin/empleado);
          3. sigue en estado `pendiente` (no se cobra dos veces);
          4. el monto pedido coincide EXACTAMENTE con `pedido.total`.
        Sin el punto 4, un cliente podría pagar $1 por un pedido de $500.000.
        """
        if datos.pedido_id is None:
            return

        pedido = self._db.get(Pedido, datos.pedido_id)
        if pedido is None:
            raise PagoNoEncontradoException(f"No existe el pedido {datos.pedido_id}.")

        es_staff = usuario is not None and usuario.rol in ("admin", "empleado")
        es_dueno = usuario is not None and pedido.usuario_id == usuario.id
        if usuario is not None and not (es_dueno or es_staff):
            # Misma respuesta que "no existe" para no confirmar ids ajenos.
            raise PagoNoEncontradoException(f"No existe el pedido {datos.pedido_id}.")

        if pedido.estado != EstadoPedido.pendiente:
            raise PagoValidacionException(
                f"El pedido {pedido.id} está en estado '{pedido.estado.value}': solo se puede pagar un pedido pendiente."
            )

        if round(datos.monto * 100) != round(float(pedido.total) * 100):
            raise PagoValidacionException(
                f"El monto no coincide con el total del pedido ({float(pedido.total):.2f} COP)."
            )

    def crear_pago(
        self,
        datos: PagoCrear,
        idempotency_key: str | None,
        creado_por_usuario_id: int | None = None,
        usuario: Usuario | None = None,
    ) -> Pago:
        """
        Crea un pago. Si `idempotency_key` viene y ya existe un pago
        previo con esa misma llave, se devuelve ESE pago tal cual en
        vez de crear uno nuevo (punto 12 del alcance: idempotencia de
        creación) — respaldado además por el UniqueConstraint de la
        columna en la base de datos.
        """
        if idempotency_key:
            pago_existente = self._repo.obtener_por_idempotency_key(idempotency_key)
            if pago_existente is not None:
                return pago_existente

        self._validar_pedido(datos, usuario)

        monto_centavos = round(datos.monto * 100)
        referencia = generar_referencia()
        url_redireccion = _con_referencia(datos.url_redireccion, referencia)

        pago = Pago(
            referencia=referencia,
            proveedor=datos.proveedor,
            monto_centavos=monto_centavos,
            moneda=datos.moneda,
            estado=EstadoPago.PENDING,
            correo_cliente=datos.correo_cliente,
            nombre_cliente=datos.nombre_cliente,
            descripcion=datos.descripcion,
            pedido_id=datos.pedido_id,
            url_redireccion=url_redireccion,
            idempotency_key=idempotency_key,
            creado_por_usuario_id=creado_por_usuario_id,
        )
        self._repo.crear(pago)

        proveedor = obtener_proveedor(datos.proveedor, self._settings)
        resultado = proveedor.create_payment(
            referencia=referencia,
            monto_centavos=monto_centavos,
            moneda=datos.moneda,
            correo_cliente=datos.correo_cliente,
            nombre_cliente=datos.nombre_cliente,
            url_redireccion=url_redireccion,
        )

        pago.url_checkout = resultado.url_checkout
        pago.id_transaccion_proveedor = resultado.id_transaccion_proveedor
        pago.respuesta_cruda = resultado.respuesta_cruda

        return self._repo.guardar(pago)

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------
    def obtener_pago(self, pago_id: int) -> Pago:
        pago = self._repo.obtener_por_id(pago_id)
        if pago is None:
            raise PagoNoEncontradoException(f"No existe un pago con id {pago_id}.")
        return pago

    def obtener_pago_por_referencia(self, referencia: str) -> Pago:
        pago = self._repo.obtener_por_referencia(referencia)
        if pago is None:
            raise PagoNoEncontradoException(f"No existe un pago con referencia '{referencia}'.")
        return pago

    # ------------------------------------------------------------------
    # Sincronización directa con el proveedor (punto 10)
    # ------------------------------------------------------------------
    def sincronizar_pago(self, pago_id: int, id_transaccion: str | None = None) -> Pago:
        """
        Consulta a Wompi el estado real y actualiza el pago local.

        `id_transaccion` (opcional) es el `?id=` que Wompi agrega a la URL
        de retorno. Sirve cuando el webhook todavía no llegó (típico en
        desarrollo local, donde Wompi no puede llamar a `localhost`).
        NUNCA se confía en él a ciegas: se pide la transacción a Wompi
        (fuente de verdad) y solo se adopta si su `reference` y su monto
        coinciden con ESTE pago. Así nadie puede "prestarse" una
        transacción aprobada ajena para marcar su pago como pagado.
        """
        pago = self.obtener_pago(pago_id)

        id_a_consultar = pago.id_transaccion_proveedor or id_transaccion
        if not id_a_consultar:
            # Todavía no sabemos el id de Wompi para este pago (el
            # cliente no ha completado el Web Checkout, o el webhook
            # aún no llegó) — no hay nada que consultar todavía.
            return pago

        proveedor = obtener_proveedor(pago.proveedor, self._settings)
        resultado = proveedor.get_payment(id_a_consultar)

        if not pago.id_transaccion_proveedor:
            datos_wompi = (resultado.respuesta_cruda or {}).get("data", {})
            if (
                datos_wompi.get("reference") != pago.referencia
                or datos_wompi.get("amount_in_cents") != pago.monto_centavos
            ):
                raise PagoValidacionException("La transacción indicada no corresponde a este pago.")
            pago.id_transaccion_proveedor = resultado.id_transaccion_proveedor or id_a_consultar

        pago.estado = transicionar_estado(pago.estado, resultado.estado)
        pago.metodo_pago = resultado.metodo_pago or pago.metodo_pago
        pago.respuesta_cruda = resultado.respuesta_cruda
        self._aplicar_efectos_del_estado(pago)
        return self._repo.guardar(pago)

    def _aplicar_efectos_del_estado(self, pago: Pago) -> None:
        """
        Efecto de negocio de un pago aprobado: el pedido asociado pasa de
        `pendiente` a `pagado`. Es idempotente (si el pedido ya no está
        pendiente, no hace nada), así que un webhook duplicado o un
        /sync repetido no lo alteran. Un pago rechazado NO cancela el
        pedido: queda `pendiente` para que el cliente reintente.
        """
        if pago.estado != EstadoPago.APPROVED or pago.pedido_id is None:
            return
        pedido = self._db.get(Pedido, pago.pedido_id)
        if pedido is not None and pedido.estado == EstadoPedido.pendiente:
            pedido.estado = EstadoPedido.pagado
            logger.info("pedido_pagado", extra={"pedido_id": pedido.id, "referencia": pago.referencia})

    # ------------------------------------------------------------------
    # Webhook (punto 11)
    # ------------------------------------------------------------------
    def procesar_webhook(self, proveedor_nombre: str, payload: dict) -> None:
        proveedor = obtener_proveedor(proveedor_nombre, self._settings)

        # Lanza WebhookValidacionException si la firma/checksum no
        # coincide — el router responde 400 y NUNCA se llega a tocar
        # la base de datos con datos no verificados.
        if not proveedor.validate_webhook(payload):
            raise WebhookValidacionException("La firma del evento no es válida.")

        evento = proveedor.extraer_evento_transaccion(payload)
        if evento is None:
            # Evento reconocido pero no relacionado con una transacción
            # (p. ej. nequi_token.updated) — se acepta sin más acción.
            return

        if not evento.referencia:
            raise PagoValidacionException("El evento de Wompi no trae una referencia de transacción.")

        pago = self._repo.obtener_por_referencia(evento.referencia)
        if pago is None:
            # No es un error de firma ni de formato: es un evento de
            # una transacción que esta base de datos no conoce. Se
            # registra para revisión manual pero NO se lanza una
            # excepción de validación (ver webhooks_pagos.py: esto se
            # reconoce con 200 para que Wompi no reintente indefinidamente
            # un evento que nunca vamos a poder resolver).
            raise PagoNoEncontradoException(f"No existe un pago con referencia '{evento.referencia}'.")

        if pago.id_transaccion_proveedor and pago.id_transaccion_proveedor != evento.id_transaccion_proveedor:
            logger.warning(
                "wompi_webhook_id_transaccion_distinto",
                extra={"referencia": pago.referencia, "id_guardado": pago.id_transaccion_proveedor, "id_evento": evento.id_transaccion_proveedor},
            )
        pago.id_transaccion_proveedor = pago.id_transaccion_proveedor or evento.id_transaccion_proveedor

        if pago.estado == evento.estado:
            # Evento duplicado (Wompi reintenta hasta 3 veces si no
            # recibe 200) — no-op idempotente, no se genera ni se
            # altera nada (punto 11: idempotencia del webhook).
            pago.payload_webhook = payload
            self._repo.guardar(pago)
            return

        pago.estado = transicionar_estado(pago.estado, evento.estado)
        pago.metodo_pago = evento.metodo_pago or pago.metodo_pago
        pago.payload_webhook = payload
        self._aplicar_efectos_del_estado(pago)
        self._repo.guardar(pago)
