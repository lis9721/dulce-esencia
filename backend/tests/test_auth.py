"""
Pruebas de AUTENTICACIÓN y AUTORIZACIÓN (criterios 4 y 9 de la matriz).

Corren con `pytest tests/test_auth.py -v`, sin MySQL ni servidor: usan
SQLite en memoria y pasan por el login real (bcrypt + JWT).
"""

from datetime import timedelta

from app.auth import crear_access_token, decodificar_access_token
from app.models.usuario import Usuario

from tests.conftest import PASSWORD_DE_PRUEBAS

REGISTRO_VALIDO = {
    "nombre": "Laura",
    "apellido": "Gómez",
    "tipo_documento": "CC",
    "numero_documento": "1020304050",
    "direccion": "Carrera 10 # 20-30",
    "telefono": "3111234567",
    "correo": "laura@example.com",
    "password": "Segura2026!",
    "confirmar_password": "Segura2026!",
    "acepta_tratamiento_datos": True,
}


class TestLogin:
    def test_login_correcto_devuelve_jwt_y_usuario(self, cliente, crear_usuario):
        crear_usuario("ana@example.com", rol="cliente")
        r = cliente.post("/api/auth/login", json={"correo": "ana@example.com", "password": PASSWORD_DE_PRUEBAS})
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["token_type"] == "bearer"
        assert cuerpo["usuario"]["correo"] == "ana@example.com"
        assert "password_hash" not in cuerpo["usuario"]  # nunca se filtra el hash
        payload = decodificar_access_token(cuerpo["access_token"])
        assert payload["sub"] == "ana@example.com" and payload["role"] == "cliente"

    def test_password_incorrecta_da_401(self, cliente, crear_usuario):
        crear_usuario("ana@example.com")
        r = cliente.post("/api/auth/login", json={"correo": "ana@example.com", "password": "OtraClave999!"})
        assert r.status_code == 401

    def test_usuario_inexistente_da_el_mismo_401_que_password_incorrecta(self, cliente, crear_usuario):
        """Mismo código y mismo mensaje: no se revela qué correos existen."""
        crear_usuario("ana@example.com")
        mala = cliente.post("/api/auth/login", json={"correo": "ana@example.com", "password": "OtraClave999!"})
        fantasma = cliente.post("/api/auth/login", json={"correo": "nadie@example.com", "password": "OtraClave999!"})
        assert mala.status_code == fantasma.status_code == 401
        assert mala.json() == fantasma.json()

    def test_correo_sin_verificar_da_403(self, cliente, crear_usuario):
        crear_usuario("nuevo@example.com", verificado=False)
        r = cliente.post("/api/auth/login", json={"correo": "nuevo@example.com", "password": PASSWORD_DE_PRUEBAS})
        assert r.status_code == 403

    def test_cuenta_inactiva_da_403(self, cliente, crear_usuario):
        crear_usuario("baja@example.com", activo=False)
        r = cliente.post("/api/auth/login", json={"correo": "baja@example.com", "password": PASSWORD_DE_PRUEBAS})
        assert r.status_code == 403

    def test_cuerpo_invalido_da_422(self, cliente):
        assert cliente.post("/api/auth/login", json={"correo": "no-es-correo", "password": "x"}).status_code == 422
        assert cliente.post("/api/auth/login", json={"correo": "a@b.co"}).status_code == 422

    def test_limite_de_intentos_da_429(self, cliente):
        """Freno a la fuerza bruta: el intento 11 desde la misma IP se bloquea."""
        codigos = [
            cliente.post("/api/auth/login", json={"correo": "x@example.com", "password": "Cualquiera123!"}).status_code
            for _ in range(11)
        ]
        assert codigos[:10] == [401] * 10
        assert codigos[10] == 429


