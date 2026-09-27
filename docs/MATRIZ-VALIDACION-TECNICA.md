# Matriz de validación técnica — Proyecto integrador React + FastAPI

**SENA — Centro de Servicios y Gestión Empresarial · Coordinación de Teleinformática, Regional Antioquia**

| | |
|---|---|
| **Ficha** | 3406211 |
| **Programa** | Tecnólogo en Análisis y Desarrollo de Software (228118) |
| **Aprendiz** | Luisa Fernanda Arias Puerta |
| **Instructor** | César Augusto Moreno Mena |
| **Proyecto evaluado** | Dulce Esencia Pastelería (FastAPI + React) |

> **Nota:** el formato original dice *"Pastelería – Catálogo de tortas"*. El código entregado es
> Dulce Esencia Pastelería; confirma con el instructor cuál nombre debe ir en el formato oficial.

**Cómo leer esta matriz.** La columna "Cumple" es una **autoevaluación con evidencia**: cada fila apunta
al archivo donde se ve el criterio y, cuando aplica, a la prueba automática que lo verifica.
Las pruebas se ejecutan con `cd backend && python -m pytest tests -v` (SQLite en memoria; no requiere MySQL).
La firma y el resultado general los define el instructor.

Leyenda: ✅ Cumple · 🟡 Cumple con observación · ⏳ Lo evalúa el instructor

## 1. Diseño y fundamentos REST

