"""
Validación de contrato con Schemathesis contra el /openapi.json real de
la app (punto pedido en el workflow de CI, ver .github/workflows/ci.yml).

Corre directamente sobre la app ASGI en memoria (schemathesis.from_asgi),
no contra un servidor levantado aparte: reutiliza el mismo patrón de
SQLite en memoria que el resto de los tests (ver conftest.py), así que
no necesita MySQL/TiDB ni credenciales reales de Wompi.

A propósito solo se activa el check `not_a_server_error`: la mayoría de
las rutas exigen JWT, así que Schemathesis las llamará sin autenticación
y recibirá 401/403 (correcto y esperado) — lo único que nos interesa
detectar aquí es que ninguna combinación de datos genere un 500 no
controlado (un contrato que la documentación promete pero el código
rompe).
"""

import os

os.environ.setdefault("SECRET_KEY", "clave-de-pruebas-para-pytest-0123456789")
os.environ.setdefault("WOMPI_PUBLIC_KEY", "pub_test_0000000000000000")
os.environ.setdefault("WOMPI_PRIVATE_KEY", "prv_test_0000000000000000")
os.environ.setdefault("WOMPI_EVENTS_SECRET", "test_events_secreto_de_pruebas")
os.environ.setdefault("WOMPI_INTEGRITY_SECRET", "test_integrity_secreto_de_pruebas")

import pytest
import schemathesis
from hypothesis import settings as hypothesis_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Mismo patrón que tests/conftest.py: SQLite en memoria en vez de la
# MySQL/TiDB real, para que Schemathesis pueda ejercitar rutas que leen
# o escriben en la base de datos sin depender de infraestructura externa.
_engine_contrato = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_SesionContrato = sessionmaker(autocommit=False, autoflush=False, bind=_engine_contrato)
Base.metadata.create_all(bind=_engine_contrato)


def _get_db_contrato():
    sesion = _SesionContrato()
    try:
        yield sesion
    finally:
        sesion.close()


@pytest.fixture(autouse=True)
def _sobreescribir_get_db():
    """
    `app` es un único objeto FastAPI compartido por TODO el proceso de
    pytest (se importa una sola vez). Otros archivos de tests (p. ej.
    conftest.py -> cliente_autenticado) hacen
    `app.dependency_overrides.clear()` en su propio teardown, lo que
    borraría también el override de este archivo si se hiciera una
    sola vez a nivel de módulo. Por eso se reaplica antes de CADA test
    de este archivo y se limpia después, sin depender del orden en que
    pytest ejecute los demás archivos.
    """
    app.dependency_overrides[get_db] = _get_db_contrato
    yield
    app.dependency_overrides.pop(get_db, None)


schema = schemathesis.openapi.from_asgi("/openapi.json", app)


@schema.parametrize()
# derandomize=True: Hypothesis usa siempre la misma semilla, así que
# genera exactamente los mismos casos en cada corrida. Sin esto, un CI
# en rojo por un caso límite real (p. ej. un id gigantesco) podría
# ponerse en verde solo por reintentar, sin haberse arreglado nada —
# preferible un fallo 100% reproducible que uno intermitente.
@hypothesis_settings(max_examples=5, deadline=None, derandomize=True)
def test_contrato_openapi_sin_errores_de_servidor(case):
    case.call_and_validate(checks=[schemathesis.checks.not_a_server_error])
