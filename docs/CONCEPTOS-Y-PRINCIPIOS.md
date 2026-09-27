# Conceptos y principios — guía de estudio con ejemplos de Dulce Esencia

Cada concepto se responde en tres partes: **definición corta**, **dónde está en TU proyecto** y **qué decir en la sustentación**.

> En tu lista aparece «Gerencia»; asumí que se refiere a **Herencia** (es el concepto que acompaña a objeto, clase y polimorfismo). Si tu instructor se refería a otra cosa, avísame y lo ajusto.

---

## 1. Clase
**Definición:** plantilla que describe atributos (datos) y métodos (comportamiento) de un tipo de cosa. No ocupa datos por sí sola.
**En el proyecto:** `class Usuario(Base)` en `backend/app/models/usuario.py` (define columnas: nombre, correo, rol…), `class PagoCrear(BaseModel)` en `schemas/pago.py` (define qué datos acepta crear un pago), `class PaymentService` en `services/pagos/payment_service.py`.
**Decir:** "Una clase es el molde; `Usuario` describe cómo es un usuario, pero no es ningún usuario en particular."

## 2. Objeto
**Definición:** una **instancia** de una clase, con valores concretos en memoria.
**En el proyecto:** en `routes/productos.py`: `producto = Producto(**datos.model_dump())` crea un objeto `Producto`; `db.add(producto); db.commit()` lo guarda como una fila. Al revés, `db.get(Pedido, 5)` lee una fila y la **convierte en un objeto** `Pedido`.
**Decir:** "El objeto es el ejemplar: `Producto(titulo='Rosa Imperial', precio=210000)`. La clase es el molde y el objeto es la pieza fundida."

## 3. Herencia
**Definición:** una clase hija reutiliza y especializa a una clase padre (`hija(Padre)`).
**En el proyecto:**
- `class Usuario(Base)`, `class Producto(Base)`… todos heredan de `Base` (`app/database.py`, `DeclarativeBase` de SQLAlchemy): así SQLAlchemy sabe qué clases son tablas.
- `class PagoValidacionException(PagoException)` (`exceptions/pagos.py`): hereda el comportamiento base y solo cambia el código HTTP y el `code`.
- `class WompiProvider(PaymentProvider)` hereda la interfaz de proveedor de pago.
- `class RolUsuario(str, enum.Enum)`: herencia múltiple (es texto y enumeración a la vez).
**Decir:** "Evita repetir código: la lógica común vive en el padre y cada hijo solo agrega lo suyo."

## 4. Polimorfismo
**Definición:** objetos distintos responden al **mismo mensaje** (método) cada uno a su manera; quien llama no necesita saber cuál es cuál.
**En el proyecto — el mejor ejemplo:** `PaymentProvider` (`services/pagos/payment_provider.py`) es una clase **abstracta** (`ABC`) con métodos `create_payment`, `get_payment`, `validate_webhook`… `WompiProvider` los implementa. `PaymentService` hace `proveedor.create_payment(...)` sin saber si es Wompi, Stripe o PayU; `payment_factory.obtener_proveedor("wompi")` decide cuál objeto entregar.
Otro: `PagoException` y sus hijas sobrescriben `status_code` y `code`; el manejador de errores trata a todas por igual y cada una responde distinto.
**Decir:** "Si mañana quiero cobrar con otro proveedor, creo `OtroProvider(PaymentProvider)` y lo registro en la fábrica; **no toco** `PaymentService` ni las rutas."

## 5. Abstracción y encapsulamiento (los que suelen acompañar)
- **Abstracción:** mostrar solo lo esencial. `PaymentProvider` define *qué* debe hacer un proveedor, no *cómo*.
- **Encapsulamiento:** ocultar detalles internos. En `PaymentService` los atributos `_db`, `_repo`, `_settings` llevan `_` (uso interno); las rutas solo llaman a `crear_pago`, `sincronizar_pago`, etc. En el chatbot local `_normalizar` y `_contiene` son privadas del módulo.

## 6. Principios SOLID aplicados
| Principio | Dónde se ve |
|---|---|
| **S** — una sola responsabilidad | `routes/` recibe HTTP, `services/` tiene la lógica de negocio, `repositories/` habla con la BD, `schemas/` valida, `models/` mapea tablas. |
| **O** — abierto/cerrado | Añadir un proveedor de pago = archivo nuevo + registro en la fábrica, sin modificar `PaymentService`. |
| **L** — sustitución de Liskov | Cualquier `PaymentProvider` (hoy `WompiProvider`) puede usarse donde se espera el tipo base. |
| **I** — segregación de interfaces | Interfaces pequeñas: el proveedor no sabe de pedidos; el servicio de correo solo expone `enviar_*`. |
| **D** — inversión de dependencias | `PaymentService` depende de la **abstracción** `PaymentProvider`, y FastAPI **inyecta** la sesión con `Depends(get_db)`. |

Patrones que puedes nombrar: **Factory** (`payment_factory.py`), **Strategy** (proveedores intercambiables), **Repository** (`repositories/`), **Máquina de estados** (`services/pagos/transiciones.py`: qué estados de pago pueden seguir a cuáles), **Inyección de dependencias** (`Depends`), **Idempotencia** (`Idempotency-Key`).

---

## 7. «¿En qué proceso/archivo se convierten las clases en objetos?»
La respuesta corta: **en tiempo de ejecución, cuando Python instancia la clase** (`NombreClase(...)`). En Dulce Esencia ocurre en cuatro momentos:

