# Dulce Esencia Pastelería

> **Nota (Cuarto Avance):** el backend de este proyecto se migró de
> Node/Express a **Python + FastAPI**, conservando el mismo frontend
> React + Vite y la misma base de datos MySQL/XAMPP. El backend Node
> original (avance anterior) ya no forma parte de esta entrega; el
> punto de entrada ahora es `backend/app/main.py`, corrido con
> `uvicorn`. Varias secciones de abajo describían el backend Node
> (`server.js`, npm, cookies httpOnly — hoy la sesión usa JWT en `Authorization: Bearer` —, `PUT` para cambiar estado,
> etc.) — la sección "1. Base de datos" y "2. Backend" ya están
> actualizadas a FastAPI; el resto del documento sigue siendo una
> referencia útil de las reglas de negocio (roles, permisos, carrito,
> checkout, facturación), aunque algún detalle puntual de implementación
> (nombre de archivo, librería usada) pueda diferir del código Python
> real en `backend/app/`.

Proyecto React + Vite (frontend) y **Python + FastAPI + MySQL** (backend),
pensado para correr la base de datos con **XAMPP**. Incluye autenticación
con JWT, roles de usuario (cliente / empleado / admin), un panel privado
con operaciones CRUD y validaciones en tiempo real en el frontend y en el
backend.

## Documentación técnica (quinto avance)

| Documento | Contenido |
|---|---|
| [`docs/MATRIZ-VALIDACION-TECNICA.md`](docs/MATRIZ-VALIDACION-TECNICA.md) | Matriz del SENA diligenciada: cada criterio con su evidencia |
| [`docs/MANUAL-TECNICO.md`](docs/MANUAL-TECNICO.md) | Arquitectura, instalación, variables de entorno, endpoints, pagos (Wompi), CI/CD y despliegue |
| [`docs/SEGURIDAD-SQL-INJECTION.md`](docs/SEGURIDAD-SQL-INJECTION.md) | Consultas preparadas, login en dos pasos y pruebas |
| [`docs/NORMALIZACION-BD.md`](docs/NORMALIZACION-BD.md) | 1FN/2FN/3FN, diagrama ER y desnormalizaciones justificadas |
| [`docs/CONCEPTOS-Y-PRINCIPIOS.md`](docs/CONCEPTOS-Y-PRINCIPIOS.md) | Objeto, clase, herencia, polimorfismo, SOLID y utilidad de cada carpeta |
| [`docs/COMPARATIVA-FASTAPI-DRF.md`](docs/COMPARATIVA-FASTAPI-DRF.md) | FastAPI vs Django REST Framework aplicado al proyecto |
| [`docs/CHATBOT-GRATUITO.md`](docs/CHATBOT-GRATUITO.md) | Chatbot local sin costo y proveedores de IA con capa gratuita |
| [`docs/DESPLIEGUE-VERCEL-RENDER.md`](docs/DESPLIEGUE-VERCEL-RENDER.md) | Guía paso a paso: frontend en Vercel, backend en Render, BD MySQL en la nube |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | Alternativa: un solo proyecto de Vercel (Services) + TiDB, sin CORS que configurar |

**Inicio rápido**

```bash
# Backend  (http://localhost:8000 · documentación interactiva en /docs)
cd backend && python -m venv .venv && .venv\Scripts\activate   # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt && cp .env.example .env         # edita .env
uvicorn app.main:app --reload

# Frontend (http://localhost:5173)
cd frontend && cp .env.example .env && npm ci && npm run dev

# Pruebas del backend (no necesitan MySQL)
cd backend && python -m pytest tests -v
```

CI/CD: `.github/workflows/ci.yml` (pruebas + lint + build) y `cd.yml` (imagen Docker en GHCR). El pago con tarjeta usa
**Wompi** y los correos salen en segundo plano (`BackgroundTasks`).

## Organización del proyecto

