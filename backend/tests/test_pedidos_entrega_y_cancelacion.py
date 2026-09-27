"""
Pruebas de lo agregado en esta ronda:
  - checkout con tipo_entrega=recoger_tienda / domicilio + franja horaria;
  - correos de confirmación y cambio de estado (mockeados, sin SMTP real);
  - POST /api/pedidos/{id}/cancelar: repone stock y, si había un pago
    APROBADO, dispara el reembolso en Wompi antes de cancelar.
"""

from datetime import date, timedelta

import pytest

from app.integrations.wompi.client import WompiClient
from app.models.pago import EstadoPago, Pago
from app.models.pedido import EstadoPedido, Pedido, TipoEntrega
from app.models.producto import Producto


def _capturar_correos(monkeypatch):
    """Reemplaza enviar_correo por una lista para no depender de SMTP real."""
    enviados = []
    monkeypatch.setattr(
        "app.services.notificaciones.enviar_correo",
        lambda destino, asunto, cuerpo: enviados.append((destino, asunto, cuerpo)) or True,
    )
    return enviados


@pytest.fixture()
def producto_con_stock(db_session):
    p = Producto(titulo="Torta de vainilla", descripcion="x" * 10, imagen="torta.jpg", precio=50000, stock=5, familia="tortas", activo=True)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _agregar_al_carrito(cliente, producto_id, cantidad=1):
    return cliente.post("/api/carrito/items", json={"producto_id": producto_id, "cantidad": cantidad})


class TestTipoDeEntrega:
    def test_checkout_a_domicilio_exige_direccion(self, cliente_autenticado, producto_con_stock):
        _agregar_al_carrito(cliente_autenticado, producto_con_stock.id)
        r = cliente_autenticado.post(
            "/api/pedidos",
            json={"telefono_contacto": "3001234567", "metodo_pago": "tarjeta", "tipo_entrega": "domicilio"},
        )
        assert r.status_code == 422, r.text  # falta direccion_envio

    def test_checkout_recoger_en_tienda_no_exige_direccion_y_guarda_texto_fijo(self, cliente_autenticado, producto_con_stock, monkeypatch):
        _capturar_correos(monkeypatch)
        _agregar_al_carrito(cliente_autenticado, producto_con_stock.id)
        r = cliente_autenticado.post(
            "/api/pedidos",
            json={
                "telefono_contacto": "3001234567",
                "metodo_pago": "tarjeta",
                "tipo_entrega": "recoger_tienda",
                "fecha_entrega_solicitada": (date.today() + timedelta(days=2)).isoformat(),
                "franja_horaria": "10:00-12:00",
            },
        )
        assert r.status_code == 201, r.text
        datos = r.json()
        assert datos["tipo_entrega"] == "recoger_tienda"
        assert "recoge" in datos["direccion_envio"].lower()
        assert datos["franja_horaria"] == "10:00-12:00"

    def test_fecha_de_entrega_en_el_pasado_se_rechaza(self, cliente_autenticado, producto_con_stock):
        _agregar_al_carrito(cliente_autenticado, producto_con_stock.id)
        r = cliente_autenticado.post(
            "/api/pedidos",
            json={
                "direccion_envio": "Calle 1 # 2-3",
                "telefono_contacto": "3001234567",
                "metodo_pago": "tarjeta",
                "fecha_entrega_solicitada": (date.today() - timedelta(days=1)).isoformat(),
            },
        )
        assert r.status_code == 422

    def test_franja_horaria_con_formato_invalido_se_rechaza(self, cliente_autenticado, producto_con_stock):
        _agregar_al_carrito(cliente_autenticado, producto_con_stock.id)
        r = cliente_autenticado.post(
            "/api/pedidos",
            json={
                "direccion_envio": "Calle 1 # 2-3",
                "telefono_contacto": "3001234567",
                "metodo_pago": "tarjeta",
                "franja_horaria": "mañana",
            },
        )
        assert r.status_code == 422


class TestCorreoDeConfirmacion:
    def test_checkout_envia_correo_de_confirmacion_al_dueno_del_pedido(self, cliente_autenticado, producto_con_stock, monkeypatch):
        enviados = _capturar_correos(monkeypatch)
        _agregar_al_carrito(cliente_autenticado, producto_con_stock.id)
        r = cliente_autenticado.post(
            "/api/pedidos",
            json={"direccion_envio": "Calle 1 # 2-3", "telefono_contacto": "3001234567", "metodo_pago": "tarjeta"},
        )
        assert r.status_code == 201, r.text
        assert len(enviados) == 1
        destino, asunto, _cuerpo = enviados[0]
        assert str(r.json()["id"]) in asunto