1. **Arranque** — `uvicorn app.main:app` importa `backend/app/main.py`, que ejecuta `app = FastAPI(...)`: ese es el primer objeto (la aplicación). Ahí mismo se crean los objetos `APIRouter` y los *middlewares* (CORS, límite de peticiones).
2. **Conexión a la BD** — `app/database.py` crea el `engine` y la fábrica de sesiones; `Base.metadata.create_all()` (dentro de `sincronizar_esquema()`, invocado en el `lifespan` de `main.py`) **lee las clases modelo** y crea las tablas en MySQL.
3. **Cada petición HTTP** — FastAPI convierte el JSON en un objeto Pydantic (`PagoCrear(**json)`, con validación), `Depends(get_db)` crea una `Session`, `get_current_user` devuelve un objeto `Usuario` cargado desde la fila de la tabla, y la ruta crea objetos de dominio (`Producto(...)`, `Usuario(...)` en `routes/*.py`). `PaymentService(db, settings)` se instancia en `routes/pagos.py::get_payment_service`, y `obtener_proveedor()` fabrica el `WompiProvider`.
4. **Frontend** — `frontend/src/main.jsx` ejecuta `createRoot(...).render(<App />)`: React convierte los componentes (funciones) en elementos y los pinta en el navegador.

**Traducción SQLAlchemy (ORM):** *fila ↔ objeto*. `db.query(Usuario)…` → objetos `Usuario`; `db.add(obj); commit()` → fila nueva.

---

## 8. Utilidad de cada carpeta/componente del proyecto

**Raíz:** `README.md` (cómo instalar y correr), `docs/` (esta documentación), `.github/workflows/` (CI/CD), `.gitignore`.

**`backend/`**
| Carpeta / archivo | Para qué sirve |
|---|---|
| `app/main.py` | **Punto de entrada.** Crea la app FastAPI, registra routers, CORS, límite de peticiones y la documentación `/docs`. |
| `app/config.py` | Lee las **variables de entorno** (`.env`) con pydantic-settings: llaves, BD, SMTP, Wompi. |
| `app/database.py` | Conexión (engine), sesión (`get_db`) y `Base` de los modelos. |
| `app/auth.py` | Hash bcrypt, creación/lectura de **JWT**, `get_current_user`, `requiere_rol`. |
| `app/rate_limit.py` | Límites de intentos (login, registro) contra fuerza bruta. |
| `app/models/` | Clases que representan **tablas** (SQLAlchemy). |
| `app/schemas/` | Clases **Pydantic**: validan lo que entra y definen lo que sale (nunca exponen `password_hash`). |
| `app/routes/` | **Endpoints** HTTP agrupados por recurso (productos, pedidos, pagos, chatbot…). |
| `app/services/` | **Lógica de negocio**: pagos (`pagos/`), chatbot (`chatbot/`), correos (`notificaciones.py`). |
| `app/repositories/` | Acceso a datos con consultas explícitas (usuarios, pagos). |
| `app/integrations/wompi/` | Cliente HTTP de Wompi y verificación de la firma del webhook. |
| `app/exceptions/` | Excepciones propias del módulo de pagos. |
| `app/utils/` | Utilidades: paginación, búsqueda segura, facturas PDF, reportes. |
| `database/schema_fastapi.sql` | Script SQL para crear la base en XAMPP. |
| `tests/` | Pruebas automáticas con pytest. |
| `uploads/` | Imágenes de productos servidas en `/uploads/...`. |
| `postman-fastapi/`, `docs/` | Colección de Postman y documentación del módulo de pagos. |
| `Dockerfile` | Imagen para desplegar el backend. |

**`frontend/`** (React + Vite)
| Carpeta | Para qué sirve |
|---|---|
| `src/main.jsx`, `App.jsx` | Arranque de React y **rutas** (react-router) con `ProtectedRoute`. |
| `src/pages/` | Pantallas: Login, Checkout, Pedidos, `PagoResultado`… |
| `src/components/` | Piezas reutilizables (Input, Button, tablas de gestión, modales). |
| `src/context/` | Estado global: sesión (`AuthContext`) y carrito (`CartContext`). |
| `src/hooks/` | Hooks propios: `useAuth`, `useForm` (validación de formularios). |
| `src/utils/api.js` | **Cliente HTTP centralizado** (URL por variable de entorno, token, conversión de nombres). |
| `src/utils/validators.js` | Validaciones de formularios en el cliente. |
| `.env.example` | `VITE_API_URL`: dirección del backend. |

---

## 9. Chat bot gratuito
Ver [CHATBOT-GRATUITO.md](CHATBOT-GRATUITO.md): funciona **sin costo y sin internet** (reglas + catálogo real) y, opcionalmente, con proveedores de IA de capa gratuita.

## 10. Preguntas rápidas de repaso
- ¿Diferencia entre clase y objeto? → molde vs. ejemplar.
- ¿Qué es un ORM? → traduce filas ↔ objetos (SQLAlchemy).
- ¿Diferencia entre modelo y schema? → el modelo es la **tabla**; el schema valida los **datos de la API**.
- ¿Por qué `Depends(get_db)`? → inyección de dependencias: FastAPI crea y cierra la sesión por petición.
- ¿Qué pasa si el webhook llega dos veces? → es **idempotente**: la segunda vez no cambia nada.
- ¿Por qué no confías en el monto que manda el navegador? → el servidor lo compara contra `pedido.total`.