```
essentia/
├── backend/
│   ├── app/
│   │   ├── main.py                # Punto de entrada — uvicorn app.main:app
│   │   ├── config.py              # Settings (lee backend/.env) + validación de SECRET_KEY
│   │   ├── database.py            # Engine SQLAlchemy + get_db()
│   │   ├── auth.py                # Emisión/verificación de JWT, requiere_rol()
│   │   ├── rate_limit.py          # Límites de peticiones (slowapi)
│   │   ├── models/                # Modelos SQLAlchemy (usuario, producto, servicio, pedido, ...)
│   │   ├── schemas/                # Esquemas Pydantic (validación de entrada/salida)
│   │   ├── routes/                # usuarios, productos, servicios, carrito, pedidos, cupones, roles, contacto
│   │   └── utils/                 # paginación, cupones, factura en PDF (reportlab)
│   ├── database/
│   │   └── schema.sql             # Script para crear la BD y las tablas (MySQL)
│   ├── postman-fastapi/           # Colección Postman actualizada para FastAPI
│   ├── postman-403-roles/         # Colección de pruebas de control de acceso por rol
│   ├── docs/                      # Notas de verificación (matriz de roles, evidencias HTTP)
│   ├── .env / .env.example        # Variables de entorno del backend Python
│   └── requirements.txt           # Dependencias (pip)
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ui/                # Input, Select, Button, Modal, Icon (reutilizables)
│       │   ├── Header.jsx         # Navbar (se adapta según sesión iniciada)
│       │   ├── Footer.jsx
│       │   ├── ProtectedRoute.jsx # Bloquea rutas privadas por sesión y/o rol
│       │   ├── RegisterModal.jsx
│       │   └── RecoverPassword.jsx
│       ├── context/
│       │   ├── AuthContext.jsx    # Estado global de sesión (usuario, token, login/logout)
│       │   └── CartContext.jsx    # Estado global del carrito (backend si hay sesión, localStorage si no)
│       ├── hooks/
│       │   ├── useForm.js         # Validación en tiempo real reutilizable
│       │   ├── useAuth.js
│       │   └── useCart.js
│       ├── pages/
│       │   ├── Index.jsx, QuienesSomos.jsx, Contacto.jsx, Login.jsx
│       │   ├── Tienda.jsx         # Catálogo real (GET /api/productos), la única página para comprar
│       │   ├── Carrito.jsx        # Revisar/editar el carrito (Fase 1 de la tienda)
│       │   ├── Panel.jsx          # Panel privado, pestañas según rol
│       │   └── panel/
│       │       ├── MiPerfil.jsx           # Ver/editar datos propios + cambiar contraseña
│       │       ├── GestionProductos.jsx   # CRUD de productos (admin/empleado)
│       │       ├── GestionServicios.jsx   # CRUD de servicios (admin/empleado)
│       │       ├── GestionUsuarios.jsx    # CRUD de usuarios (admin) / solo lectura (empleado)
│       │       ├── MisPedidos.jsx         # Pedidos propios de cualquier usuario autenticado
│       │       ├── GestionPedidos.jsx     # Todos los pedidos + cambio de estado (admin/empleado)
│       │       └── GestionCupones.jsx     # CRUD de cupones de descuento (solo admin)
│       └── utils/
│           ├── api.js             # Helper de fetch (agrega el JWT automáticamente)
│           └── validators.js      # Funciones de validación por campo
│
├── CRITERIOS_ACEPTACION.md        # Historias de usuario + criterios Given/When/Then
└── README.md
```

## 1. Base de datos (XAMPP)

1. Abre el **Panel de control de XAMPP** e inicia los módulos **Apache** y
   **MySQL**.
2. Ve a `http://localhost/phpmyadmin`.
3. Entra a la pestaña **Importar**, selecciona el archivo
   `backend/database/schema.sql` y dale a **Continuar**.
   - Esto crea la base de datos `essentia_db` con todas las tablas del
     proyecto: `usuarios` (con columna `rol`), `roles`/`permisos`/
     `rol_permisos`, `productos` (ya con los 10 productos del
     carrusel, con precio, stock, sku y estado activo/inactivo),
     `servicios` (con 5 servicios de ejemplo), `carritos`/
     `carrito_items`, `pedidos`/`pedido_items`, `cupones` y
     `mensajes_contacto`.
4. Si tu instalación de XAMPP tiene contraseña para el usuario `root`,
   o usas otro puerto, ajusta `backend/.env` (ver siguiente paso).

## 2. Backend (Python + FastAPI)

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows — en Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Por defecto queda corriendo en `http://127.0.0.1:8000`. Documentación
interactiva automática (Swagger UI) en `http://127.0.0.1:8000/docs`.

El archivo `backend/.env` ya trae los valores por defecto de XAMPP:

```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=essentia_db
```

Al arrancar, la consola te dirá si logró conectarse a MySQL. Si ves un
error, confirma que MySQL esté iniciado en XAMPP y que hayas importado el
`schema.sql`.

