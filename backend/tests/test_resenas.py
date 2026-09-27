import pytest

from app.models.pedido import EstadoPedido, Pedido, PedidoItem
from app.models.producto import Producto
from app.models.usuario import Usuario


@pytest.fixture()
def producto(db_session):
    p = Producto(titulo="Cupcake de chocolate", descripcion="x" * 10, imagen="cupcake.jpg", precio=8000, stock=20, familia="tortas", activo=True)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture()
def usuario_comprador(db_session):
    """Persiste el usuario id=1 que simula `cliente_autenticado` (ver conftest.py)."""
    if db_session.get(Usuario, 1) is None:
        db_session.add(
            Usuario(
                id=1, nombre="Cliente", apellido="De Pruebas", tipo_documento="CC", numero_documento="123456789",
                direccion="Calle Falsa 123", telefono="3000000000", correo="cliente@correo.com",
                password_hash="x", rol="cliente",
            )
        )
        db_session.commit()


def _crear_pedido_pagado(db_session, producto_id, usuario_id=1, estado=EstadoPedido.pagado):
    pedido = Pedido(
        usuario_id=usuario_id, subtotal=8000, descuento=0, total=8000,
        direccion_envio="Calle 1 # 2-3", telefono_contacto="3001234567", metodo_pago="tarjeta", estado=estado,
    )
    db_session.add(pedido)
    db_session.commit()
    db_session.add(PedidoItem(pedido_id=pedido.id, producto_id=producto_id, titulo="x", precio_unitario=8000, cantidad=1))
    db_session.commit()
    return pedido


class TestCrearResena:
    def test_sin_haber_comprado_no_puede_resenar(self, cliente_autenticado, producto, usuario_comprador):
        r = cliente_autenticado.post(f"/api/productos/{producto.id}/resenas", json={"calificacion": 5, "comentario": "Buenísimo"})
        assert r.status_code == 403

    def test_con_pedido_pagado_puede_resenar_y_el_promedio_se_actualiza(self, cliente_autenticado, producto, usuario_comprador, db_session):
        _crear_pedido_pagado(db_session, producto.id)
        r = cliente_autenticado.post(f"/api/productos/{producto.id}/resenas", json={"calificacion": 4, "comentario": "Muy rico"})
        assert r.status_code == 201, r.text
        assert r.json()["calificacion"] == 4

        db_session.expire_all()
        actualizado = db_session.get(Producto, producto.id)
        assert actualizado.total_resenas == 1
        assert float(actualizado.calificacion_promedio) == 4.0

    def test_con_pedido_pendiente_sin_pagar_no_puede_resenar(self, cliente_autenticado, producto, usuario_comprador, db_session):
        _crear_pedido_pagado(db_session, producto.id, estado=EstadoPedido.pendiente)
        r = cliente_autenticado.post(f"/api/productos/{producto.id}/resenas", json={"calificacion": 5})
        assert r.status_code == 403

    def test_no_puede_resenar_dos_veces_el_mismo_producto(self, cliente_autenticado, producto, usuario_comprador, db_session):
        _crear_pedido_pagado(db_session, producto.id)
        assert cliente_autenticado.post(f"/api/productos/{producto.id}/resenas", json={"calificacion": 5}).status_code == 201
        r = cliente_autenticado.post(f"/api/productos/{producto.id}/resenas", json={"calificacion": 3})
        assert r.status_code == 409

    def test_calificacion_fuera_de_rango_se_rechaza(self, cliente_autenticado, producto, usuario_comprador, db_session):
        _crear_pedido_pagado(db_session, producto.id)
        r = cliente_autenticado.post(f"/api/productos/{producto.id}/resenas", json={"calificacion": 6})
        assert r.status_code == 422

    def test_producto_inexistente_da_404(self, cliente_autenticado):
        r = cliente_autenticado.post("/api/productos/999999/resenas", json={"calificacion": 5})
        assert r.status_code == 404