class TestProteccionPorToken:
    def test_sin_token_da_401(self, cliente):
        assert cliente.get("/api/usuarios/perfil").status_code == 401

    def test_token_basura_da_401(self, cliente):
        r = cliente.get("/api/usuarios/perfil", headers={"Authorization": "Bearer esto.no.es.un.jwt"})
        assert r.status_code == 401

    def test_token_expirado_da_401(self, cliente, crear_usuario):
        crear_usuario("ana@example.com")
        vencido = crear_access_token({"sub": "ana@example.com", "role": "cliente", "tv": 0}, expira=timedelta(seconds=-5))
        assert cliente.get("/api/usuarios/perfil", headers={"Authorization": f"Bearer {vencido}"}).status_code == 401

    def test_token_valido_accede_al_perfil(self, cliente, crear_usuario, token_de):
        crear_usuario("ana@example.com")
        r = cliente.get("/api/usuarios/perfil", headers=token_de("ana@example.com"))
        assert r.status_code == 200 and r.json()["correo"] == "ana@example.com"

    def test_token_se_invalida_si_cambia_token_version(self, cliente, crear_usuario, token_de, db_session):
        """Cambiar la contraseña sube token_version y mata los JWT anteriores."""
        usuario = crear_usuario("ana@example.com")
        headers = token_de("ana@example.com")
        usuario.token_version += 1
        db_session.commit()
        assert cliente.get("/api/usuarios/perfil", headers=headers).status_code == 401

    def test_cuenta_desactivada_pierde_acceso_de_inmediato(self, cliente, crear_usuario, token_de, db_session):
        usuario = crear_usuario("ana@example.com")
        headers = token_de("ana@example.com")
        usuario.activo = False
        db_session.commit()
        assert cliente.get("/api/usuarios/perfil", headers=headers).status_code == 403


class TestAutorizacionPorRol:
    def test_cliente_no_puede_listar_usuarios(self, cliente, crear_usuario, token_de):
        crear_usuario("cli@example.com", rol="cliente")
        assert cliente.get("/api/usuarios", headers=token_de("cli@example.com")).status_code == 403

    def test_empleado_y_admin_si_pueden(self, cliente, crear_usuario, token_de):
        crear_usuario("emp@example.com", rol="empleado")
        crear_usuario("adm@example.com", rol="admin")
        assert cliente.get("/api/usuarios", headers=token_de("emp@example.com")).status_code == 200
        assert cliente.get("/api/usuarios", headers=token_de("adm@example.com")).status_code == 200

    def test_empleado_no_puede_borrar_usuarios_solo_admin(self, cliente, crear_usuario, token_de):
        crear_usuario("emp@example.com", rol="empleado")
        objetivo = crear_usuario("otro@example.com", rol="cliente")
        assert cliente.delete(f"/api/usuarios/{objetivo.id}", headers=token_de("emp@example.com")).status_code == 403

    def test_cliente_no_puede_ver_el_pedido_de_otro(self, cliente, crear_usuario, token_de):
        crear_usuario("cli@example.com", rol="cliente")
        assert cliente.get("/api/pedidos/999999", headers=token_de("cli@example.com")).status_code in (403, 404)