### Endpoints de la API (operaciones CRUD)

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/api/salud/db` | Pública | Confirma si la conexión a MySQL está activa |
| GET | `/api/productos` | Pública (ve inactivos si eres admin/empleado) | Lista productos, paginado. Filtros opcionales: `?familia=` (tortas/cupcakes/galletas/postres/hojaldres/panaderia), `?orden=precio_asc\|precio_desc` |
| GET | `/api/productos/:id` | Pública (ve inactivos si eres admin/empleado) | Obtiene un producto por id |
| POST | `/api/productos` | admin, empleado | Crea un producto (precio y familia obligatorios; stock/sku/pesoG/activo opcionales) |
| PUT | `/api/productos/:id` | admin, empleado | Edita un producto, incluyendo precio/stock/sku/familia/pesoG/activo |
| DELETE | `/api/productos/:id` | admin | Elimina un producto |
| GET | `/api/servicios` | Pública (ve inactivos si eres admin/empleado) | Lista servicios, paginado |
| GET | `/api/servicios/:id` | Pública (ve inactivos si eres admin/empleado) | Obtiene un servicio por id |
| POST | `/api/servicios` | admin, empleado | Crea un servicio (precio obligatorio; duración/imagen/código/activo opcionales) |
| PUT | `/api/servicios/:id` | admin, empleado | Edita un servicio |
| DELETE | `/api/servicios/:id` | admin | Elimina un servicio |
| GET | `/api/carrito` | Cualquier autenticado | Ve su propio carrito: items con subtotal + total |
| POST | `/api/carrito` | Cualquier autenticado | Agrega un producto (o suma cantidad si ya estaba) |
| PUT | `/api/carrito/:productoId` | Cualquier autenticado | Reemplaza la cantidad de un item ya en el carrito |
| DELETE | `/api/carrito/:productoId` | Cualquier autenticado | Quita un producto del carrito |
| DELETE | `/api/carrito` | Cualquier autenticado | Vacía el carrito completo |
| POST | `/api/carrito/fusionar` | Cualquier autenticado | Fusiona el carrito de invitado (localStorage) al iniciar sesión |
| POST | `/api/pedidos` | Cualquier autenticado | Checkout: crea el pedido a partir del carrito actual (ver más abajo) |
| GET | `/api/pedidos` | Cualquier autenticado | Lista sus propios pedidos (admin/empleado ven los de todos) |
| GET | `/api/pedidos/{id}` | Dueño del pedido, admin, empleado | Detalle completo de un pedido (cabecera + items) |
| PATCH | `/api/pedidos/{id}/estado` | admin, empleado | Cambia el estado del pedido (repone stock si se cancela) |
| GET | `/api/pedidos/{id}/factura` | Dueño del pedido, admin, empleado | Genera y descarga el PDF de la factura del pedido |
| POST | `/api/cupones/validar` | Cualquier autenticado | Preview: `{ codigo, subtotal }` → descuento que tendría, sin gastar un uso |
| GET | `/api/cupones` | admin | Lista todos los cupones (activos e inactivos), paginado |
| POST | `/api/cupones` | admin | Crea un cupón |
| PUT | `/api/cupones/{id}` | admin | Edita un cupón |
| DELETE | `/api/cupones/{id}` | admin | Elimina un cupón |
| POST | `/api/usuarios/registro` | Pública | Crea un cliente (rol `cliente` siempre) |
| POST | `/api/auth/login` | Pública | Inicia sesión, devuelve `access_token` (JWT) en el body |
| GET | `/api/usuarios/perfil` | Cualquier autenticado | Devuelve los datos propios |
| PUT | `/api/usuarios/perfil` | Cualquier autenticado | Edita datos propios (nombre, dirección, teléfono) |
| PUT | `/api/usuarios/perfil/password` | Cualquier autenticado | Cambia la contraseña propia |
| GET | `/api/usuarios` | admin, empleado | Lista todos los usuarios |
| POST | `/api/usuarios` | admin | Crea un usuario directamente (elige el rol; queda activo y verificado) |
| PUT | `/api/usuarios/{id}/rol` | admin | Cambia el rol de otro usuario |
| PATCH | `/api/usuarios/{id}/estado` | admin | Activa/desactiva un usuario (`{ "activo": true\|false }`) sin borrarlo |
| DELETE | `/api/usuarios/{id}` | admin | Elimina un usuario |
| GET | `/api/productos/admin/todos` | admin, empleado | Catálogo completo (activos e inactivos) para el panel de gestión |
| GET | `/api/servicios/admin/todos` | admin, empleado | Catálogo completo (activos e inactivos) para el panel de gestión |
| POST | `/api/productos/imagen` | admin, empleado | Sube la imagen de un producto (`multipart/form-data`) |
| GET | `/api/roles` | admin | Lista los roles con sus permisos asociados |
| POST | `/api/contacto` | Pública | Guarda un mensaje del formulario de Contacto |

> El JWT viaja en el header `Authorization: Bearer <token>` (no en una
> cookie httpOnly) y se guarda en `localStorage` del navegador — ver
> `frontend/src/utils/api.js`. Las contraseñas se cifran con
> **bcrypt vía `passlib`** (no `bcrypt.compare()` de Node) y el PDF de
> la factura se genera con **`reportlab`** (no `pdfkit`).

### Roles de usuario

Cada fila de `usuarios` tiene una columna `rol` (`cliente`, `empleado` o
`admin`, por defecto `cliente`). El registro público **siempre** crea
clientes — nadie puede auto-asignarse `admin` o `empleado`. Para dar un
rol distinto:

1. Regístrate normalmente desde la web (queda como `cliente`).
2. En phpMyAdmin (o `mysql`), ejecuta:

```sql
UPDATE usuarios SET rol = 'admin' WHERE correo = 'tu_correo@ejemplo.com';
-- o rol = 'empleado'
```

3. Vuelve a iniciar sesión para que el nuevo token incluya el rol
   actualizado.

### Tablas `roles` y `permisos`

Además de la columna `usuarios.rol`, el esquema incluye tres tablas
relacionales dedicadas (punto 1 del enunciado): `roles`, `permisos` y
`rol_permisos` (relación muchos-a-muchos entre las dos anteriores),
con datos semilla ya cargados por `schema.sql` — 3 roles, 14 permisos
y sus 28 relaciones.

**Importante — cómo conviven estas tablas con el control de acceso
real:** la aplicación sigue autorizando cada petición por
`usuarios.rol` (el ENUM) + el middleware `verificarRol(...)`, exactamente
igual que antes. Las tablas `roles`/`permisos` no reemplazan eso — lo
**documentan** como datos relacionales consultables, para que existan
como tablas de verdad (no solo como un ENUM) sin arriesgar romper todo
el código que ya depende de ese ENUM (JWT, middlewares, frontend, y
los 241 tests del backend). `roles.nombre` se mantiene sincronizado a
mano con los 3 valores del ENUM.

Se pueden consultar con:

- `GET /api/roles` (admin, empleado): cada rol con la lista de
  permisos que tiene asociados (JOIN de las 3 tablas).
- `GET /api/roles/permisos` (admin, empleado): el catálogo completo
  de permisos, sin agrupar.

Si tu base de datos ya existía de un avance anterior sin estas tres
tablas, basta con volver a correr `schema.sql` completo — es
**idempotente**: usa `CREATE TABLE IF NOT EXISTS` y
`INSERT ... ON DUPLICATE KEY UPDATE`, así que se puede ejecutar varias
veces sin duplicar filas ni romper los datos que ya tenías.

Si tu base de datos ya existía de un avance anterior, corre antes la
línea de migración correspondiente (comentada en
`backend/database/schema.sql`):

```sql
-- Si la tabla no tenía columna "rol":
ALTER TABLE usuarios ADD COLUMN rol ENUM('cliente','empleado','admin') NOT NULL DEFAULT 'cliente' AFTER password_hash;

