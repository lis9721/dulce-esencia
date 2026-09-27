# Auditoría contra la Lista de Chequeo (Valoración Final — FastAPI)

Este documento recorre los 65 criterios del archivo
`LISTA_CHEQUEO_VALORACION_FINAL_PROYECTO_FASTAPI_FICHA_-_3406211.xlsx` y
dice, para cada uno, si el proyecto lo cumple y dónde. Se usa como
referencia de esta entrega, no reemplaza el propio checklist.

Leyenda: ✅ cumple · ⚠️ cumple parcialmente (se explica la brecha) ·
❌ no se abordó en esta entrega.

## Diseño de API y rutas

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Rutas en plural, sin verbos | ✅ | `/api/proveedores`, `/api/proveedores/{id}`; sub-recursos también son sustantivos (`/suspensiones`, `/reactivaciones`), nunca `/suspender`. |
| 2 | El verbo HTTP corresponde a la operación | ✅ | `app/routes/proveedores.py`: GET lee, POST crea, PUT reemplaza, PATCH actualiza parcial, DELETE elimina. |
| 3 | Tabla recurso–verbo–ruta–código previa al código | ✅ | Docstring de `app/routes/proveedores.py`, tabla completa antes del primer endpoint. |
| 4 | Una operación de negocio como sub-recurso | ✅ | `POST /proveedores/{id}/suspensiones` y `/reactivaciones` — no un PATCH genérico sobre `estado`. |
| 5 | El cliente no decide id/fechas/estado | ✅ | `ProveedorCrear`/`ProveedorActualizar` usan `extra="forbid"`; `estado` no existe en ningún esquema de entrada (`test_el_cliente_no_puede_enviar_campos_que_decide_el_servidor`). |

## Estructura del proyecto

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 6 | Estructura modular (routers/schemas/models/crud/core/services) | ✅ | Se agregó `app/crud/` y `app/core/` (antes solo existían `routes/`, `schemas/`, `models/`, `services/`, `repositories/`). El resto de recursos del proyecto original ya seguía esta separación salvo por la falta de una capa `crud/` explícita. |
| 7 | `main.py` solo config/middlewares/`include_router` | ✅ | `app/main.py` no contiene lógica de negocio; se le agregaron 2 líneas de `add_middleware` y una llamada a `registrar_manejadores_globales`. |
| 8 | Cada recurso con su `APIRouter` (prefix + tags) | ✅ | Ya era el patrón del proyecto; `proveedores.router` sigue la misma convención. |
| 9 | La lógica de datos vive en `crud`, no en la ruta | ✅ para proveedores · ⚠️ para el resto | `app/routes/proveedores.py` no toca la sesión directamente. Los routers preexistentes (`productos.py`, `usuarios.py`, etc.) siguen consultando la BD dentro de la función de ruta — migrarlos todos a `crud/` queda fuera del alcance de esta entrega. |
| 10 | `requirements.txt` con versiones fijas + `.env.example` | ✅ | Ya existían y no se modificaron; ninguna librería nueva fue necesaria. |

## Esquemas Pydantic v2

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 11 | Esquemas separados creación/actualización/respuesta | ✅ | `ProveedorCrear`, `ProveedorReemplazar`, `ProveedorActualizar`, `ProveedorSalida` en `app/schemas/proveedor.py`. |
| 12 | Restricciones con `Field` | ✅ | `min_length`/`max_length`/`ge`/`le`/`pattern` en cada campo de `ProveedorBase`. |
| 13 | `field_validator` con regla de negocio propia | ✅ | `normalizar_nit` calcula el dígito de verificación con el algoritmo de la DIAN; `validar_correo_corporativo` rechaza dominios personales. |
| 14 | `model_validator` que compara varios campos | ✅ | `validar_coherencia_de_credito`: cruza `dias_credito` y `cupo_credito`, y aplica el tope de logística según `categoria`. |
| 15 | PATCH con `exclude_unset=True`, sin sobrescribir con nulos | ✅ | `app/routes/proveedores.py::actualizar_proveedor` + `test_patch_no_sobrescribe_con_nulos_los_campos_omitidos`. |
| 16 | Nada de Pydantic v1 | ✅ | Todo el módulo nuevo usa `field_validator`/`model_validator`/`ConfigDict`/`model_dump`; se verificó que no aparezca `@validator`, `class Config`, `.dict()` ni `orm_mode`. |
| 17 | `response_model` controla la salida | ✅ | `ProveedorSalida` declara cada campo explícitamente — nada del modelo ORM se serializa "por accidente". |