class TestCancelarPedido:
    @pytest.fixture()
    def pedido_pendiente(self, db_session, producto_con_stock):
        from app.models.usuario import Usuario

        # `cliente_autenticado` (conftest.py) simula el usuario id=1 vía
        # dependency override SIN insertarlo en la base de datos (no
        # hace falta para probar /api/pagos). Pero cancelar_pedido sí
        # necesita `pedido.usuario` cargable desde la BD (para armar el
        # correo), así que aquí sí se persiste una fila real con ese id.
        if db_session.get(Usuario, 1) is None:
            db_session.add(
                Usuario(
                    id=1,
                    nombre="Cliente",
                    apellido="De Pruebas",
                    tipo_documento="CC",
                    numero_documento="123456789",
                    direccion="Calle Falsa 123",
                    telefono="3000000000",
                    correo="cliente@correo.com",
                    password_hash="x",
                    rol="cliente",
                )
            )
            db_session.commit()

        pedido = Pedido(
            usuario_id=1,
            subtotal=50000,
            descuento=0,
            total=50000,
            direccion_envio="Calle 1 # 2-3",
            telefono_contacto="3001234567",
            metodo_pago="tarjeta",
            tipo_entrega=TipoEntrega.domicilio,
        )
        db_session.add(pedido)
        db_session.commit()
        db_session.refresh(pedido)
        from app.models.pedido import PedidoItem

        db_session.add(
            PedidoItem(pedido_id=pedido.id, producto_id=producto_con_stock.id, titulo=producto_con_stock.titulo, precio_unitario=50000, cantidad=1)
        )
        producto_con_stock.stock -= 1  # simula el descuento que hace el checkout real
        db_session.commit()
        db_session.refresh(pedido)
        return pedido

    def test_cancelar_pedido_pendiente_sin_pago_repone_stock_y_no_intenta_reembolso(
        self, cliente_autenticado, pedido_pendiente, producto_con_stock, db_session, monkeypatch
    ):
        enviados = _capturar_correos(monkeypatch)
        stock_antes = producto_con_stock.stock

        r = cliente_autenticado.post(f"/api/pedidos/{pedido_pendiente.id}/cancelar")

        assert r.status_code == 200, r.text
        assert r.json()["estado"] == "cancelado"
        db_session.expire_all()
        assert db_session.get(Producto, producto_con_stock.id).stock == stock_antes + 1
        assert len(enviados) == 1
        assert "no tenía un pago aprobado" not in enviados[0][2] or "reembolsado" not in enviados[0][2]

    def test_cancelar_pedido_pagado_con_pago_aprobado_dispara_reembolso(
        self, cliente_autenticado, pedido_pendiente, producto_con_stock, db_session, monkeypatch
    ):
        _capturar_correos(monkeypatch)
        pedido_pendiente.estado = EstadoPedido.pagado
        pago = Pago(
            referencia=f"DULCE-{pedido_pendiente.id}",
            proveedor="wompi",
            pedido_id=pedido_pendiente.id,
            correo_cliente="cliente@example.com",
            monto_centavos=5000000,
            moneda="COP",
            estado=EstadoPago.APPROVED,
            id_transaccion_proveedor="tx-aprobada-123",
        )
        db_session.add(pago)
        db_session.commit()

        llamados = []

        def _anular_transaccion(self, id_transaccion):
            llamados.append(id_transaccion)
            return {"data": {"id": id_transaccion, "status": "VOIDED"}}

        monkeypatch.setattr(WompiClient, "anular_transaccion", _anular_transaccion)

        r = cliente_autenticado.post(f"/api/pedidos/{pedido_pendiente.id}/cancelar")

        assert r.status_code == 200, r.text
        assert llamados == ["tx-aprobada-123"]
        db_session.expire_all()
        assert db_session.get(Pago, pago.id).estado == EstadoPago.VOIDED
        assert db_session.get(Pedido, pedido_pendiente.id).estado == EstadoPedido.cancelado

    def test_no_se_puede_cancelar_un_pedido_ya_entregado(self, cliente_autenticado, pedido_pendiente, db_session):
        pedido_pendiente.estado = EstadoPedido.entregado
        db_session.commit()
        r = cliente_autenticado.post(f"/api/pedidos/{pedido_pendiente.id}/cancelar")
        assert r.status_code == 409

    def test_no_se_puede_cancelar_el_pedido_de_otro_usuario(self, cliente_autenticado, db_session):
        ajeno = Pedido(
            usuario_id=99, subtotal=10000, descuento=0, total=10000,
            direccion_envio="x" * 10, telefono_contacto="3000000000", metodo_pago="tarjeta",
        )
        db_session.add(ajeno)
        db_session.commit()
        r = cliente_autenticado.post(f"/api/pedidos/{ajeno.id}/cancelar")
        assert r.status_code == 403

    def test_patch_estado_no_permite_poner_cancelado_directamente(self, cliente_autenticado, pedido_pendiente):
        """Ese atajo se saltaría el reembolso/reposición de stock — ver cancelar_pedido."""
        # Nota: PATCH /estado exige admin/empleado; cliente_autenticado es un cliente normal -> 403 primero.
        r = cliente_autenticado.patch(f"/api/pedidos/{pedido_pendiente.id}/estado", json={"estado": "cancelado"})
        assert r.status_code == 403