-- Si ya tenía "rol" pero solo con 'cliente'/'admin' (2do avance):
ALTER TABLE usuarios MODIFY COLUMN rol ENUM('cliente','empleado','admin') NOT NULL DEFAULT 'cliente';
```

Un admin también puede crear un usuario **directamente con el rol que
quiera** (sin pasar primero por el registro público + ascenso):

- Backend: `POST /api/usuarios` (solo admin). Pide los mismos campos
  que el registro público más `rol`, y crea la cuenta ya `verificado
  = 1` y `activo = 1` (un admin dando de alta a alguien manualmente
  no necesita el correo de verificación del flujo público).
- Frontend: botón "Agregar usuario" en `/panel/usuarios`
  (`components/ui/CrearUsuarioModal.jsx`), que reutiliza el mismo
  `useForm` y los mismos validadores que `RegisterModal.jsx`, más un
  `<Select>` para elegir el rol.

**Permisos por rol** (ver también `CRITERIOS_ACEPTACION.md`):

| Acción | Cliente | Empleado | Admin |
|---|---|---|---|
| Ver/editar su propio perfil y contraseña | ✅ | ✅ | ✅ |
| Ver el catálogo de productos | ✅ | ✅ | ✅ |
| Crear / editar productos | ❌ | ✅ | ✅ |
| Eliminar productos | ❌ | ❌ | ✅ |
| Ver el catálogo de servicios | ✅ | ✅ | ✅ |
| Crear / editar servicios | ❌ | ✅ | ✅ |
| Eliminar servicios | ❌ | ❌ | ✅ |
| Ver la lista de usuarios | ❌ | ✅ | ✅ |
| Cambiar el rol de un usuario / activarlo o desactivarlo / eliminarlo | ❌ | ❌ | ✅ |
| Aplicar un cupón en el carrito | ✅ | ✅ | ✅ |
| Crear / editar / eliminar cupones | ❌ | ❌ | ✅ |
| Ver los propios pedidos y descargar su factura | ✅ | ✅ | ✅ |
| Ver y cambiar el estado de los pedidos de toda la tienda | ❌ | ✅ | ✅ |

### Estado de usuario (Activo / Inactivo)

Cada fila de `usuarios` también tiene una columna `activo`
(`TINYINT(1)`, por defecto `1`). Es el mecanismo recomendado para
"apagar" una cuenta **sin borrarla** — así se conserva su historial
(pedidos, mensajes de contacto, etc.) en vez de perderlo con un
`DELETE`.

- `PATCH /api/usuarios/{id}/estado` (solo admin, body `{ "activo": false }`)
  activa o desactiva a otro usuario. Un admin no puede cambiar el
  estado de su propia cuenta (misma restricción que ya existía para
  `/rol`).
- Un usuario **inactivo** no puede iniciar sesión: `POST /api/auth/login`
  responde `403` aunque la contraseña sea correcta.
- Si la cuenta se desactiva **mientras la persona ya tiene sesión
  iniciada**, el corte de acceso aplica de inmediato en la siguiente
  petición protegida (no hay que esperar a que el JWT expire por su
  cuenta): `get_current_user` (`app/auth.py`) vuelve a consultar la
  fila y compara `token_version` en cada petición, igual que ya hacía
  para detectar cambios de rol o contraseña.
- En el frontend, `/panel/usuarios` (`GestionUsuarios.jsx`) muestra una
  columna "Estado" (Activo/Inactivo) y, para un admin, un botón
  Activar/Desactivar junto al de Eliminar.
- `backend/database/schema.sql` ya incluye la columna `activo` desde
  la creación de la tabla `usuarios`, no como migración aparte.

### Seguridad de la contraseña

- Las contraseñas se cifran con **bcrypt vía `passlib`**
  (`CryptContext(schemes=["bcrypt"])`, `app/auth.py`) antes de
  guardarse; **nunca** se almacenan ni se comparan en texto plano.
- El login usa `pwd_context.verify()` contra el hash guardado.
- Ningún endpoint (`/perfil`, `/usuarios`, etc.) devuelve `password_hash`
  en sus respuestas (los `schemas/` de salida no incluyen ese campo).
- Cambiar la contraseña exige primero la contraseña actual correcta.

### Protección con JWT

- Al iniciar sesión (`POST /api/auth/login`) recibes un `access_token`
  en el body de la respuesta (no en una cookie). Envíalo en las rutas
  protegidas con el header: `Authorization: Bearer <token>`.
- `backend/app/auth.py` expone las dependencias que usan las rutas:
  - `get_current_user` — exige un JWT válido (401 si falta, expiró, o
    su `token_version` ya no coincide con el de la base de datos).
  - `requiere_rol("admin", "empleado", ...)` — además del token, exige
    que el usuario tenga uno de esos roles (403 si no).
- Ejemplo de uso en una ruta (FastAPI, vía `Depends`):
  `@router.get("/perfil", dependencies=[Depends(get_current_user)])` o
  `@router.delete("/{id}", dependencies=[Depends(requiere_rol("admin"))])`.

### Colecciones de Postman (pruebas)

Para el backend FastAPI:

- `backend/postman-fastapi/ESSENTIA-FastAPI.postman_collection.json` +
  `ESSENTIA-FastAPI-local.postman_environment.json` — endpoints
  actualizados a las rutas reales de FastAPI (`/api/auth/login`, `PATCH`
  para cambiar estado, etc.). Ver `backend/postman-fastapi/LEEME.md`
  para el detalle de cómo importarla y correrla.
- `backend/postman-403-roles/ESSENTIA-403-roles.postman_collection.json`
  — pruebas dedicadas a verificar que cada endpoint protegido responde
  `401` sin token y `403` con un rol incorrecto (ver también
  `backend/docs/matriz-acceso-roles.md` y `guia-prueba-manual-403.md`).

Cómo correrlas:

1. Arranca el backend (`uvicorn app.main:app --reload`).
2. En Postman: **Import** → arrastra los archivos `.json` de la carpeta
   que quieras probar.
3. Selecciona el environment correspondiente (apunta a
   `http://127.0.0.1:8000/api`).