class TestRegistro:
    def test_registro_crea_cuenta_sin_verificar_y_envia_correo_en_segundo_plano(self, cliente, monkeypatch, db_session):
        from app.models.usuario import Usuario

        enviados = []
        monkeypatch.setattr(
            "app.routes.usuarios.enviar_verificacion_cuenta",
            lambda correo, nombre, codigo, minutos_vigencia: enviados.append((correo, nombre, codigo, minutos_vigencia)),
        )
        r = cliente.post("/api/usuarios/registro", json=REGISTRO_VALIDO)
        assert r.status_code == 201, r.text

        usuario = db_session.query(Usuario).filter_by(correo="laura@example.com").one()
        assert usuario.verificado is False
        assert usuario.rol == "cliente"  # el registro público nunca crea admins
        assert usuario.password_hash != REGISTRO_VALIDO["password"]  # guardada como hash
        assert usuario.password_hash.startswith("$2")  # bcrypt
        assert usuario.verificacion_otp_hash is not None  # se guardó el hash del OTP, no el código

        # La tarea en segundo plano corrió con el código OTP de 6 dígitos.
        assert len(enviados) == 1
        correo_enviado, _nombre, codigo_enviado, _minutos = enviados[0]
        assert correo_enviado == "laura@example.com"
        assert codigo_enviado.isdigit() and len(codigo_enviado) == 6

        # Queda registrada la fecha de aceptación de la política de datos
        # (ver docs/POLITICA-TRATAMIENTO-DATOS.md), no solo un booleano.
        assert usuario.tratamiento_datos_aceptado_en is not None

    def test_registro_sin_aceptar_tratamiento_de_datos_da_400(self, cliente, db_session):
        from app.models.usuario import Usuario

        r = cliente.post("/api/usuarios/registro", json={**REGISTRO_VALIDO, "acepta_tratamiento_datos": False})
        assert r.status_code == 400, r.text
        assert db_session.query(Usuario).filter_by(correo="laura@example.com").first() is None

    def test_verificar_correo_con_codigo_correcto_activa_la_cuenta(self, cliente, db_session):
        r = cliente.post("/api/usuarios/registro", json=REGISTRO_VALIDO)
        assert r.status_code == 201, r.text
        codigo = r.json()["codigoVerificacion"]  # solo expuesto fuera de producción (NODE_ENV != "production")

        r2 = cliente.post("/api/usuarios/verificar-correo", json={"correo": "laura@example.com", "codigo": codigo})
        assert r2.status_code == 200, r2.text

        usuario = db_session.query(Usuario).filter_by(correo="laura@example.com").one()
        assert usuario.verificado is True
        assert usuario.verificacion_otp_hash is None  # el código se consume: no puede reutilizarse

    def test_verificar_correo_con_codigo_incorrecto_da_400_y_cuenta_el_intento(self, cliente, db_session):
        cliente.post("/api/usuarios/registro", json=REGISTRO_VALIDO)

        r = cliente.post("/api/usuarios/verificar-correo", json={"correo": "laura@example.com", "codigo": "000000"})
        assert r.status_code == 400
        assert "intento" in r.json()["detail"].lower()

        usuario = db_session.query(Usuario).filter_by(correo="laura@example.com").one()
        assert usuario.verificacion_otp_intentos == 1
        assert usuario.verificado is False

    def test_verificar_correo_invalida_el_codigo_tras_agotar_intentos(self, cliente, db_session):
        from app.rate_limit import limiter

        r = cliente.post("/api/usuarios/registro", json=REGISTRO_VALIDO)
        codigo_correcto = r.json()["codigoVerificacion"]
        codigo_incorrecto = "000000" if codigo_correcto != "000000" else "111111"

        for _ in range(5):
            r = cliente.post(
                "/api/usuarios/verificar-correo", json={"correo": "laura@example.com", "codigo": codigo_incorrecto}
            )
            assert r.status_code == 400

        # El límite de 5 intentos AL CÓDIGO ya se agotó; se resetea el
        # límite de peticiones POR IP (LIMITE_RECUPERAR, un mecanismo
        # aparte, ver app/rate_limit.py) para poder comprobar en esta
        # misma prueba que el límite que importa aquí es el de
        # intentos por código, no el de peticiones por IP.
        limiter.reset()

        # Ya se agotaron los 5 intentos: aunque ahora se mande el código
        # CORRECTO, se rechaza porque el backend ya lo invalidó.
        r_final = cliente.post(
            "/api/usuarios/verificar-correo", json={"correo": "laura@example.com", "codigo": codigo_correcto}
        )
        assert r_final.status_code == 400

        usuario = db_session.query(Usuario).filter_by(correo="laura@example.com").one()
        assert usuario.verificado is False
        assert usuario.verificacion_otp_hash is None
        assert usuario.verificacion_otp_intentos == 0

    def test_codigo_con_formato_invalido_da_422(self, cliente):
        r = cliente.post("/api/usuarios/verificar-correo", json={"correo": "laura@example.com", "codigo": "123"})
        assert r.status_code == 422

    def test_registro_no_permite_elegir_rol_admin(self, cliente, db_session):
        from app.models.usuario import Usuario

        cliente.post("/api/usuarios/registro", json={**REGISTRO_VALIDO, "rol": "admin"})
        usuario = db_session.query(Usuario).filter_by(correo="laura@example.com").one()
        assert usuario.rol == "cliente"

    def test_registro_con_password_debil_da_422(self, cliente):
        r = cliente.post("/api/usuarios/registro", json={**REGISTRO_VALIDO, "password": "123", "confirmar_password": "123"})
        assert r.status_code == 422

    def test_registro_duplicado_da_409(self, cliente):
        assert cliente.post("/api/usuarios/registro", json=REGISTRO_VALIDO).status_code == 201
        assert cliente.post("/api/usuarios/registro", json=REGISTRO_VALIDO).status_code == 409


