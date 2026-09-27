"""
GET /health y /health/db — alias en inglés pedidos explícitamente por
el punto 23 del alcance del módulo de pagos.

Este backend ya expone su propio health check en español
(GET / y GET /api/salud/db, ver app/main.py). Este router NO los
reemplaza: solo agrega las rutas /health y /health/db con la forma de
respuesta exacta que pide el módulo de pagos, para no romper nada que
ya esté usando /api/salud/db (p. ej. el frontend actual).
"""

from fastapi import APIRouter

from app.database import verificar_conexion

router = APIRouter(tags=["salud"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/health/db")
def health_db():
    if verificar_conexion():
        return {"status": "ok"}
    return {"status": "error"}
