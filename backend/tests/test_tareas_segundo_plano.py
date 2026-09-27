"""
Pruebas de TAREAS EN SEGUNDO PLANO (BackgroundTasks) — criterio 6.2.

Se comprueba que (1) la respuesta HTTP sale bien y (2) la tarea corre
después con los datos correctos, y (3) que un fallo del correo NUNCA
rompe la operación de negocio ya confirmada.
"""

from types import SimpleNamespace

from app.services import notificaciones

PQR = {"tipo": "reclamo", "asunto": "Pedido incompleto", "descripcion": "Solo llegó una de las dos cajas de cupcakes."}


class TestPQRNotificacion:
    def test_crear_pqr_responde_201_y_dispara_la_tarea(self, cliente, crear_usuario, token_de, monkeypatch):
        llamadas = []
        monkeypatch.setattr("app.routes.pqr.notificar_pqr_recibida", lambda *args: llamadas.append(args))
        crear_usuario("cli@example.com")

        r = cliente.post("/api/pqr", json=PQR, headers=token_de("cli@example.com"))

        assert r.status_code == 201
        assert len(llamadas) == 1
        correo, nombre, pqr_id, tipo, asunto = llamadas[0]
        assert correo == "cli@example.com" and pqr_id == r.json()["id"] and tipo == "reclamo"

    def test_pqr_sin_token_401_y_sin_tarea(self, cliente, monkeypatch):
        llamadas = []
        monkeypatch.setattr("app.routes.pqr.notificar_pqr_recibida", lambda *args: llamadas.append(args))
        assert cliente.post("/api/pqr", json=PQR).status_code == 401
        assert llamadas == []

    def test_pqr_invalida_422_y_sin_tarea(self, cliente, crear_usuario, token_de, monkeypatch):
        llamadas = []
        monkeypatch.setattr("app.routes.pqr.notificar_pqr_recibida", lambda *args: llamadas.append(args))
        crear_usuario("cli@example.com")
        r = cliente.post("/api/pqr", json={**PQR, "descripcion": "corta"}, headers=token_de("cli@example.com"))
        assert r.status_code == 422 and llamadas == []

    def test_un_correo_que_falla_no_rompe_la_creacion_de_la_pqr(self, cliente, crear_usuario, token_de, monkeypatch):
        """SMTP configurado pero inalcanzable: la PQR igual queda creada (201)."""
        smtp_roto = SimpleNamespace(SMTP_HOST="127.0.0.1", SMTP_PORT=1, SMTP_USER="", SMTP_PASSWORD="", SMTP_FROM="x@x.co")
        monkeypatch.setattr(notificaciones, "get_settings", lambda: smtp_roto)
        crear_usuario("cli@example.com")
        headers = token_de("cli@example.com")

        r = cliente.post("/api/pqr", json=PQR, headers=headers)

        assert r.status_code == 201
        assert cliente.get(f"/api/pqr/{r.json()['id']}", headers=headers).status_code == 200


class TestServicioDeCorreo:
    def test_sin_smtp_no_envia_y_no_falla(self, monkeypatch, caplog):
        monkeypatch.setattr(notificaciones, "get_settings", lambda: SimpleNamespace(SMTP_HOST=""))
        with caplog.at_level("INFO", logger="app.services.notificaciones"):
            assert notificaciones.enviar_correo("a@b.co", "Asunto", "Cuerpo") is False
        assert "correo_simulado" in caplog.text

    def test_con_smtp_arma_y_envia_el_mensaje(self, monkeypatch):
        enviados = []

        class SMTPFalso:
            def __init__(self, host, port, timeout):
                self.host = host

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def starttls(self):
                pass

            def login(self, u, p):
                pass

            def send_message(self, mensaje):
                enviados.append(mensaje)

        cfg = SimpleNamespace(SMTP_HOST="smtp.falso.co", SMTP_PORT=587, SMTP_USER="u", SMTP_PASSWORD="p", SMTP_FROM="Dulce Esencia <x@x.co>")
        monkeypatch.setattr(notificaciones, "get_settings", lambda: cfg)
        monkeypatch.setattr(notificaciones.smtplib, "SMTP", SMTPFalso)

        assert notificaciones.enviar_correo("cli@example.com", "Hola", "Cuerpo") is True
        assert enviados[0]["To"] == "cli@example.com" and enviados[0]["Subject"] == "Hola"


class TestRecuperacionEnSegundoPlano:
    def test_recuperar_envia_codigo_otp_solo_si_el_correo_existe_pero_responde_igual(self, cliente, crear_usuario, monkeypatch):
        enviados = []
        monkeypatch.setattr("app.routes.usuarios.enviar_recuperacion_password", lambda *a: enviados.append(a))
        crear_usuario("cli@example.com")

        existe = cliente.post("/api/usuarios/recuperar", json={"correo": "cli@example.com"})
        no_existe = cliente.post("/api/usuarios/recuperar", json={"correo": "fantasma@example.com"})

        assert existe.status_code == no_existe.status_code == 200
        assert existe.json() == no_existe.json()  # no revela qué correos existen

        # Solo se envía tarea en segundo plano para el correo que SÍ existe,
        # con un código OTP de 6 dígitos numéricos (no un enlace con token).
        assert len(enviados) == 1
        codigo_enviado = enviados[0][2]
        assert codigo_enviado.isdigit() and len(codigo_enviado) == 6