| Criterio | Estado | Evidencia / Observaciones |
|---|---|---|
| Endpoints con criterio REST (recurso – verbo – ruta – código) | ✅ | `backend/app/routes/*.py`. Recursos en plural (`/api/productos`), verbos GET/POST/PUT/PATCH/DELETE, códigos 200/201/404/409/422/401/403. Catálogo completo en [MANUAL-TECNICO.md](MANUAL-TECNICO.md#6-endpoints) (84 operaciones generadas desde OpenAPI). |
| Parámetros de ruta y consulta con validación (Query, Path, Annotated / type hints) | ✅ | `Query(ge=1, le=…)` (≈60 usos), type hints en rutas (`/productos/abc` → 422) y `Annotated[int, Path(ge=1)]` en `routes/productos.py` (`IdProducto`). Pruebas: `test_productos_crud.py::test_id_de_ruta_menor_a_1…`, `test_parametro_de_consulta_invalido_422`. |
| CRUD completo sobre los recursos principales | ✅ | Productos: `POST/GET/GET{id}/PUT/PATCH/DELETE` con roles. También servicios, cupones, PQR, usuarios. Prueba: `tests/test_productos_crud.py` (13 casos). |

## 2. Modelado y validación de datos (Pydantic)

| Criterio | Estado | Evidencia / Observaciones |
|---|---|---|
| Esquemas Pydantic v2 separados de entrada y salida (Create / Update / Response) | ✅ | `backend/app/schemas/`: `ProductoCrear` / `ProductoSalida`, `UsuarioCrear` / `UsuarioSalida`, `PQRCrear` / `PQRActualizar` / `PQRSalida`, `PagoCrear` / `PagoSalida`. La salida nunca incluye `password_hash` (`test_auth.py::test_login_correcto…`). |
| Validaciones propias del dominio (field_validator / model_validator / Field) | ✅ | 22 archivos de schemas con `field_validator`; `model_validator` en `schemas/venta.py` y `schemas/cupon.py`; `Field(gt=0, max_length=…)`. Ej.: contraseña 8–72 bytes, moneda soportada, cupón con vigencia coherente. |

## 3. Persistencia de datos (SQLAlchemy)

| Criterio | Estado | Evidencia / Observaciones |
|---|---|---|
| Al menos dos entidades relacionadas con SQLAlchemy 2.0 | ✅ | `backend/app/models/`: 13 archivos con `Mapped[...]`/`mapped_column` y `relationship(...)` (Usuario↔Pedido↔PedidoItem↔Producto, Venta↔Factura, Conversación↔Mensaje…). Análisis en [NORMALIZACION-BD.md](NORMALIZACION-BD.md). |
| CRUD persistente en BD real (SQLite/PostgreSQL), no en memoria | ✅ | MySQL/MariaDB (XAMPP) con PyMySQL: `app/database.py`, `database/schema_fastapi.sql`. 🟡 Las pruebas automáticas usan SQLite en memoria por rapidez; la persistencia contra MySQL real **no la ejecuté yo**, verifícala con `uvicorn` + XAMPP. |

## 4. Autenticación y autorización

| Criterio | Estado | Evidencia / Observaciones |
|---|---|---|
| Inicio de sesión con JWT (OAuth2 password u equivalente) | 🟡 | `POST /api/auth/login` (correo + contraseña bcrypt) devuelve JWT firmado HS256 que se envía como `Authorization: Bearer`. Es el **equivalente** del flujo password, pero con cuerpo JSON y `HTTPBearer`, no con `OAuth2PasswordRequestForm` (form-data). Si el instructor exige la forma literal, el cambio es pequeño. Pruebas: `tests/test_auth.py::TestLogin`, `TestProteccionPorToken`. |
| Protege endpoints sensibles según autenticación / rol | ✅ | `requiere_rol("admin","empleado")` (`app/auth.py`). Pruebas por rol: `test_auth.py::TestAutorizacionPorRol`, `test_productos_crud.py` (401 sin token, 403 cliente). Además: `token_version` revoca tokens, límite de 10 intentos/15 min (429). |

## 5. Manejo de errores y middlewares

| Criterio | Estado | Evidencia / Observaciones |
|---|---|---|
| Errores estandarizados (HTTPException, 404/422, mensajes claros) | ✅ | `HTTPException` con mensajes en español en las rutas; 422 automático de Pydantic; el módulo de pagos usa su jerarquía `PagoException` con formato `{success, error:{code,message}}` (`app/exceptions/pagos.py`). Respuestas documentadas en `/docs`. |
| CORS configurado para el frontend React | ✅ | `CORSMiddleware` en `app/main.py`; orígenes tomados de `FRONTEND_URL` (variable de entorno). También `SlowAPIMiddleware` (límite de peticiones). |

## 6. Asincronía y tareas en segundo plano

| Criterio | Estado | Evidencia / Observaciones |
|---|---|---|
| Al menos un endpoint o flujo con async/await | 🟡 | `async def subir_imagen_producto` con `await imagen.read()` (`routes/productos.py`). El resto son `def` a propósito: SQLAlchemy sincrónico + PyMySQL bloquearía el event loop en `async def`; FastAPI ejecuta las `def` en un pool de hilos. Está explicado en [COMPARATIVA-FASTAPI-DRF.md](COMPARATIVA-FASTAPI-DRF.md). |
| BackgroundTasks para al menos una tarea no bloqueante | ✅ | `BackgroundTasks` en `POST /api/pqr` (confirmación), `POST /api/usuarios/registro` (verificación) y `POST /api/usuarios/recuperar` → `app/services/notificaciones.py`. Pruebas: `tests/test_tareas_segundo_plano.py` (la tarea corre; un SMTP caído no rompe la operación). |

## 7. Integración de Inteligencia Artificial

| Criterio | Estado | Evidencia / Observaciones |
|---|---|---|
| Endpoint que integra un modelo propio o servicio de IA externo | ✅ | `POST /api/chatbot/mensaje` → `services/chatbot/ai_service.py` (cliente compatible con OpenAI: OpenAI, Groq, Gemini, OpenRouter, Ollama) con **respaldo local gratuito** `faq_service.py`. Ver [CHATBOT-GRATUITO.md](CHATBOT-GRATUITO.md). 🟡 No probé una llamada real a un proveedor de IA (no hay API key en este entorno); sí probé el camino local. |
| Credenciales/llaves por variables de entorno, nunca en el código | ✅ | `app/config.py` (pydantic-settings) + `.env.example`. `.gitignore` excluye `.env`. ⚠️ El zip anterior incluía `backend/.env`: **si lo compartiste o lo subiste, cambia `SECRET_KEY`**. |

## 8. Documentación y preparación para despliegue

| Criterio | Estado | Evidencia / Observaciones |
|---|---|---|
| `/docs` y `/redoc` personalizados con tags, descripciones y ejemplos | ✅ | `app/main.py`: descripción con guía de autenticación, 18 tags descritos, versión, contacto; ejemplos en `LoginEntrada`, `ProductoCrear`, `PQRCrear`, `PagoCrear`, `ChatbotMensajeEntrada`; `summary` y `responses` (401/403/404/409/422) en el CRUD de productos. Abrir `http://localhost:8000/docs`. 🟡 Los demás routers tienen resumen automático; se puede ampliar. |
| README con instalación/ejecución, `requirements.txt`, `.env.example` | ✅ | `README.md`, `backend/requirements.txt`, `backend/.env.example`, `frontend/.env.example`. Más `backend/Dockerfile` y CI/CD en `.github/workflows/`. |

## 9. Pruebas (Testing)

| Criterio | Estado | Evidencia / Observaciones |
|---|---|---|
| Pytest / TestClient que cubran al menos el CRUD y la autenticación | ✅ | `backend/tests/`: **112 pruebas pasan, 3 se saltan** (la de extremo a extremo que necesita un servidor real). `test_auth.py` (21), `test_productos_crud.py` (13), `test_seguridad_sqli.py` (27), `test_pagos.py` (19) + `test_pagos_pedido.py` (12), `test_chatbot_local.py` (13), `test_tareas_segundo_plano.py`. |

## 10. Frontend — React

| Criterio | Estado | Evidencia / Observaciones |
|---|---|---|
| Cliente HTTP centralizado con URL por variable de entorno | ✅ | `frontend/src/utils/api.js` (`apiRequest`, `import.meta.env.VITE_API_URL`; conversión camelCase↔snake_case; manejo de 401). |
| CRUD funcional desde la interfaz (listar, crear, editar, eliminar) | ✅ | Panel de gestión (`components/`, p. ej. `GestionProductos.jsx`) sobre `crearProducto/actualizarProducto/eliminarProducto`. 🟡 Verificado por lectura de código y `vite build`; no lo probé en un navegador. |
| Formularios reflejan esquemas Create/Update y validan en cliente sin sustituir al servidor | ✅ | `utils/validators.js` + hook `hooks/useForm.js` (mismas reglas que los `field_validator`); el backend revalida siempre. Login en **dos pasos** (`pages/Login.jsx`). |
| Estados de carga y de error frente a la API | ✅ | Patrón `cargando / error` en las páginas (`PedidoDetalle.jsx`, `Checkout.jsx`, `PagoResultado.jsx`). `npm run lint` → 0 errores; `npm run build` compila. |

## 11. Comparativa técnica y sustentación

| Criterio | Estado | Evidencia / Observaciones |
|---|---|---|
| Análisis comparativo FastAPI vs Django REST Framework aplicado al proyecto | ✅ | [COMPARATIVA-FASTAPI-DRF.md](COMPARATIVA-FASTAPI-DRF.md). |
| El aprendiz sustenta con claridad el funcionamiento y las decisiones técnicas | ⏳ | Lo evalúa el instructor. Material de estudio: [CONCEPTOS-Y-PRINCIPIOS.md](CONCEPTOS-Y-PRINCIPIOS.md), [SEGURIDAD-SQL-INJECTION.md](SEGURIDAD-SQL-INJECTION.md), [NORMALIZACION-BD.md](NORMALIZACION-BD.md), [MANUAL-TECNICO.md](MANUAL-TECNICO.md). |

## Resumen

| Total de criterios | ✅ Cumple | 🟡 Cumple con observación | ⏳ Del instructor |
|---|---|---|---|
| 24 | 21 | 2 (4.1 y 6.1) | 1 (11.2) |

Varias filas ✅ traen además notas 🟡 sobre lo que no pude verificar en vivo (ver el último párrafo).

**Resultado general propuesto:** *Aprueba con observaciones* — a decisión del instructor.

**Límites de esta autoevaluación (lo que NO verifiqué):** ejecución contra MySQL real, checkout real en el sandbox de Wompi,
llamadas reales a un proveedor de IA, ejecución de los workflows en GitHub, y el comportamiento del frontend en un navegador.
