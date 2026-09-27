"""
Tests del módulo de pagos. Corren con:

    cd backend
    pytest tests/test_pagos.py -v

No hacen NINGUNA llamada real a Wompi: WompiProvider.create_payment()
no llama a ninguna API externa (solo firma un enlace, ver docstring de
app/services/pagos/wompi_provider.py), y las pruebas que sí requerirían
red (GET /transactions/{id} en `/sync`) mockean `WompiClient` con
`monkeypatch` — punto 18 del alcance: "Utilizar mocks para las llamadas
externas durante los tests. No hacer llamadas reales a Wompi durante
los tests unitarios."
"""

import os

import pytest

from app.integrations.wompi.firma import calcular_checksum_evento
from app.integrations.wompi.client import WompiClient
from app.models.pago import EstadoPago, Pago

EVENTS_SECRET = os.environ["WOMPI_EVENTS_SECRET"]


def _body_pago_valido(**overrides) -> dict:
    body = {
        "monto": 50000,
        "moneda": "COP",
        "correo_cliente": "cliente@example.com",
        "nombre_cliente": "Cliente Demo",
        "descripcion": "Pago de prueba",
        "proveedor": "wompi",
    }
    body.update(overrides)
    return body


def _evento_transaction_updated(*, referencia: str, estado: str, id_transaccion: str = "1234-abc", monto_centavos: int = 5000000, timestamp: int = 1530291411) -> dict:
    """Arma un evento de Wompi con un checksum VÁLIDO (calculado con el mismo algoritmo oficial)."""
    data = {
        "transaction": {
            "id": id_transaccion,
            "amount_in_cents": monto_centavos,
            "reference": referencia,
            "customer_email": "cliente@example.com",
            "currency": "COP",
            "payment_method_type": "NEQUI",
            "status": estado,
        }
    }
    propiedades = ["transaction.id", "transaction.status", "transaction.amount_in_cents"]
    checksum = calcular_checksum_evento(data=data, propiedades=propiedades, timestamp=timestamp, secreto_eventos=EVENTS_SECRET)
    return {
        "event": "transaction.updated",
        "data": data,
        "environment": "test",
        "signature": {"properties": propiedades, "checksum": checksum},
        "timestamp": timestamp,
        "sent_at": "2018-07-20T16:45:05.000Z",
    }


# ----------------------------------------------------------------------
# Crear pago
# ----------------------------------------------------------------------
class TestCrearPago:
    def test_pago_valido(self, cliente_autenticado):
        respuesta = cliente_autenticado.post("/api/pagos", json=_body_pago_valido())
        assert respuesta.status_code == 201
        datos = respuesta.json()
        assert datos["status"] == "PENDING"
        assert datos["provider"] == "wompi"
        assert datos["checkout_url"].startswith("https://checkout.wompi.co/p/")
        assert "reference" in datos and datos["reference"]

    def test_monto_invalido(self, cliente_autenticado):
        respuesta = cliente_autenticado.post("/api/pagos", json=_body_pago_valido(monto=0))
        assert respuesta.status_code == 422

    def test_moneda_invalida(self, cliente_autenticado):
        respuesta = cliente_autenticado.post("/api/pagos", json=_body_pago_valido(moneda="USD"))
        assert respuesta.status_code == 422

    def test_email_invalido(self, cliente_autenticado):
        respuesta = cliente_autenticado.post("/api/pagos", json=_body_pago_valido(correo_cliente="no-es-un-correo"))
        assert respuesta.status_code == 422

    def test_proveedor_inexistente(self, cliente_autenticado):
        respuesta = cliente_autenticado.post("/api/pagos", json=_body_pago_valido(proveedor="otro_proveedor"))
        assert respuesta.status_code == 422

    def test_error_de_wompi_credenciales_faltantes(self, cliente_autenticado, monkeypatch):
        """Si falta el secreto de integridad, WompiProvider debe fallar con un error controlado (502), no un 500 crudo."""
        from app.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "WOMPI_INTEGRITY_SECRET", "")

        respuesta = cliente_autenticado.post("/api/pagos", json=_body_pago_valido())
        assert respuesta.status_code == 502
        assert respuesta.json()["success"] is False
        assert respuesta.json()["error"]["code"] == "PAYMENT_PROVIDER_ERROR"

    def test_idempotencia_misma_llave_no_duplica_pago(self, cliente_autenticado, db_session):
        headers = {"Idempotency-Key": "prueba-idempotencia-001"}
        r1 = cliente_autenticado.post("/api/pagos", json=_body_pago_valido(), headers=headers)
        r2 = cliente_autenticado.post("/api/pagos", json=_body_pago_valido(), headers=headers)

        assert r1.status_code == 201 and r2.status_code == 201
        assert r1.json()["payment_id"] == r2.json()["payment_id"]
        assert r1.json()["reference"] == r2.json()["reference"]

        total_pagos = db_session.query(Pago).count()
        assert total_pagos == 1


