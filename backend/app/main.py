"""
Punto de entrada de la API — equivalente en Python a backend-node/server.js.

Corre con:  uvicorn app.main:app --reload
(por defecto queda en el puerto 8000 de uvicorn)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings, validar_env
from app.core.errores import registrar_manejadores_globales
from app.core.middleware import CabecerasSeguridadMiddleware, RegistroPeticionesMiddleware
from app.database import sincronizar_esquema, verificar_conexion
from app.exceptions.pagos import registrar_manejadores_excepciones
from app.rate_limit import limiter, manejador_limite_excedido

# Importa todos los modelos para que queden registrados en Base.metadata
# (create_all/Alembic los necesitan) apenas se importe la app.
from app import models  # noqa: F401
from app.routes import (
    carrito,
    chatbot,
    contacto,
    cupones,
    estadisticas,
    facturas,
    health,
    pagos,
    pedidos,
    pqr,
    productos,
    proveedores,
    reportes,
    resenas,
    roles,
    servicios,
    usuarios,
    ventas,
    webhooks_pagos,
)

settings = get_settings()

DESCRIPCION_API = """
API REST de **Dulce Esencia Pastelería** (catálogo, carrito, pedidos, pagos, ventas, facturas, PQR y chatbot).

## Cómo autenticarte en esta documentación
1. Ejecuta `POST /api/auth/login` con un correo verificado y su contraseña.
2. Copia el valor de `access_token` de la respuesta.
3. Pulsa **Authorize** (candado, arriba a la derecha) y pega solo el token.
4. Los endpoints con candado ya funcionan. Los roles son `cliente`, `empleado` y `admin`.

## Convenciones
- Errores: `{"detail": "mensaje"}` (o una lista en errores de validación **422**). El módulo de pagos
  responde `{"success": false, "error": {"code", "message"}}`.
- Listados paginados: `?page=1&limit=10` → `{"datos": [...], "paginacion": {...}}`.
- Códigos usados: 200/201 éxito, 400 petición inválida, 401 sin sesión, 403 sin permiso, 404 no
  existe, 409 conflicto, 422 validación, 429 límite de peticiones, 502 falla del proveedor de pago.

