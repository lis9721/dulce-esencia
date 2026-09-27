"""
Fixtures de pytest exclusivas de los tests del módulo de pagos.

No toca ni depende del test existente (tests/test_endpoint_roles_403.py,
que corre contra un servidor real con MySQL/XAMPP levantado) — este
conftest es autocontenido: usa SQLite en memoria en vez de la MySQL
real de desarrollo, así que `pytest` corre en cualquier máquina sin
necesitar XAMPP levantado ni credenciales de Wompi reales (punto 18 del
alcance: "No hacer llamadas reales a Wompi durante los tests
unitarios").

Variables de entorno (SECRET_KEY, etc.) se definen ANTES de importar
`app.main` porque `get_settings()` está cacheada con `@lru_cache` y
`validar_env()` se ejecuta al importar el módulo.
"""

import os

os.environ.setdefault("SECRET_KEY", "clave-de-pruebas-para-pytest-0123456789")
os.environ.setdefault("WOMPI_PUBLIC_KEY", "pub_test_0000000000000000")
os.environ.setdefault("WOMPI_PRIVATE_KEY", "prv_test_0000000000000000")
os.environ.setdefault("WOMPI_EVENTS_SECRET", "test_events_secreto_de_pruebas")
os.environ.setdefault("WOMPI_INTEGRITY_SECRET", "test_integrity_secreto_de_pruebas")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.pago import Pago  # noqa: F401 - registra la tabla en Base.metadata
from app.models.usuario import Usuario

# engine de SQLite en memoria, compartido entre conexiones (StaticPool)
# para que todas las requests de un mismo test vean las mismas tablas.
engine_pruebas = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SesionPruebas = sessionmaker(autocommit=False, autoflush=False, bind=engine_pruebas)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine_pruebas)
    sesion = SesionPruebas()
    try:
        yield sesion
    finally:
        sesion.close()
        Base.metadata.drop_all(bind=engine_pruebas)


@pytest.fixture()
def cliente_autenticado(db_session, monkeypatch):
    """
    TestClient con:
      - get_db() sobreescrito para usar la sesión de SQLite en memoria.
      - get_current_user() sobreescrito para simular un usuario ya
        logueado (correo "cliente@correo.com"), sin pasar por
        login/JWT real — lo que se está probando es el módulo de
        pagos, no la autenticación (que ya tiene su propia prueba en
        tests/test_endpoint_roles_403.py).
    """
    from app.auth import get_current_user
    from app.main import app

    usuario_falso = Usuario(
        id=1,
        nombre="Cliente",
        apellido="De Pruebas",
        tipo_documento="CC",
        numero_documento="123456789",
        direccion="Calle Falsa 123",
        telefono="3000000000",
        correo="cliente@correo.com",
        password_hash="hash-no-usado-en-esta-prueba",
        rol="cliente",
        activo=True,
    )

    def _get_db_pruebas():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_pruebas
    app.dependency_overrides[get_current_user] = lambda: usuario_falso

    with TestClient(app) as cliente:
        yield cliente

    app.dependency_overrides.clear()


# ======================================================================
# Fixtures para las pruebas de INTEGRACIÓN con autenticación REAL
# (tests/test_auth.py, test_productos_crud.py, test_seguridad_sqli.py...)
#
# A diferencia de `cliente_autenticado` (que finge un usuario logueado),
# estas pruebas pasan por POST /api/auth/login y usan el JWT de verdad,
# así se prueba también la protección por token y por rol. Todo corre
# sobre SQLite en memoria: no hace falta MySQL/XAMPP.
# ======================================================================
import itertools

_contador_documento = itertools.count(10_000_000)
PASSWORD_DE_PRUEBAS = "Clave1234!"


@pytest.fixture(autouse=True)
def _reiniciar_limitador_de_peticiones():
    """El login tiene un tope de 10 intentos/15 min por IP: se reinicia entre pruebas."""
    from app.rate_limit import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture()
def cliente(db_session):
    """TestClient con la BD de pruebas y SIN sobreescribir la autenticación."""
    from app.main import app

    def _get_db_pruebas():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_pruebas
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


@pytest.fixture()
def crear_usuario(db_session):
    """Fábrica de usuarios ya verificados (bcrypt real) para probar por rol."""
    from app.auth import crear_hash

    def _crear(correo="cliente@example.com", rol="cliente", password=PASSWORD_DE_PRUEBAS, verificado=True, activo=True):
        usuario = Usuario(
            nombre="Prueba",
            apellido=rol.capitalize(),
            tipo_documento="CC",
            numero_documento=str(next(_contador_documento)),
            direccion="Calle 1 # 2-3",
            telefono="3001234567",
            correo=correo,
            password_hash=crear_hash(password),
            rol=rol,
            verificado=verificado,
            activo=activo,
        )
        db_session.add(usuario)
        db_session.commit()
        db_session.refresh(usuario)
        return usuario

    return _crear


@pytest.fixture()
def token_de(cliente):
    """Inicia sesión por la API real y devuelve el header Authorization."""

    def _token(correo, password=PASSWORD_DE_PRUEBAS):
        respuesta = cliente.post("/api/auth/login", json={"correo": correo, "password": password})
        assert respuesta.status_code == 200, respuesta.text
        return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}

    return _token