class TestRecuperarPassword:
    def test_recuperar_responde_generico_exista_o_no_el_correo(self, cliente, crear_usuario):
        crear_usuario("ana@example.com")
        r1 = cliente.post("/api/usuarios/recuperar", json={"correo": "ana@example.com"})
        r2 = cliente.post("/api/usuarios/recuperar", json={"correo": "nadie@example.com"})
        assert r1.status_code == r2.status_code == 200
        assert r1.json() == r2.json()

    def test_recuperar_genera_otp_hasheado_para_cuenta_existente(self, cliente, crear_usuario, db_session):
        usuario = crear_usuario("ana@example.com")
        cliente.post("/api/usuarios/recuperar", json={"correo": "ana@example.com"})
        db_session.refresh(usuario)
        assert usuario.reset_otp_hash is not None
        assert usuario.reset_otp_expira is not None
        assert usuario.reset_otp_intentos == 0

    def test_restablecer_con_codigo_correcto_cambia_la_password_y_sube_token_version(
        self, cliente, crear_usuario, db_session
    ):
        usuario = crear_usuario("ana@example.com")
        version_previa = usuario.token_version

        # Se genera el OTP directamente (sin depender del envío real de
        # correo) para poder leerlo en texto plano en la prueba, igual
        # que hace el backend antes de hashearlo.
        from app.utils.otp import generar_otp, hash_otp
        from datetime import datetime, timedelta, timezone

        codigo = generar_otp()
        usuario.reset_otp_hash = hash_otp(codigo)
        usuario.reset_otp_expira = datetime.now(timezone.utc) + timedelta(minutes=10)
        db_session.commit()

        r = cliente.post(
            "/api/usuarios/restablecer",
            json={"correo": "ana@example.com", "codigo": codigo, "password_nueva": "NuevaClave123!"},
        )
        assert r.status_code == 200, r.text

        db_session.refresh(usuario)
        assert usuario.token_version == version_previa + 1
        assert usuario.reset_otp_hash is None  # se consume: no se puede reutilizar

        # La contraseña nueva ya sirve para iniciar sesión.
        login = cliente.post("/api/auth/login", json={"correo": "ana@example.com", "password": "NuevaClave123!"})
        assert login.status_code == 200

    def test_restablecer_con_codigo_expirado_da_400(self, cliente, crear_usuario, db_session):
        usuario = crear_usuario("ana@example.com")

        from app.utils.otp import generar_otp, hash_otp
        from datetime import datetime, timedelta, timezone

        codigo = generar_otp()
        usuario.reset_otp_hash = hash_otp(codigo)
        usuario.reset_otp_expira = datetime.now(timezone.utc) - timedelta(minutes=1)  # ya venció
        db_session.commit()

        r = cliente.post(
            "/api/usuarios/restablecer",
            json={"correo": "ana@example.com", "codigo": codigo, "password_nueva": "NuevaClave123!"},
        )
        assert r.status_code == 400

    def test_restablecer_sin_solicitar_codigo_antes_da_400(self, cliente, crear_usuario):
        crear_usuario("ana@example.com")
        r = cliente.post(
            "/api/usuarios/restablecer",
            json={"correo": "ana@example.com", "codigo": "123456", "password_nueva": "NuevaClave123!"},
        )
        assert r.status_code == 400