Documentación alterna en **ReDoc**: `/redoc`.
"""

TAGS_METADATA = [
    {"name": "auth", "description": "Inicio de sesión. Devuelve un **JWT** (flujo Bearer)."},
    {"name": "usuarios", "description": "Registro, verificación de correo, recuperación de contraseña, perfil y gestión de usuarios (admin)."},
    {"name": "productos", "description": "Catálogo de la pastelería (tortas, cupcakes, galletas...): consulta pública y **CRUD** protegido (admin/empleado)."},
    {"name": "servicios", "description": "Servicios de la pastelería (tortas personalizadas, mesas de dulces, talleres): consulta pública y CRUD protegido."},
    {"name": "carrito", "description": "Carrito de compras persistente del usuario autenticado."},
    {"name": "pedidos", "description": "Checkout: convierte el carrito en pedido (valida stock y precio en el servidor) y factura PDF."},
    {"name": "cupones", "description": "Cupones de descuento (porcentaje o monto fijo) con vigencia y usos máximos."},
    {"name": "pagos", "description": "Pasarela de pagos **Wompi** (Checkout Web): crea el pago, lo consulta y lo sincroniza."},
    {"name": "webhooks", "description": "Recepción de eventos firmados de los proveedores de pago."},
    {"name": "ventas", "description": "Punto de venta: ventas de productos y servicios, o generadas desde un pedido pagado."},
    {"name": "facturas", "description": "Facturas emitidas a partir de una venta, con descarga en PDF."},
    {"name": "reportes", "description": "Reporte diario de ventas en JSON, PDF y Excel."},
    {"name": "estadisticas", "description": "Indicadores para los dashboards del panel."},
    {"name": "pqr", "description": "Peticiones, quejas, reclamos y sugerencias. El correo de confirmación se envía en **segundo plano**."},
    {"name": "chatbot", "description": "Asistente virtual: IA (si hay API key) o chatbot local gratuito basado en reglas."},
    {"name": "proveedores", "description": "Proveedores de materias primas, lácteos, empaques, insumos y logística: CRUD y suspensión/reactivación (admin/empleado)."},
    {"name": "roles", "description": "Roles y permisos del sistema (solo admin)."},
    {"name": "contacto", "description": "Mensajes del formulario de contacto."},
    {"name": "salud", "description": "Comprobación de que el servidor y la base de datos responden."},
]


# Corta el arranque si falta JWT_SECRET o sigue siendo el placeholder
# del .env.example — mismo criterio que validarEnv() en server.js.
validar_env(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verifica en vivo que la conexión a MySQL/TiDB esté activa al arrancar.
    conectado = verificar_conexion()
    # En Vercel (SKIP_SCHEMA_SYNC=true) el esquema NO se sincroniza en
    # cada cold start de la función: ya corrió una única vez desde el
    # workflow de deploy (backend/scripts/sync_schema.py) antes de
    # publicar este código. Repetirlo en cada arranque solo agregaría
    # latencia (varias consultas + posibles ALTER TABLE) sin necesidad.
    # En local (XAMPP) se deja en False y sí se sincroniza al vuelo,
    # como siempre.
    if conectado and not settings.SKIP_SCHEMA_SYNC:
        # Crea las tablas que falten y agrega columnas nuevas del modelo
        # (p. ej. productos.familia / productos.peso_g, o las de la
        # nueva tabla `pagos`) que aún no existan en la base de datos
        # física. Ver docstring en app/database.py para el detalle de
        # por qué hace falta esto además de Base.metadata.create_all().
        sincronizar_esquema()
    yield


app = FastAPI(
    title="Dulce Esencia Pastelería — API",
    version="5.0.0",
    description=DESCRIPCION_API,
    openapi_tags=TAGS_METADATA,
    contact={"name": "Equipo Dulce Esencia", "url": "https://github.com/"},
    license_info={"name": "Uso académico — SENA"},
    lifespan=lifespan,
)

# Rate limiting (equivalente a express-rate-limit en server.js): el
# Limiter vive en app/rate_limit.py y se aplica ruta por ruta con
# @limiter.limit(...) en app/routes/usuarios.py (login, registro,
# recuperar, restablecer, reenviar-verificacion). Estas tres líneas son
# el "cableado" que hace falta para que esos decoradores funcionen: el
# limiter queda accesible desde cualquier request, un 429 (no un 500)
# cuando se supera el límite, y la IP real del cliente detrás de un
# proxy/balanceador (X-Forwarded-For) en vez de siempre la del proxy.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, manejador_limite_excedido)
app.add_middleware(SlowAPIMiddleware)

# Handlers de la jerarquía de PagoException (app/exceptions/pagos.py):
# responden {"success": false, "error": {...}} solo para /api/pagos y
# /api/webhooks, sin afectar el resto de la API.
registrar_manejadores_excepciones(app)

# Handlers GLOBALES (app/core/errores.py): dan a TODA la API un mismo
# cuerpo de error —404, 409, 422 de Pydantic y el 500 inesperado— y
# dejan la traza de los 500 en el log en vez de en la respuesta.
# Se registran DESPUÉS de los de pagos a propósito: aquellos son por
# tipo de excepción (PagoException) y siguen ganando en su módulo.
registrar_manejadores_globales(app)

# Middlewares propios (app/core/middleware.py): una línea de log por
# petición con su X-Request-ID, y las cabeceras de seguridad que en el
# backend Node ponía helmet. HSTS solo en producción.
app.add_middleware(RegistroPeticionesMiddleware)
app.add_middleware(
    CabecerasSeguridadMiddleware,
    solo_https=settings.NODE_ENV == "production",
)

# CORS restringido por origen (igual que server.js): en desarrollo solo
# FRONTEND_URL; en producción, la lista separada por comas de
# CORS_ORIGIN. allow_credentials=True se mantiene por si en el futuro
# se vuelve a una variante con cookie (ver decisión de arquitectura en
# app/auth.py: hoy el JWT viaja en el header Authorization: Bearer, no
# en una cookie httpOnly) — el origen nunca puede ser "*" mientras esto
# siga en True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origenes_permitidos,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Archivos de imagen de productos ya subidos, servidos en /uploads/...
# (ej. /uploads/productos/<archivo>.jpg), igual que en server.js.
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/", tags=["salud"], summary="Mensaje de bienvenida")
def raiz():
    return {"mensaje": "Backend de Dulce Esencia Pastelería funcionando correctamente"}


@app.get("/api/salud/db", tags=["salud"], summary="Estado de la conexión a la base de datos")
def salud_db():
    conectado = verificar_conexion()
    if conectado:
        return {"conectado": True, "mensaje": "Conexión a MySQL activa."}
    return {"conectado": False, "error": "No se pudo comprobar la conexión a la base de datos."}


app.include_router(usuarios.router)
app.include_router(usuarios.auth_router)
app.include_router(productos.router)
app.include_router(resenas.router)
app.include_router(proveedores.router)
app.include_router(servicios.router)
app.include_router(contacto.router)
app.include_router(carrito.router)
app.include_router(pedidos.router)
app.include_router(cupones.router)
app.include_router(roles.router)
app.include_router(pagos.router)
app.include_router(webhooks_pagos.router)
app.include_router(ventas.router)
app.include_router(facturas.router)
app.include_router(reportes.router)
app.include_router(pqr.router)
app.include_router(chatbot.router)
app.include_router(estadisticas.router)
app.include_router(health.router)