4. Corre **Login** primero: el token queda guardado en la variable de
   colección para que las peticiones protegidas lo reutilicen.
5. Para ver en verde las pruebas que requieren `admin`, conviértete en
   admin con el `UPDATE` de la sección anterior y vuelve a iniciar
   sesión.

> Requiere MySQL/XAMPP corriendo: sin base de datos, las pruebas que
> consultan la BD fallan por conexión rechazada, no por un problema de
> la colección en sí. También puedes probar cada endpoint directamente
> desde el Swagger UI en `http://127.0.0.1:8000/docs`, sin Postman.

## 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Por defecto el frontend llama al backend en `http://localhost:7463/api`.
Si cambiaste el `PORT` del backend, crea un archivo `frontend/.env`
(puedes copiar `frontend/.env.example`) y ajusta `VITE_API_URL`.

### Modo oscuro

Botón de sol/luna en el navbar (escritorio y móvil), persistido en
`localStorage` y con la preferencia del sistema operativo como
respaldo la primera vez. Técnicamente:

- `index.css` define un `@custom-variant dark` (Tailwind v4) atado a
  una clase `.dark` en `<html>` — no a `prefers-color-scheme` — para
  que el toggle manual mande por encima del tema del SO.
- Como Tailwind v4 compila cada utilidad como `var(--color-x)`, basta
  con sobreescribir 5 tokens "neutros" (`cream`, `section`, `primary`,
  `primary-dark`, `beige`) dentro de `.dark` para que casi todo el
  sitio se adapte solo, sin tocar className por componente.