## CRUD y códigos de estado

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 18 | CRUD completo del recurso principal | ✅ | Proveedores: GET (lista y detalle), POST, PUT, PATCH, DELETE + 2 sub-recursos. |
| 19 | POST responde 201 con el recurso | ✅ | `crear_proveedor` → `status.HTTP_201_CREATED`, devuelve `ProveedorSalida`. |
| 20 | DELETE responde 204 sin cuerpo | ✅ | `eliminar_proveedor` no tiene `return`; `test_delete_responde_204_sin_cuerpo` verifica `respuesta.content == b""`. |
| 21 | Conflictos → 409, nunca 400/422/500 | ✅ | NIT duplicado, proveedor con productos y transición de estado inválida son 409 (`app/exceptions/dominio.py`). |
| 22 | Paginación + 3 filtros opcionales | ✅ | `?categoria=&estado=&ciudad=&buscar=&dias_credito_maximo=` — 5 filtros combinables. |
| 23 | 404 con mensaje claro en recurso inexistente | ✅ | `ProveedorNoEncontrado` incluye el id en el mensaje. |
| 24 | Todos los endpoints con tag y summary | ✅ | Cada endpoint de `proveedores.py` declara `summary=`. |
| 25 | La app declara título/descripción/versión/tags | ✅ | Ya existía en `app/main.py`; se agregó la entrada `proveedores` a `TAGS_METADATA`. |
| 26 | Códigos de error a mano declarados en `responses` | ✅ | Cada endpoint de proveedores documenta sus posibles 401/403/404/409/422. |
| 27 | Ejemplo de cuerpo con `json_schema_extra` | ✅ | `ProveedorCrear`, `ProveedorReemplazar`, `ProveedorActualizar` y `SuspensionCrear` traen `examples`. |

## Manejo de errores

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 28 | Jerarquía de excepciones propia | ✅ | `app/exceptions/dominio.py`: `ErrorDeDominio` → `RecursoNoEncontrado`/`ConflictoDeNegocio`/`ReglaDeNegocioViolada` → especializaciones de proveedores. |
| 29 | La capa `crud` no lanza `HTTPException` | ✅ | `app/crud/proveedores.py` solo lanza excepciones de dominio; verificado por inspección (`grep HTTPException` no encuentra nada en ese archivo). |
| 30 | Handlers traducen cada excepción a su código HTTP | ✅ | `app/core/errores.py::manejador_error_de_dominio` usa `exc.status_code` de cada subclase. |
| 31 | Mismo formato de cuerpo en todos los errores | ✅ | `construir_cuerpo_error` es la única función que arma un error; se aplica a excepciones de dominio, `HTTPException` heredados y errores inesperados (excepto pagos, que mantiene su formato propio por alcance de ese módulo). |
| 32 | El 422 de validación con el mismo formato + detalle por campo | ✅ | `manejador_validacion` arma `error.campos` con `{campo, mensaje}` por cada error de Pydantic. |
| 33 | Un 500 responde genérico y registra la traza | ✅ | `manejador_error_inesperado` usa `logger.exception(...)` y nunca incluye el detalle técnico en la respuesta. |

## Dependencias

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 34 | Paginación extraída a una dependencia reutilizable | ✅ | `app/core/dependencias.py::ParametrosPaginacion`. |
| 35 | Dependencia que resuelve el recurso y corta con 404 | ✅ | `obtener_proveedor_o_404`, usada como `ProveedorDeLaRuta` en cada endpoint que recibe `{proveedor_id}`. |
| 36 | Dependencia anidada o parametrizable con clase | ✅ | `ParametrosPaginacion` es una clase parametrizable (`limite_por_defecto`, `limite_maximo`); `obtener_proveedor_o_404` depende a su vez de `get_db` (anidada). |
| 37 | `dependencies=[...]` a nivel de router cuando aplica a todo el recurso | ✅ | `router = APIRouter(..., dependencies=[Depends(requiere_rol("admin", "empleado"))])`. |