# ----------------------------------------------------------------------
# Consultar pago
# ----------------------------------------------------------------------
class TestConsultarPago:
    def test_pago_existente(self, cliente_autenticado):
        creado = cliente_autenticado.post("/api/pagos", json=_body_pago_valido()).json()
        respuesta = cliente_autenticado.get(f"/api/pagos/{creado['payment_id']}")
        assert respuesta.status_code == 200
        assert respuesta.json()["referencia"] == creado["reference"]
        assert respuesta.json()["monto"] == 50000

    def test_pago_inexistente(self, cliente_autenticado):
        respuesta = cliente_autenticado.get("/api/pagos/999999")
        assert respuesta.status_code == 404
        assert respuesta.json()["error"]["code"] == "PAYMENT_NOT_FOUND"

    def test_pago_por_referencia(self, cliente_autenticado):
        creado = cliente_autenticado.post("/api/pagos", json=_body_pago_valido()).json()
        respuesta = cliente_autenticado.get(f"/api/pagos/referencia/{creado['reference']}")
        assert respuesta.status_code == 200
        assert respuesta.json()["id"] == creado["payment_id"]


# ----------------------------------------------------------------------
# Sincronizar pago (/sync) — mockea WompiClient, nunca llama a Wompi real
# ----------------------------------------------------------------------
class TestSincronizarPago:
    def test_sync_actualiza_estado_desde_wompi(self, cliente_autenticado, monkeypatch):
        creado = cliente_autenticado.post("/api/pagos", json=_body_pago_valido()).json()

        # El pago recién creado no tiene id_transaccion_proveedor
        # todavía (Web Checkout no ha llamado al webhook), así que se
        # simula que ya se conoce, para poder probar el /sync.
        from app.database import get_db
        from app.main import app

        db = next(app.dependency_overrides[get_db]())
        pago = db.get(Pago, creado["payment_id"])
        pago.id_transaccion_proveedor = "1234-abc"
        db.commit()

        def _obtener_transaccion_falso(self, id_transaccion):
            return {"data": {"id": id_transaccion, "status": "APPROVED", "payment_method_type": "NEQUI"}}

        monkeypatch.setattr(WompiClient, "obtener_transaccion", _obtener_transaccion_falso)

        respuesta = cliente_autenticado.post(f"/api/pagos/{creado['payment_id']}/sync")
        assert respuesta.status_code == 200
        assert respuesta.json()["estado"] == "APPROVED"
        assert respuesta.json()["metodo_pago"] == "NEQUI"

    def test_sync_sin_id_transaccion_no_falla(self, cliente_autenticado):
        """Si Wompi aún no ha asignado id de transacción, /sync no debe fallar: solo devuelve el estado actual."""
        creado = cliente_autenticado.post("/api/pagos", json=_body_pago_valido()).json()
        respuesta = cliente_autenticado.post(f"/api/pagos/{creado['payment_id']}/sync")
        assert respuesta.status_code == 200
        assert respuesta.json()["estado"] == "PENDING"