class TestListarYPromedio:
    def test_promedio_con_varias_resenas_de_distintos_usuarios(self, cliente, producto, db_session):
        from app.auth import crear_hash

        for i, calificacion in enumerate([5, 3], start=1):
            usuario = Usuario(
                nombre=f"U{i}", apellido="Test", tipo_documento="CC", numero_documento=f"{i}"*10,
                direccion="x", telefono="3000000000", correo=f"u{i}@example.com",
                password_hash=crear_hash("Segura2026!"), rol="cliente", verificado=True,
            )
            db_session.add(usuario)
            db_session.commit()
            _crear_pedido_pagado(db_session, producto.id, usuario_id=usuario.id)

            login = cliente.post("/api/auth/login", json={"correo": f"u{i}@example.com", "password": "Segura2026!"})
            token = login.json()["access_token"]
            r = cliente.post(
                f"/api/productos/{producto.id}/resenas",
                json={"calificacion": calificacion},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 201, r.text

        db_session.expire_all()
        actualizado = db_session.get(Producto, producto.id)
        assert actualizado.total_resenas == 2
        assert float(actualizado.calificacion_promedio) == 4.0  # (5+3)/2

        r = cliente.get(f"/api/productos/{producto.id}/resenas")
        assert r.status_code == 200
        assert r.json()["meta"]["total"] == 2


class TestEditarYBorrar:
    def test_editar_propia_resena_recalcula_promedio(self, cliente_autenticado, producto, usuario_comprador, db_session):
        _crear_pedido_pagado(db_session, producto.id)
        creada = cliente_autenticado.post(f"/api/productos/{producto.id}/resenas", json={"calificacion": 2}).json()

        r = cliente_autenticado.put(f"/api/productos/{producto.id}/resenas/{creada['id']}", json={"calificacion": 5, "comentario": "Cambié de opinión"})
        assert r.status_code == 200
        db_session.expire_all()
        assert float(db_session.get(Producto, producto.id).calificacion_promedio) == 5.0

    def test_borrar_propia_resena_recalcula_promedio_a_cero(self, cliente_autenticado, producto, usuario_comprador, db_session):
        _crear_pedido_pagado(db_session, producto.id)
        creada = cliente_autenticado.post(f"/api/productos/{producto.id}/resenas", json={"calificacion": 3}).json()

        r = cliente_autenticado.delete(f"/api/productos/{producto.id}/resenas/{creada['id']}")
        assert r.status_code == 204
        db_session.expire_all()
        actualizado = db_session.get(Producto, producto.id)
        assert actualizado.total_resenas == 0
        assert float(actualizado.calificacion_promedio) == 0

    def test_no_puede_editar_la_resena_de_otro(self, cliente, producto, db_session):
        from app.auth import crear_hash

        autor = Usuario(
            nombre="Autor", apellido="Original", tipo_documento="CC", numero_documento="1111111111",
            direccion="x", telefono="3000000000", correo="autor@example.com",
            password_hash=crear_hash("Segura2026!"), rol="cliente", verificado=True,
        )
        otro = Usuario(
            nombre="Otro", apellido="Usuario", tipo_documento="CC", numero_documento="9999999999",
            direccion="x", telefono="3000000000", correo="otro@example.com",
            password_hash=crear_hash("Segura2026!"), rol="cliente", verificado=True,
        )
        db_session.add_all([autor, otro])
        db_session.commit()
        _crear_pedido_pagado(db_session, producto.id, usuario_id=autor.id)

        token_autor = cliente.post("/api/auth/login", json={"correo": "autor@example.com", "password": "Segura2026!"}).json()["access_token"]
        creada = cliente.post(
            f"/api/productos/{producto.id}/resenas",
            json={"calificacion": 3},
            headers={"Authorization": f"Bearer {token_autor}"},
        ).json()

        token_otro = cliente.post("/api/auth/login", json={"correo": "otro@example.com", "password": "Segura2026!"}).json()["access_token"]
        r = cliente.put(
            f"/api/productos/{producto.id}/resenas/{creada['id']}",
            json={"calificacion": 1},
            headers={"Authorization": f"Bearer {token_otro}"},
        )
        assert r.status_code == 403
