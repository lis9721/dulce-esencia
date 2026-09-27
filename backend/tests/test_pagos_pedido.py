"""
Integración PASARELA DE PAGOS ↔ PEDIDOS.

Antes de este módulo, un pago aprobado NO cambiaba el estado del pedido y
el monto lo mandaba el navegador (se podía "pagar" $1 por un pedido de
$500.000). Estas pruebas fijan el comportamiento correcto:
  - el monto debe coincidir con el total del pedido (validado en el servidor);
  - solo se paga un pedido propio y pendiente;
  - pago APROBADO  -> pedido `pagado` (idempotente); RECHAZADO -> sigue `pendiente`;
  - /sync con el `?id=` de Wompi solo se acepta si la transacción es de ESTE pago.
Sin llamadas reales a Wompi (se mockea WompiClient).
"""

import pytest

from app.integrations.wompi.client import WompiClient
from app.models.pago import Pago
from app.models.pedido import EstadoPedido, Pedido
from tests.test_pagos import _body_pago_valido, _evento_transaction_updated

TOTAL = 189000.0


@pytest.fixture()
def pedido(db_session):
    """Pedido pendiente del usuario simulado por `cliente_autenticado` (id=1)."""
    p = Pedido(
        usuario_id=1, subtotal=TOTAL, descuento=0, total=TOTAL,
        direccion_envio="Calle 1 # 2-3", telefono_contacto="3001234567", metodo_pago="tarjeta",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _crear(cliente, pedido, **cambios):
    body = _body_pago_valido(monto=TOTAL, pedido_id=pedido.id, url_redireccion="http://localhost:5173/pago/resultado")
    body.update(cambios)
    return cliente.post("/api/pagos", json=body)


class TestValidacionDelPedido:
    def test_monto_correcto_crea_el_pago_y_pone_la_referencia_en_la_url_de_retorno(self, cliente_autenticado, pedido, db_session):
        r = _crear(cliente_autenticado, pedido)
        assert r.status_code == 201, r.text
        pago = db_session.get(Pago, r.json()["payment_id"])
        assert pago.pedido_id == pedido.id
        assert f"referencia={r.json()['reference']}" in pago.url_redireccion
        assert "redirect-url=" in r.json()["checkout_url"]

    def test_monto_distinto_al_total_del_pedido_se_rechaza(self, cliente_autenticado, pedido, db_session):
        r = _crear(cliente_autenticado, pedido, monto=1)
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "PAYMENT_VALIDATION_ERROR"
        assert db_session.query(Pago).count() == 0  # ni se registró el pago

    def test_pedido_inexistente_404(self, cliente_autenticado, pedido):
        r = cliente_autenticado.post("/api/pagos", json=_body_pago_valido(monto=TOTAL, pedido_id=987654))
        assert r.status_code == 404

    def test_pedido_de_otro_usuario_404_sin_confirmar_que_existe(self, cliente_autenticado, db_session):
        ajeno = Pedido(usuario_id=99, subtotal=TOTAL, descuento=0, total=TOTAL, direccion_envio="x" * 10, telefono_contacto="3000000000", metodo_pago="tarjeta")
        db_session.add(ajeno)
        db_session.commit()
        r = cliente_autenticado.post("/api/pagos", json=_body_pago_valido(monto=TOTAL, pedido_id=ajeno.id))
        assert r.status_code == 404

    def test_pedido_ya_pagado_no_se_cobra_otra_vez(self, cliente_autenticado, pedido, db_session):
        pedido.estado = EstadoPedido.pagado
        db_session.commit()
        assert _crear(cliente_autenticado, pedido).status_code == 422

    def test_pago_sin_pedido_sigue_funcionando(self, cliente_autenticado):
        assert cliente_autenticado.post("/api/pagos", json=_body_pago_valido()).status_code == 201


class TestEfectoSobreElPedido:
    def _estado(self, db_session, pedido):
        db_session.expire_all()
        return db_session.get(Pedido, pedido.id).estado

    def test_webhook_aprobado_marca_el_pedido_como_pagado(self, cliente_autenticado, pedido, db_session):
        ref = _crear(cliente_autenticado, pedido).json()["reference"]
        assert self._estado(db_session, pedido) == EstadoPedido.pendiente

        r = cliente_autenticado.post("/api/webhooks/wompi", json=_evento_transaction_updated(referencia=ref, estado="APPROVED", monto_centavos=int(TOTAL * 100)))

        assert r.status_code == 200
        assert self._estado(db_session, pedido) == EstadoPedido.pagado

    def test_evento_duplicado_no_altera_un_pedido_que_ya_avanzo(self, cliente_autenticado, pedido, db_session):
        ref = _crear(cliente_autenticado, pedido).json()["reference"]
        evento = _evento_transaction_updated(referencia=ref, estado="APPROVED")
        cliente_autenticado.post("/api/webhooks/wompi", json=evento)
        pedido_bd = db_session.get(Pedido, pedido.id)
        pedido_bd.estado = EstadoPedido.enviado  # el empleado ya lo despachó
        db_session.commit()

        cliente_autenticado.post("/api/webhooks/wompi", json=evento)  # Wompi reintenta

        assert self._estado(db_session, pedido) == EstadoPedido.enviado  # no retrocede a "pagado"

    def test_pago_rechazado_deja_el_pedido_pendiente_para_reintentar(self, cliente_autenticado, pedido, db_session):
        ref = _crear(cliente_autenticado, pedido).json()["reference"]
        cliente_autenticado.post("/api/webhooks/wompi", json=_evento_transaction_updated(referencia=ref, estado="DECLINED"))
        assert self._estado(db_session, pedido) == EstadoPedido.pendiente


class TestSyncConIdDeWompi:
    def _respuesta_wompi(self, *, referencia, monto_centavos, estado="APPROVED"):
        def _obtener(self, id_transaccion):
            return {"data": {"id": id_transaccion, "status": estado, "reference": referencia, "amount_in_cents": monto_centavos, "payment_method_type": "CARD"}}

        return _obtener

    def test_sync_con_transaccion_verificada_aprueba_el_pago_y_el_pedido(self, cliente_autenticado, pedido, db_session, monkeypatch):
        creado = _crear(cliente_autenticado, pedido).json()
        monkeypatch.setattr(WompiClient, "obtener_transaccion", self._respuesta_wompi(referencia=creado["reference"], monto_centavos=int(TOTAL * 100)))

        r = cliente_autenticado.post(f"/api/pagos/{creado['payment_id']}/sync?transaction_id=tx-123")

        assert r.status_code == 200 and r.json()["estado"] == "APPROVED"
        assert r.json()["id_transaccion_proveedor"] == "tx-123"
        db_session.expire_all()
        assert db_session.get(Pedido, pedido.id).estado == EstadoPedido.pagado

    def test_no_se_puede_adoptar_una_transaccion_de_otra_referencia(self, cliente_autenticado, pedido, db_session, monkeypatch):
        """Ataque: usar el id de una transacción APROBADA ajena para marcar mi pago como pagado."""
        creado = _crear(cliente_autenticado, pedido).json()
        monkeypatch.setattr(WompiClient, "obtener_transaccion", self._respuesta_wompi(referencia="ESSENTIA-OTRA-REF", monto_centavos=int(TOTAL * 100)))

        r = cliente_autenticado.post(f"/api/pagos/{creado['payment_id']}/sync?transaction_id=tx-ajena")

        assert r.status_code == 422
        db_session.expire_all()
        assert db_session.get(Pedido, pedido.id).estado == EstadoPedido.pendiente

    def test_no_se_adopta_una_transaccion_de_menor_monto(self, cliente_autenticado, pedido, monkeypatch):
        creado = _crear(cliente_autenticado, pedido).json()
        monkeypatch.setattr(WompiClient, "obtener_transaccion", self._respuesta_wompi(referencia=creado["reference"], monto_centavos=100))
        assert cliente_autenticado.post(f"/api/pagos/{creado['payment_id']}/sync?transaction_id=tx-1").status_code == 422