# ----------------------------------------------------------------------
# Webhook
# ----------------------------------------------------------------------
class TestWebhook:
    def test_webhook_valido_actualiza_el_pago(self, cliente_autenticado):
        creado = cliente_autenticado.post("/api/pagos", json=_body_pago_valido()).json()
        evento = _evento_transaction_updated(referencia=creado["reference"], estado="APPROVED")

        respuesta = cliente_autenticado.post("/api/webhooks/wompi", json=evento)
        assert respuesta.status_code == 200

        pago = cliente_autenticado.get(f"/api/pagos/{creado['payment_id']}").json()
        assert pago["estado"] == "APPROVED"
        assert pago["id_transaccion_proveedor"] == "1234-abc"

    def test_webhook_firma_invalida_se_rechaza(self, cliente_autenticado):
        creado = cliente_autenticado.post("/api/pagos", json=_body_pago_valido()).json()
        evento = _evento_transaction_updated(referencia=creado["reference"], estado="APPROVED")
        evento["signature"]["checksum"] = "checksum-adulterado"

        respuesta = cliente_autenticado.post("/api/webhooks/wompi", json=evento)
        assert respuesta.status_code == 400

        pago = cliente_autenticado.get(f"/api/pagos/{creado['payment_id']}").json()
        assert pago["estado"] == "PENDING"  # nunca se tocó el registro

    def test_webhook_pago_inexistente_responde_200_sin_crear_nada(self, cliente_autenticado, db_session):
        evento = _evento_transaction_updated(referencia="REFERENCIA-QUE-NO-EXISTE", estado="APPROVED")
        respuesta = cliente_autenticado.post("/api/webhooks/wompi", json=evento)
        # Se reconoce con 200 para que Wompi no reintente indefinidamente
        # (ver docstring de app/routes/webhooks_pagos.py) pero no debió
        # crear ni modificar ningún Pago.
        assert respuesta.status_code == 200
        assert db_session.query(Pago).count() == 0

    def test_webhook_evento_duplicado_es_idempotente(self, cliente_autenticado):
        creado = cliente_autenticado.post("/api/pagos", json=_body_pago_valido()).json()
        evento = _evento_transaction_updated(referencia=creado["reference"], estado="APPROVED")

        r1 = cliente_autenticado.post("/api/webhooks/wompi", json=evento)
        r2 = cliente_autenticado.post("/api/webhooks/wompi", json=evento)
        assert r1.status_code == 200 and r2.status_code == 200

        pago = cliente_autenticado.get(f"/api/pagos/{creado['payment_id']}").json()
        assert pago["estado"] == "APPROVED"  # sin duplicar ni romper nada al repetirse

    def test_webhook_transicion_invalida_no_rompe_y_responde_200(self, cliente_autenticado):
        """
        Un pago ya APPROVED no puede "volver" a DECLINED (ver
        TRANSICIONES_VALIDAS en app/models/pago.py). El webhook debe
        registrar la anomalía y responder 200 igualmente (no reintentos
        infinitos de Wompi por algo que nuestra máquina de estados
        nunca va a aceptar), sin tocar el estado ya guardado.
        """
        creado = cliente_autenticado.post("/api/pagos", json=_body_pago_valido()).json()
        aprobado = _evento_transaction_updated(referencia=creado["reference"], estado="APPROVED", timestamp=1111)
        cliente_autenticado.post("/api/webhooks/wompi", json=aprobado)

        declinado = _evento_transaction_updated(referencia=creado["reference"], estado="DECLINED", timestamp=2222)
        respuesta = cliente_autenticado.post("/api/webhooks/wompi", json=declinado)
        assert respuesta.status_code == 200

        pago = cliente_autenticado.get(f"/api/pagos/{creado['payment_id']}").json()
        assert pago["estado"] == "APPROVED"  # se queda como estaba, no se corrompe


