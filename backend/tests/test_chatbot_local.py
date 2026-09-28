"""
Pruebas del CHATBOT GRATUITO (criterio 7 y sección «Chat bot gratuito»):
sin OPENAI_API_KEY responde por reglas + catálogo real, sin internet.
"""

import pytest

from app.models.producto import FamiliaProducto, Producto
from app.services.chatbot.faq_service import _normalizar, responder_localmente


@pytest.fixture()
def catalogo(db_session):
    db_session.add_all(
        [
            Producto(titulo="Torta de Fresas y Crema", descripcion="Bizcocho de vainilla con crema y fresas.", imagen="a.jpg", precio=78000, stock=5, familia=FamiliaProducto.tortas, activo=True),
            Producto(titulo="Torta Tres Leches", descripcion="Bizcocho bañado en tres leches.", imagen="b.jpg", precio=72000, stock=0, familia=FamiliaProducto.tortas, activo=True),
            Producto(titulo="Cupcakes de Vainilla x6", descripcion="Cupcakes con buttercream.", imagen="c.jpg", precio=36000, stock=9, familia=FamiliaProducto.cupcakes, activo=False),
        ]
    )
    db_session.commit()


def test_normaliza_tildes_y_mayusculas():
    assert _normalizar("¿Cuánto CUESTA el envío?") == "¿cuanto cuesta el envio?"


def test_familia_lista_productos_reales_con_precio(db_session, catalogo):
    r = responder_localmente(db_session, "¿Qué tortas tienen?")
    assert "Torta de Fresas y Crema" in r and "$78.000 COP" in r
    assert "Torta Tres Leches" in r and "agotado" in r  # avisa el stock 0


def test_singular_tambien_reconoce_la_familia(db_session, catalogo):
    assert "Torta de Fresas y Crema" in responder_localmente(db_session, "busco una torta")


def test_palabra_clave_corta_no_se_activa_dentro_de_otra_palabra(db_session):
    # «pse» está dentro de «repsol»: no debe responder con medios de pago.
    assert "Wompi" not in responder_localmente(db_session, "trabajo en repsol")


def test_no_recomienda_productos_inactivos(db_session, catalogo):
    assert "Cupcakes de Vainilla" not in responder_localmente(db_session, "quiero unos cupcakes")


def test_busqueda_por_nombre(db_session, catalogo):
    assert "Torta Tres Leches" in responder_localmente(db_session, "cuanto vale la tres leches")


def test_pqr_deriva_al_panel(db_session):
    assert "PQR" in responder_localmente(db_session, "quiero poner una queja")


def test_medios_de_pago_no_inventa_otros(db_session):
    r = responder_localmente(db_session, "¿Cómo puedo pagar?")
    assert "Wompi" in r and "contraentrega" in r


def test_saludo_y_mensaje_desconocido(db_session):
    assert "asistente virtual" in responder_localmente(db_session, "hola")
    assert "No estoy seguro" in responder_localmente(db_session, "asdfgh qwerty")


def test_inyeccion_en_el_mensaje_no_rompe(db_session, catalogo):
    r = responder_localmente(db_session, "'; DROP TABLE productos; --")
    assert isinstance(r, str) and db_session.query(Producto).count() == 3


class TestEndpoint:
    def test_sin_api_key_responde_local_y_guarda_la_conversacion(self, cliente, catalogo, monkeypatch):
        monkeypatch.setattr("app.services.chatbot.ai_service.get_settings", lambda: type("S", (), {"OPENAI_API_KEY": "", "OPENAI_BASE_URL": "", "OPENAI_MODEL": "x"})())
        r = cliente.post("/api/chatbot/mensaje", json={"mensaje": "quiero ver las tortas"})  # invitado, sin token
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["origen"] == "local" and "Torta de Fresas y Crema" in cuerpo["respuesta"]

        historial = cliente.get(f"/api/chatbot/conversaciones/{cuerpo['conversacion_id']}")
        assert [m["rol"] for m in historial.json()["mensajes"]] == ["usuario", "asistente"]

    def test_mensaje_vacio_422(self, cliente):
        assert cliente.post("/api/chatbot/mensaje", json={"mensaje": "   "}).status_code == 422