- Los acentos de marca (`blush`, `champagne`, `sage`, `accent`) se
  dejan **intactos** a propósito en ambos temas — son colores de
  marca, no deben cambiar. Donde un acento fijo se combinaba con texto
  que sí cambia de tono (`text-primary`/`text-cream`), se introdujeron
  dos tokens fijos nuevos (`--color-ink`, `--color-paper`) para que esa
  tinta nunca pierda contraste contra el acento, sin importar el tema.
- Un script inline en `index.html` aplica la clase antes del primer
  render de React, para evitar el "flash" de tema equivocado al
  cargar la página.
- De paso, esta revisión encontró y corrigió un problema de contraste
  que ya existía en modo claro: texto blanco sobre el coral de acento
  (`bg-accent`) rondaba ~2.25:1 de contraste, por debajo del mínimo
  WCAG AA (4.5:1) — afectaba el botón "Añadir al carrito" y el badge
  del contador del carrito.

### Navbar autenticado

El `Header` (navbar) cambia según haya o no sesión iniciada:

- **Sin sesión:** muestra el botón "Iniciar sesión".
- **Con sesión:** muestra un acceso a "Mi panel" (con las iniciales del
  usuario) y un botón "Cerrar sesión". El estado se maneja globalmente
  con `AuthContext` (`frontend/src/context/AuthContext.jsx`), que guarda
  el token, decodifica el rol y expone `login()` / `logout()` a toda la
  app.

### Panel privado (`/panel`)

Ruta protegida (`ProtectedRoute`): si no hay sesión, redirige a
`/login`. Adentro, `Panel.jsx` muestra distintas pestañas según el rol
del usuario logueado:

- **Cliente:** "Mi perfil" + "Mis pedidos".
- **Empleado:** "Mi perfil" + "Mis pedidos" + "Productos" (crear/editar,
  sin eliminar) + "Servicios" (misma regla que Productos) + "Usuarios"
  (tabla de solo lectura) + "Pedidos" (todos los de la tienda, con
  cambio de estado).
- **Admin:** todas las pestañas anteriores con todas las acciones
  habilitadas (incluye cambiar roles y eliminar productos/servicios/
  usuarios), más "Cupones" (CRUD completo, exclusivo de admin).

### Botón flotante de WhatsApp

`components/WhatsAppButton.jsx` es un componente reutilizable, sin
props, montado una sola vez en `App.jsx` (junto al `Header`/`Footer`,
fuera de `<Routes>`) para que quede visible en **todas** las páginas,
siempre fijo en la esquina inferior derecha (`position: fixed`).

- Abre `https://wa.me/<número>` en una pestaña nueva, con un mensaje
  predeterminado ya escrito.
- El número de contacto es la constante `TELEFONO_WHATSAPP` al inicio
  del archivo (hoy apunta al mismo teléfono de ejemplo que se muestra
  en `/contacto`) — cámbiala ahí por el número real antes de entregar.
- Usa los colores del proyecto (`bg-primary`, `text-cream`) en vez del
  verde genérico de WhatsApp, para mantener coherencia visual con el
  resto del sitio.

### Validaciones en tiempo real

Todos los formularios (registro, login, recuperar contraseña, mi perfil,
productos, servicios) usan el hook `useForm` (`frontend/src/hooks/useForm.js`) junto
con las funciones de `frontend/src/utils/validators.js`:

- El error aparece apenas el campo pierde el foco (`onBlur`), sin
  necesidad de enviar el formulario.
- Mientras el campo ya fue "tocado", el error se recalcula en cada
  tecla, y desaparece en cuanto el valor es válido.
- El envío se bloquea en el cliente si hay errores, evitando llamadas
  innecesarias al backend.

### Vitrina del home vs. Tienda (catálogo real)

El home (`/`) tiene un carrusel (`components/Carousel.jsx`) con datos fijos
en `data/carouselData.js` — es contenido puramente editorial/decorativo,
sin botón de compra ni conexión a la base de datos, así que un cambio ahí
**no** afecta lo que el admin gestiona en `/panel/productos`.

Las tarjetas de "Nuestra vitrina" (`components/Collections.jsx`, categorías
del home) sí conectan con el catálogo real: cada una enlaza a
`/tienda?familia=<id>` (ej. `/tienda?familia=tortas`), y `Tienda.jsx`
lee ese parámetro de la URL al cargar para preseleccionar el filtro
correspondiente — usando el mismo vocabulario de categorías en ambos
lugares (`data/coleccionesData.js` y `constants/familiasProducto.js`).

La compra real vive únicamente en `/tienda` (`pages/Tienda.jsx`):

- Lista el catálogo real con `listarProductos()` (`GET /api/productos`,
  el mismo endpoint que ya consume `GestionProductos.jsx` en el panel),
  así que siempre refleja lo que el admin/empleado crea, edita o
  desactiva — sin datos duplicados ni desincronizados.
- Permite filtrar por categoría y ordenar por precio, ambos
  resueltos por el backend (`?familia=`, `?orden=`), no en el cliente.
- Ese filtro/orden, más la página actual, se reflejan en la URL de
  `/tienda` (`?familia=&orden=&pagina=`) usando `useSearchParams`: al
  recargar la página o compartir el link se conserva exactamente el
  mismo estado del catálogo. La búsqueda por nombre queda fuera de la
  URL a propósito — es solo un filtro dentro de la página ya cargada,
  no un estado de todo el catálogo que tenga sentido compartir.
- Reutiliza el componente `Paginacion` del panel y el botón
  `BotonAgregarCarrito` tal cual, sin lógica nueva de carrito.
- Es una ruta pública (sin `ProtectedRoute`): el propio backend, con
  `verificarTokenOpcional`, ya filtra los productos inactivos según el
  rol de quien pregunta.
- No tiene ningún control de editar/eliminar, aunque quien la visite sea
  admin o empleado — esa función se queda exclusivamente en el panel,
  para no duplicar el CRUD en dos lugares.
- Si una imagen de producto no carga (el campo `imagen` es un nombre de
  archivo escrito a mano desde el panel, sin subida real de archivo),
  la tarjeta muestra un ícono de repuesto en vez del ícono roto del
  navegador.

### Carrito de compras (Fase 1 del plan de tienda)

- Con sesión iniciada, el carrito vive en el backend (`carritos` +
  `carrito_items`, un carrito por usuario, creado al primer producto
  agregado) y se calcula siempre contra `productos.precio`/`stock`
  actuales — nunca se confía en un precio que mande el frontend.
- Sin sesión, el carrito se guarda en `localStorage` del navegador
  (`frontend/src/context/CartContext.jsx`), para que un visitante
  pueda armar y revisar su carrito (`/carrito`) sin tener que
  registrarse todavía.
- Al iniciar sesión, ese carrito de invitado se fusiona automáticamente
  (una sola vez) con el que el usuario ya tuviera guardado, sumando
  cantidades y respetando el stock disponible (`POST /api/carrito/fusionar`).
- El ícono de carrito del `Header` (con contador) y el botón "Añadir al
  carrito" de cada tarjeta de producto usan el hook `useCart()`
  (`frontend/src/hooks/useCart.js`).
- El botón "Ir a pagar" de `/carrito` lleva a `/checkout` (Fase 2, ver
  abajo); si no hay sesión iniciada, primero pasa por `/login` y vuelve
  automáticamente a `/checkout` al autenticarse.

### Pedidos y checkout (Fase 2 del plan de tienda)

