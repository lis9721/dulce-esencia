# Comparativa técnica: FastAPI vs Django REST Framework (DRF) aplicada a Dulce Esencia

## 1. Idea central
| | **FastAPI** (lo que usa el proyecto) | **Django REST Framework** |
|---|---|---|
| Naturaleza | Micro-framework moderno sobre Starlette + Pydantic. Solo lo necesario; el resto se elige. | Extensión de **Django**, un framework "todo incluido" (ORM, admin, auth, migraciones). |
| Estilo | Funciones con *type hints*; la validación sale de los tipos. | Clases (`ViewSet`, `Serializer`, `Router`). |
| Documentación | **OpenAPI/Swagger automático** (`/docs`, `/redoc`) desde el código. | Requiere `drf-spectacular` o `drf-yasg`. |
| Asincronía | Nativa (`async def`, ASGI). | Soporte parcial; el ecosistema es mayormente síncrono (WSGI). |

## 2. Mismo problema, dos enfoques (ejemplos del proyecto)

| Necesidad | En Dulce Esencia con FastAPI | Cómo sería en DRF |
|---|---|---|
| Validar entrada | `class ProductoCrear(BaseModel)` + `Field` + `field_validator` (`schemas/producto.py`) | `class ProductoSerializer(serializers.ModelSerializer)` + `validate_*` |
| Modelo/BD | SQLAlchemy 2.0 (`models/`), esquema SQL propio | Django ORM + **migraciones automáticas** (`makemigrations`) |
| CRUD | 5 funciones en `routes/productos.py` con decoradores | Un `ModelViewSet` + `router.register(...)` (mucho menos código) |
| Autenticación | JWT propio: `app/auth.py` (bcrypt + `HTTPBearer` + `requiere_rol`) | `SimpleJWT` + `permission_classes` |
| Panel de administración | Hecho a mano en React (`GestionProductos`…) | **Django Admin gratis** |
| Tareas en segundo plano | `BackgroundTasks` (correo de PQR/registro) | Celery (más potente, más infraestructura) |
| Pruebas | `TestClient` + pytest (`tests/`) | `APITestCase` / pytest-django |
| Documentación de la API | Automática y personalizada (`main.py`) | Paquete adicional |

## 3. Ventajas y desventajas

**FastAPI**
- ➕ Rendimiento alto, validación automática, documentación viva, poco código repetitivo de validación, ideal para APIs consumidas por React.
- ➕ Flexibilidad: el proyecto pudo montar su módulo de pagos con Factory/Strategy sin pelear con el framework.
- ➖ Hay que **armar más piezas a mano**: autenticación, permisos, migraciones (aquí se usa un script SQL + `sincronizar_esquema`), panel admin.
- ➖ Ecosistema y convenciones más jóvenes; cada proyecto se organiza distinto.

**DRF**
- ➕ "Baterías incluidas": admin, ORM, migraciones, permisos, paginación, filtros y mucha comunidad.
- ➕ Muy productivo para CRUD estándar y paneles administrativos.
- ➖ Más pesado y rígido; la validación está en serializers (más verbosa); asincronía limitada; la doc OpenAPI no viene incluida.

## 4. Decisiones concretas del proyecto (y por qué)
1. **Se eligió FastAPI** porque el frontend es una SPA en React que consume una API JSON: importa la documentación automática, la validación de tipos y el rendimiento; no se necesitaba HTML renderizado ni el admin de Django.
2. **Funciones `def` sincrónicas en casi todas las rutas** y `async def` solo donde hay E/S asíncrona real (`subir_imagen_producto`, `await imagen.read()`). Razón: SQLAlchemy sincrónico + PyMySQL **bloquean**; dentro de un `async def` congelarían el event loop. FastAPI ejecuta las `def` en un pool de hilos, sin bloquear el servidor. Convertir todo a async exigiría `AsyncSession` y un driver asíncrono (`aiomysql`/`asyncmy`).
3. **Pydantic v2** separa esquemas de entrada/salida: el `password_hash` nunca sale porque no está en `UsuarioSalida`.
4. **Sin migraciones formales**: se usa `schema_fastapi.sql` + `sincronizar_esquema()`. En DRF/Django esto lo resolvería `makemigrations`; en FastAPI la alternativa profesional es **Alembic** (mejora futura recomendada).

## 5. ¿Cuándo usaría cada uno?
- **FastAPI:** API para SPA/móvil, microservicios, integraciones con IA/pagos, cuando se quiere rendimiento y documentación automática.
- **DRF:** aplicación con muchas entidades y un panel administrativo, equipos que prefieren convenciones estrictas, MVPs donde el admin de Django ahorra semanas.

## 6. Respuesta modelo para la sustentación
> "Usé FastAPI porque mi frontend es React y necesito una API rápida, tipada y autodocumentada. Con Pydantic valido la entrada
> sin escribir código repetido y con SQLAlchemy controlo el modelo de datos. Lo que en DRF me daría hecho —admin, migraciones y
> permisos— aquí lo implementé yo: el panel en React, `requiere_rol` para permisos y un script SQL para el esquema. Si el
> proyecto fuera un backoffice con muchas tablas, DRF me habría ahorrado tiempo; para una tienda con API consumida por React y
> pagos/IA, FastAPI encaja mejor."