class TestEscaladoAPQR:
    """El chatbot no solo *dice* que hay que registrar una PQR: la crea de una vez cuando puede."""

    def test_usuario_logueado_con_queja_crea_la_pqr_de_verdad(self, cliente, catalogo, crear_usuario, token_de, monkeypatch):
        monkeypatch.setattr(
            "app.services.chatbot.ai_service.get_settings",
            lambda: type("S", (), {"OPENAI_API_KEY": "", "OPENAI_BASE_URL": "", "OPENAI_MODEL": "x"})(),
        )
        crear_usuario(correo="quejoso@example.com")
        headers = token_de("quejoso@example.com")

        r = cliente.post(
            "/api/chatbot/mensaje",
            json={"mensaje": "Quiero poner una queja: mi torta llegó dañada"},
            headers=headers,
        )
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["pqr_creada_id"] is not None
        assert f"#{cuerpo['pqr_creada_id']}" in cuerpo["respuesta"]

        pqr = cliente.get(f"/api/pqr/{cuerpo['pqr_creada_id']}", headers=headers)
        assert pqr.status_code == 200 and pqr.json()["tipo"] == "queja"

    def test_visitante_sin_sesion_no_crea_pqr_solo_lo_invita_a_iniciar_sesion(self, cliente, catalogo, monkeypatch):
        monkeypatch.setattr(
            "app.services.chatbot.ai_service.get_settings",
            lambda: type("S", (), {"OPENAI_API_KEY": "", "OPENAI_BASE_URL": "", "OPENAI_MODEL": "x"})(),
        )
        r = cliente.post("/api/chatbot/mensaje", json={"mensaje": "tengo una queja"})
        assert r.status_code == 200
        assert r.json()["pqr_creada_id"] is None


def test_si_la_ia_responde_vacio_tambien_degrada_al_bot_local(cliente, catalogo, monkeypatch):
    """Content vacío/None del proveedor (recorte, filtro, etc.) no debe llegar en blanco al usuario."""

    class Mensaje:
        content = "   "

    class Choice:
        message = Mensaje()

    class RespuestaVacia:
        choices = [Choice()]

    class ClienteVacio:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return RespuestaVacia()

    monkeypatch.setattr("app.services.chatbot.ai_service._cliente_openai", lambda: ClienteVacio())
    r = cliente.post("/api/chatbot/mensaje", json={"mensaje": "quiero ver las tortas"})
    assert r.status_code == 200
    assert r.json()["origen"] == "local" and "Torta de Fresas y Crema" in r.json()["respuesta"]


def test_si_el_proveedor_de_ia_falla_responde_el_bot_local(cliente, catalogo, monkeypatch):
    """Cuota agotada / sin red: el usuario igual recibe respuesta (origen = local)."""
    import httpx
    from openai import APIConnectionError

    class ClienteRoto:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise APIConnectionError(request=httpx.Request("POST", "https://api.proveedor.test/v1"))

    monkeypatch.setattr("app.services.chatbot.ai_service._cliente_openai", lambda: ClienteRoto())
    r = cliente.post("/api/chatbot/mensaje", json={"mensaje": "quiero ver las tortas"})
    assert r.status_code == 200
    assert r.json()["origen"] == "local" and "Torta de Fresas y Crema" in r.json()["respuesta"]


# ---------------------------------------------------------------------------
# Funcionalidades nuevas: contexto real para la IA, pedidos y tarjetas de producto
# ---------------------------------------------------------------------------

SIN_API_KEY = lambda: type("S", (), {"OPENAI_API_KEY": "", "OPENAI_BASE_URL": "", "OPENAI_MODEL": "x"})()  # noqa: E731