# ----------------------------------------------------------------------
# Firma / checksum (unitarios, sin HTTP)
# ----------------------------------------------------------------------
class TestFirma:
    def test_firma_integridad_es_determinista(self):
        from app.integrations.wompi.firma import generar_firma_integridad

        f1 = generar_firma_integridad(referencia="ABC", monto_centavos=1000, moneda="COP", secreto_integridad="secreto")
        f2 = generar_firma_integridad(referencia="ABC", monto_centavos=1000, moneda="COP", secreto_integridad="secreto")
        assert f1 == f2
        assert len(f1) == 64  # hex de SHA256

    def test_firma_integridad_coincide_con_el_ejemplo_oficial_de_wompi(self):
        """
        Vector de prueba tomado literalmente de la documentación oficial
        (https://docs.wompi.co/docs/colombia/widget-checkout-web/,
        sección "Genera una firma de integridad"): si esta aserción
        alguna vez falla, es porque Wompi cambió el algoritmo — no un
        bug de este proyecto.
        """
        from app.integrations.wompi.firma import generar_firma_integridad

        firma = generar_firma_integridad(
            referencia="sk8-438k4-xmxm392-sn2m",
            monto_centavos=2490000,
            moneda="COP",
            secreto_integridad="prod_integrity_Z5mMke9x0k8gpErbDqwrJXMqsI6SFli6",
        )
        assert firma == "37c8407747e595535433ef8f6a811d853cd943046624a0ec04662b17bbf33bf5"

    def test_firma_integridad_con_expiration_time_inserta_la_fecha_antes_del_secreto(self):
        """
        Con `expiration-time`, la documentación oficial exige el orden
        <referencia><monto><moneda><fecha_expiracion><secreto> (la
        fecha va ANTES del secreto, no al final).
        """
        import hashlib

        from app.integrations.wompi.firma import generar_firma_integridad

        firma = generar_firma_integridad(
            referencia="sk8-438k4-xmxm392-sn2m",
            monto_centavos=2490000,
            moneda="COP",
            secreto_integridad="prod_integrity_Z5mMke9x0k8gpErbDqwrJXMqsI6SFli6",
            fecha_expiracion="2023-06-09T20:28:50.000Z",
        )
        esperado = hashlib.sha256(
            "sk8-438k4-xmxm392-sn2m2490000COP2023-06-09T20:28:50.000Zprod_integrity_Z5mMke9x0k8gpErbDqwrJXMqsI6SFli6".encode()
        ).hexdigest()
        assert firma == esperado
        # Y sin fecha_expiracion, la firma vuelve a ser la de siempre (no rompe nada ya integrado).
        firma_sin_fecha = generar_firma_integridad(
            referencia="sk8-438k4-xmxm392-sn2m",
            monto_centavos=2490000,
            moneda="COP",
            secreto_integridad="prod_integrity_Z5mMke9x0k8gpErbDqwrJXMqsI6SFli6",
        )
        assert firma_sin_fecha == "37c8407747e595535433ef8f6a811d853cd943046624a0ec04662b17bbf33bf5"
        assert firma != firma_sin_fecha

    def test_checksum_evento_sigue_el_algoritmo_oficial(self):
        """
        Verifica paso a paso el algoritmo descrito en la documentación
        oficial (concatenar los valores de `signature.properties` en
        orden + `timestamp` + el secreto, y aplicar SHA256), calculando
        el valor esperado de forma independiente con hashlib puro.
        """
        import hashlib

        data = {
            "transaction": {
                "id": "1234-1610641025-49201",
                "status": "APPROVED",
                "amount_in_cents": 4490000,
            }
        }
        timestamp = 1530291411
        secreto = "test_events_secreto_de_pruebas"

        esperado = hashlib.sha256(f"1234-1610641025-49201APPROVED44900001530291411{secreto}".encode()).hexdigest()

        checksum = calcular_checksum_evento(
            data=data,
            propiedades=["transaction.id", "transaction.status", "transaction.amount_in_cents"],
            timestamp=timestamp,
            secreto_eventos=secreto,
        )
        assert checksum == esperado
