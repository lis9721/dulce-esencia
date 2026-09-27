# Colección Postman — backend FastAPI (Dulce Esencia)

Esta carpeta reemplaza/adapta la colección Postman a la `baseUrl` real
del backend Python (`http://localhost:8000`, puerto por defecto de
`uvicorn`), a diferencia de `postman-403-roles/` que ya venía correcta
pero solo cubría el escenario de permisos 403 por rol.

Cubre los **5 métodos HTTP** (GET, POST, PUT, PATCH, DELETE) en los
8 módulos de la API: auth/usuarios, productos, servicios, carrito,
pedidos, cupones, contacto y roles — 60 peticiones en total.

## 1. Importar

En Postman: **Import** → arrastra los dos archivos:

- `ESSENTIA-FastAPI.postman_collection.json`
- `ESSENTIA-FastAPI-local.postman_environment.json`

Arriba a la derecha, selecciona el environment **"Dulce Esencia FastAPI - local"**.

## 2. Arrancar el backend

```
cd backend
uvicorn app.main:app --reload
```

Confirma que quedó arriba con la carpeta **"0. Salud"** (`GET /` y
`GET /api/salud/db`).

## 3. Completar credenciales

Abre el environment y llena (con cuentas que ya existan en tu base de
datos, o créalas primero con el flujo de registro / "POST Crear
usuario (admin)"):

- `correo_admin` / `password_admin`
- `correo_empleado` / `password_empleado`
- `correo_cliente` / `password_cliente`

## 4. Iniciar sesión

Corre **"1. Auth / Usuarios" → POST Login admin** (y opcionalmente
Login empleado / Login cliente). El token queda guardado solo en el
environment (`{{token}}`, `{{token_admin}}`, etc.) gracias al script
de test de cada login — no hay que copiar/pegar nada a mano.

## 5. Recorrer las demás carpetas

Cada `POST` de creación (producto, servicio, cupón, usuario, mensaje
de contacto, pedido) guarda automáticamente el `id` creado en el
environment (`producto_id`, `servicio_id`, etc.), así que las
peticiones de `PUT`/`PATCH`/`DELETE` de la misma carpeta ya lo
encuentran listo — solo tienes que correrlas en el orden en que
aparecen.

**Nota — Carrito y Pedidos:** usan `{{token}}` (el último login
corrido). Para probar ese flujo como querría un cliente real, corre
"POST Login cliente" justo antes.

**Nota — subir imagen de producto:** en "3. Productos → POST Subir
imagen de producto" el body es `form-data`; antes de enviar, haz clic
en el campo `imagen` y selecciona un archivo `.jpg/.jpeg/.png/.webp`
de tu computador (Postman no puede adjuntar el archivo por ti).

## 6. Para las capturas de evidencia (Parte 9)

Por cada método que necesites documentar:

1. Corre la petición.
2. En la respuesta, ten visibles: el método + URL (arriba), el body
   enviado (si aplica) y el código de estado + cuerpo de la
   respuesta (abajo).
3. Toma la captura de esa pantalla completa de Postman.

Repite al menos una vez por método (GET, POST, PUT, PATCH, DELETE);
lo ideal es una captura por módulo si el tiempo alcanza, para dejar
evidencia de que la migración a FastAPI cubre el mismo alcance que el
backend Node original.