def _crear_pedido(db_session, usuario, estado="enviado", total=78000):
    from app.models.pedido import EstadoPedido, MetodoPago, Pedido

    pedido = Pedido(
        usuario_id=usuario.id,
        estado=EstadoPedido(estado),
        subtotal=total,
        descuento=0,
        total=total,
        direccion_envio="Calle 1 # 2-3",
        telefono_contacto="3001234567",
        metodo_pago=MetodoPago.transferencia,
    )
    db_session.add(pedido)
    db_session.commit()
    db_session.refresh(pedido)
    return pedido


def test_contexto_de_la_ia_trae_catalogo_activo_y_no_pedidos_de_un_visitante(db_session, catalogo):
    from app.services.chatbot.contexto import construir_contexto

    contexto = construir_contexto(db_session, None)
    assert "Torta de Fresas y Crema" in contexto and "$78.000 COP" in contexto
    assert "Cupcakes de Vainilla" not in contexto  # inactivo
    assert "VISITANTE SIN SESIÓN" in contexto and "Pedido #" not in contexto


def test_contexto_solo_incluye_los_pedidos_del_propio_usuario(db_session, catalogo, crear_usuario):
    from app.services.chatbot.contexto import construir_contexto

    ana = crear_usuario(correo="ana@example.com")
    beto = crear_usuario(correo="beto@example.com")
    pedido_ana = _crear_pedido(db_session, ana, estado="enviado")
    pedido_beto = _crear_pedido(db_session, beto, estado="pagado", total=36000)

    contexto = construir_contexto(db_session, ana)
    assert f"Pedido #{pedido_ana.id}" in contexto and "enviado" in contexto
    assert f"Pedido #{pedido_beto.id}" not in contexto


def test_bot_local_informa_el_estado_de_los_pedidos_del_usuario(db_session, crear_usuario):
    ana = crear_usuario(correo="ana@example.com")
    pedido = _crear_pedido(db_session, ana, estado="enviado")

    r = responder_localmente(db_session, "¿cómo va mi pedido?", ana)
    assert f"Pedido #{pedido.id}" in r and "enviado" in r


def test_bot_local_pide_iniciar_sesion_para_ver_pedidos(db_session):
    assert "Inicia sesión" in responder_localmente(db_session, "¿cómo va mi pedido?")


def test_endpoint_devuelve_tarjetas_de_producto_para_comprar_desde_el_chat(cliente, catalogo, monkeypatch):
    monkeypatch.setattr("app.services.chatbot.ai_service.get_settings", SIN_API_KEY)
    r = cliente.post("/api/chatbot/mensaje", json={"mensaje": "quiero ver las tortas"})
    assert r.status_code == 200
    productos = r.json()["productos"]
    assert {p["titulo"] for p in productos} == {"Torta de Fresas y Crema", "Torta Tres Leches"}
    assert all({"id", "titulo", "precio", "stock", "imagen"} <= set(p) for p in productos)


def test_endpoint_no_devuelve_tarjetas_si_el_mensaje_no_habla_de_catalogo(cliente, catalogo, monkeypatch):
    monkeypatch.setattr("app.services.chatbot.ai_service.get_settings", SIN_API_KEY)
    r = cliente.post("/api/chatbot/mensaje", json={"mensaje": "hola"})
    assert r.status_code == 200 and r.json()["productos"] == []


def test_la_ia_recibe_el_contexto_real_de_la_tienda(cliente, catalogo, monkeypatch):
    capturado = {}

    def falsa_generar(historial, contexto=""):
        capturado["contexto"] = contexto
        return "Te recomiendo la Torta de Fresas y Crema."

    monkeypatch.setattr("app.routes.chatbot.generar_respuesta", falsa_generar)
    r = cliente.post("/api/chatbot/mensaje", json={"mensaje": "¿qué me recomiendas?"})
    assert r.status_code == 200 and r.json()["origen"] == "ia"
    assert "Torta de Fresas y Crema" in capturado["contexto"]
