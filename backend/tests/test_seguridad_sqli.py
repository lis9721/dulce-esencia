"""
Pruebas de INYECCIÓN SQL. Evidencia para la sustentación
(docs/SEGURIDAD-SQL-INJECTION.md).

Se prueban las TRES capas de defensa:
  1. Validación de entrada (Pydantic): un "correo" con comillas ni llega a la BD.
  2. Consulta preparada: aunque la validación se saltara, el valor viaja como
     PARÁMETRO ligado y no como código SQL.
  3. Hash bcrypt: la contraseña nunca se compara dentro del SQL.
"""

import pytest
from sqlalchemy import event

from app.models.usuario import Usuario
from app.repositories.usuario_repository import buscar_por_correo, sql_de_busqueda_por_correo
from app.utils.busqueda import escapar_like
from tests.conftest import PASSWORD_DE_PRUEBAS

PAYLOADS = [
    "' OR 1=1 --",
    "' OR '1'='1",
    "admin@example.com' --",
    "admin@example.com'; DROP TABLE usuarios; --",
    "\" OR \"\"=\"",
    "' UNION SELECT id, password_hash FROM usuarios --",
    "1; SELECT SLEEP(5)",
]


class TestCapa1ValidacionDeEntrada:
    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_payload_en_el_correo_se_rechaza_con_422(self, cliente, crear_usuario, payload):
        crear_usuario("admin@example.com", rol="admin")
        r = cliente.post("/api/auth/login", json={"correo": payload, "password": PASSWORD_DE_PRUEBAS})
        assert r.status_code == 422  # ni siquiera llega a consultar la base de datos

    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_payload_como_password_no_inicia_sesion(self, cliente, crear_usuario, payload):
        crear_usuario("admin@example.com", rol="admin")
        r = cliente.post("/api/auth/login", json={"correo": "admin@example.com", "password": payload + "xxxxxxxx"})
        assert r.status_code in (401, 422)
        assert "access_token" not in r.text


class TestCapa2ConsultaPreparada:
    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_repositorio_trata_el_payload_como_dato(self, db_session, crear_usuario, payload):
        """Salta la validación de Pydantic y le pasa el payload directo a la consulta."""
        crear_usuario("admin@example.com", rol="admin")
        assert buscar_por_correo(db_session, payload) is None  # con concatenación devolvería al primer usuario

    def test_la_tabla_sigue_intacta_tras_un_drop_table_inyectado(self, db_session, crear_usuario):
        crear_usuario("admin@example.com", rol="admin")
        buscar_por_correo(db_session, "x'; DROP TABLE usuarios; --")
        assert db_session.query(Usuario).count() == 1

    def test_el_sql_lleva_un_marcador_y_no_el_valor(self):
        sql = sql_de_busqueda_por_correo().lower()
        assert "where usuarios.correo = :correo" in sql

    def test_en_ejecucion_el_valor_va_en_los_parametros_no_en_el_texto(self, db_session, crear_usuario):
        capturado = []

        def _espia(conn, cursor, statement, parameters, context, executemany):
            capturado.append((statement, parameters))

        # Se registra el "espía" sobre la conexión de ESTA sesión (los
        # listeners a nivel de Engine solo aplican a conexiones nuevas).
        conexion = db_session.connection()
        event.listen(conexion, "before_cursor_execute", _espia)
        try:
            payload = "' OR 1=1 --"
            buscar_por_correo(db_session, payload)
        finally:
            event.remove(conexion, "before_cursor_execute", _espia)

        statement, parameters = capturado[-1]
        assert payload not in statement  # el texto SQL NO contiene lo que escribió el usuario
        assert payload in parameters  # viaja aparte, como parámetro
        assert "?" in statement or "%s" in statement or ":" in statement  # marcador de posición


class TestOtrasEntradas:
    def test_busqueda_de_catalogo_con_payload_no_rompe_ni_filtra(self, cliente):
        for payload in ("'; DROP TABLE productos; --", "' OR '1'='1"):
            r = cliente.get("/api/productos", params={"buscar": payload})
            assert r.status_code == 200 and r.json()["datos"] == []

    def test_id_no_numerico_en_la_ruta_da_422(self, cliente):
        assert cliente.get("/api/productos/1 OR 1=1").status_code == 422

    def test_escape_de_comodines_like(self):
        assert escapar_like("50%_off\\") == "50\\%\\_off\\\\"