## Seguridad

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 38 | Contraseñas hasheadas con algoritmo moderno | ✅ | Ya existía (`app/auth.py::crear_hash`, bcrypt vía passlib); no se modificó. |
| 39 | `SECRET_KEY` desde el entorno, sin default inseguro | ✅ | Ya existía (`app/config.py::validar_env` rechaza placeholders); no se modificó. |
| 40 | Login emite JWT con `sub`, `rol` y `exp` | ✅ | Ya existía; no se modificó. |
| 41 | Dependencia valida el token y entrega el usuario | ✅ | Ya existía (`get_current_user`); reutilizada tal cual por el router de proveedores. |
| 42 | 401 vs 403 distinguidos, 401 con `WWW-Authenticate` | ✅ | Ya existía; `test_sin_token_responde_401_con_www_authenticate` lo verifica también para proveedores. |
| 43 | Endpoints que modifican exigen autenticación y rol | ✅ | Todo el router de proveedores exige rol; DELETE exige admin explícitamente. |
| 44 | CORS con lista explícita, sin comodín | ✅ | Ya existía (`settings.origenes_permitidos`); no se modificó. |
| 45 | Middleware propio de logging y cabeceras de seguridad | ✅ | **Nuevo**: `app/core/middleware.py` — `RegistroPeticionesMiddleware` (log + `X-Request-ID`) y `CabecerasSeguridadMiddleware` (nosniff, X-Frame-Options, CSP, Permissions-Policy, HSTS en producción). Antes el proyecto no tenía ninguno de los dos. |

## Modelo de datos y ORM

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 46 | Modelos con `DeclarativeBase`/`Mapped`/`mapped_column` | ✅ | `app/models/proveedor.py` sigue el mismo estilo que el resto del proyecto. |
| 47 | ≥4 entidades relacionadas con FK | ✅ | Ya eran más de 4 en el proyecto original (usuarios, productos, pedidos, ventas...); se agregó `proveedores` con FK real desde `productos.proveedor_id`. |
| 48 | Unicidad e índices donde corresponde | ✅ | `uq_proveedores_nit`, `uq_proveedores_razon_social`, índices en `estado`, `categoria` y `productos.proveedor_id`. |
| 49 | Engine único, sesión por dependencia | ✅ | Ya existía (`app/database.py`); no se modificó. |
| 50 | `select()`/`where()`, conteos en la base | ✅ | `app/crud/proveedores.py::listar` usa `select(func.count())` sobre una subconsulta, nunca `len()` sobre filas traídas a Python. |
| 51 | Operaciones con >1 escritura en una sola transacción | ✅ | `crud.suspender`: cambia el proveedor y desactiva su catálogo con un `UPDATE` masivo, todo antes de un único `commit()`; si algo falla, `rollback()` deshace ambas. |
| 52 | `IntegrityError` capturado → rollback → 409 | ✅ | `_traducir_integrity_error` en `app/crud/proveedores.py`. |
| 53 | `from_attributes` + esquemas Resumen para relaciones | ✅ | `ProveedorSalida`/`ProveedorResumen` usan `ConfigDict(from_attributes=True)`; `ProductoSalida.proveedor` usa el esquema Resumen, no el completo. |
| 54 | Script que puebla la base con datos realistas | ✅ | **Nuevo**: `backend/seed.py` — usuarios, 6 proveedores y 8 productos, idempotente. |
| 55 | Capa de datos asíncrona | ❌ | El proyecto entero usa SQLAlchemy **síncrono** (`Session`, no `AsyncSession`); migrarlo es un cambio arquitectónico que toca los 17 routers existentes y el `engine` compartido, fuera del alcance de esta entrega. El módulo de proveedores es consistente con el resto del proyecto, pero no resuelve este punto. |