- `POST /api/pedidos` crea el pedido a partir del carrito del usuario
  autenticado, dentro de una única transacción SQLAlchemy (sesión con
  `commit`/`rollback`, ver `app/routes/pedidos.py`):
  - El stock se descuenta con un `UPDATE productos SET stock = stock - :cant
    WHERE id = :id AND stock >= :cant` **condicional** (nunca un
    `SELECT` seguido de una comparación en Python), para que dos
    compras simultáneas de la última unidad nunca dejen el stock en
    negativo.
  - El subtotal/total se recalculan siempre en el backend contra el
    precio leído en esa misma transacción — el frontend nunca manda
    (ni el backend confía en) un total ya calculado.
  - `pedido_items` copia `titulo`/`precio_unitario` al momento de la
    compra: si el producto cambia de precio o se despublica después,
    el pedido ya facturado no se altera.
- **Idempotencia**: el frontend genera un `Idempotency-Key` (UUID) una
  sola vez al entrar a `/checkout` y lo reenvía en cada intento. Un
  doble clic en "Confirmar pedido" o un reintento de red nunca crea un
  pedido duplicado — la garantía real es la `UNIQUE KEY (usuario_id,
  idempotency_key)` en la tabla `pedidos` (ver `database/schema.sql`),
  no solo la comprobación previa en el controlador.
- **Autorización a nivel de fila**: `GET /api/pedidos/:id` no alcanza
  con "tener sesión" — el controlador verifica explícitamente que
  quien pregunta sea el dueño del pedido o tenga rol admin/empleado.
- `PUT /api/pedidos/:id/estado` (admin/empleado) repone el stock si el
  nuevo estado es `cancelado`, y bloquea cualquier cambio posterior una
  vez que el pedido llega a un estado terminal (`entregado` o
  `cancelado`).
- En el frontend: `/checkout` (formulario de envío + resumen, dirección
  y teléfono pre-cargados desde el perfil), `/pedidos/:id` (detalle /
  confirmación), `Mis pedidos` en el panel para cualquier usuario
  autenticado, y `Pedidos` en el panel (admin/empleado) para cambiar el
  estado de cualquier pedido.

### Facturación (Fase 4 del plan de tienda)

Sin sistema contable aparte: la factura es un PDF generado **al vuelo**
a partir de un `pedido` ya confirmado, nunca guardado en disco.

- `GET /api/pedidos/{id}/factura` (`app/routes/pedidos.py`): protegida
  por `get_current_user`, con la misma autorización a nivel de fila que
  `GET /api/pedidos/{id}` — solo el dueño del pedido o admin/empleado,
  nunca "basta con tener sesión".
- El PDF se arma en cada petición desde `pedidos` + `pedido_items` +
  los datos del cliente en `usuarios` (nombre, documento, correo). Si
  el pedido cambia de estado después (ej. se cancela), la próxima
  descarga ya lo refleja, porque no hay ninguna copia guardada que se
  desactualice.
- `app/utils/factura.py` genera el documento con
  [`reportlab`](https://pypi.org/project/reportlab/), devuelto como
  `StreamingResponse` (`Content-Type: application/pdf`,
  `Content-Disposition: attachment`) — nada toca el disco.
- Contenido de la factura: número de pedido, fecha, estado, datos del
  cliente (nombre, tipo/número de documento, correo), dirección de
  envío y teléfono de contacto del pedido, tabla de items
  (título/precio unitario/cantidad/subtotal), subtotal, descuento
  (con el código del cupón si aplicó uno) y total, y método de pago.
- **Frontend**: botón "Descargar factura" en `/pedidos/:id`
  (`PedidoDetalle.jsx`) y un ícono de descarga junto a cada fila en
  "Mis pedidos" (`MisPedidos.jsx`). Como el JWT viaja en el header
  `Authorization: Bearer` (no en una cookie), no alcanza con un
  `<a href="...">` plano: ambos usan una función de `utils/api.js` que
  hace `fetch` con el header Bearer, lee la respuesta como `blob` y
  dispara la descarga con `URL.createObjectURL`, respetando el nombre
  de archivo que manda el backend en `Content-Disposition`.
  Admin/empleado llegan al mismo botón entrando al detalle del pedido
  desde "Ver detalle" en el panel de Pedidos.

## Criterios de aceptación

Todas las historias de usuario (registro, login, roles, navbar
autenticado, CRUD de productos y usuarios, validaciones en tiempo real y
seguridad de la contraseña) están documentadas con criterios
**Dado/Cuando/Entonces** en [`CRITERIOS_ACEPTACION.md`](./CRITERIOS_ACEPTACION.md).

## Notas

- Las imágenes del carrusel siguen siendo los archivos locales en
  `frontend/src/assets/images` (se cargan directo con Vite, sin pasar por
  la base de datos) — la tabla `productos` queda lista para administrar
  el catálogo dinámicamente desde el panel (admin/empleado).
- Las contraseñas se guardan cifradas con `bcrypt`, nunca en texto plano
  (ver sección "Seguridad de la contraseña" arriba).