## IA / servicios externos (chatbot)

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 56 | Modelo propio configurable | ✅ | `OPENAI_MODEL` en `.env` (`app/config.py`), sin nada hardcodeado; sirve para OpenAI o cualquier proveedor compatible vía `OPENAI_BASE_URL` — ver `docs/CHATBOT-GRATUITO.md`. |
| 57 | `run_in_threadpool` | ✅ | `enviar_mensaje` (`app/routes/chatbot.py`) es una función `def` normal, no `async def`: FastAPI/Starlette la ejecuta automáticamente en el threadpool (`run_in_threadpool`), así la llamada bloqueante al SDK de OpenAI no bloquea el event loop. |
| 58 | Timeout/reintentos | ✅ | `_cliente_openai()` (`app/services/chatbot/ai_service.py`) fija `timeout=15s` y `max_retries=1` en el cliente de `openai`; antes no había ningún límite y una respuesta lenta del proveedor dejaba la petición colgada. |
| 59 | Degradación | ✅ | `routes/chatbot.py`: cualquier `ChatbotNoConfigurado` (sin API key, error del SDK, timeout agotado) cae al chatbot local por reglas (`faq_service.responder_localmente`) — nunca queda mudo. Cubierto por `tests/test_chatbot_local.py`. |
| 60 | Validación de la respuesta | ✅ | `generar_respuesta` ahora revisa que el `content` no venga vacío/`None` (recorte, filtro del proveedor, etc.); si viene vacío, se trata como fallo y también degrada al chatbot local en vez de mostrarle un mensaje en blanco al usuario. Prueba: `test_si_la_ia_responde_vacio_tambien_degrada_al_bot_local`. |

## Tareas en segundo plano y pruebas

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 61 | Tarea en segundo plano con sesión propia y captura de excepciones | ✅ | `app/services/proveedores.py::notificar_alta_de_proveedor` — abre `SessionLocal()` propia, recibe solo datos simples, captura toda excepción. |
| 62 | Pruebas contra base aislada | ✅ | `tests/test_proveedores.py` usa las fixtures de `conftest.py` (SQLite en memoria). |
| 63 | `dependency_overrides` limpiados al terminar cada prueba | ✅ | Ya lo hacía `conftest.py` (`app.dependency_overrides.clear()`); reutilizado tal cual. |
| 64 | Pruebas del camino correcto y de cada error de negocio | ✅ | `tests/test_proveedores.py`: ~25 pruebas — creación, listado con filtros, PUT, PATCH, DELETE, suspensión/reactivación, y un caso por cada error (404, 409×3, 422×4, 401, 403×2). |
| 65 | Servicios externos e IA sustituidos por dobles | ✅ para proveedores | El fixture `_sin_correos_reales` reemplaza `enviar_correo` con `monkeypatch`; ninguna prueba abre un socket SMTP real. No aplica IA en este módulo. |

## Resumen

- **63 de 65 criterios cumplidos** por el módulo de proveedores, los
  componentes transversales nuevos (`app/core/`, `app/exceptions/dominio.py`)
  y el chatbot (`app/services/chatbot/`, `app/routes/chatbot.py`).
- **1 criterio (55)** requiere una migración a SQLAlchemy asíncrono que
  toca todo el proyecto existente, no solo el módulo nuevo — no se
  abordó por alcance.
- **1 criterio (9)** se cumple para proveedores pero no para los
  routers que ya existían antes de esta entrega (productos, usuarios,
  pedidos...), que siguen consultando la base de datos dentro de la
  función de ruta en vez de una capa `crud/` separada.

## Frontend — resumen de lo hecho fuera de la lista de chequeo (que es 100% backend)

- Rediseño completo de la paleta de color (`frontend/src/index.css`) a
  tonos pastel, con cada par texto/fondo verificado contra WCAG 2.1 AA.
- Foco visible global, área táctil mínima en móvil y enlace de salto al
  contenido.
- Página `GestionProveedores.jsx` con CRUD completo, filtros, y flujo de
  suspensión/reactivación con motivo.
- Selector de proveedor en `GestionProductos.jsx` (solo proveedores
  activos) y columna de proveedor en la tabla del catálogo.
