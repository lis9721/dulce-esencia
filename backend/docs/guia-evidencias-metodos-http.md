# Guía — Evidencias de los 5 métodos HTTP (Parte 9, Prioridad 8)

Objetivo: dejar una captura real por cada método (GET, POST, PUT, PATCH,
DELETE), mostrando la petición y la respuesta con su código de estado.
Puedes hacerlo con **Swagger UI** (viene gratis con FastAPI, cero
configuración) o con la colección de **Postman** que ya está en
`backend/postman-fastapi/`. Ambas rutas están documentadas abajo — usa
la que te resulte más cómoda, o las dos si el enunciado pide variedad
de herramientas.

---

## Antes de empezar

1. Arranca MySQL/XAMPP y el backend:
   ```
   cd backend
   uvicorn app.main:app --reload
   ```
2. Confirma que responde: abre `http://localhost:8000/` en el navegador
   — debe mostrar `{"mensaje": "Backend de Dulce Esencia Pastelería..."}`.
3. Ten a mano un correo/contraseña de un usuario **admin** ya existente
   en tu base de datos (si no tienes uno, créalo con
   `POST /api/usuarios/registro` y luego súbele el rol manualmente en
   la BD, o usa uno que ya hayas usado en pruebas anteriores).

---

## Opción A — Swagger UI (recomendada, no necesita instalar nada)

Con el servidor corriendo, abre:

```
http://localhost:8000/docs
```

FastAPI genera esta interfaz solo, a partir de las rutas y los
schemas Pydantic — vas a ver todos los endpoints agrupados por
módulo (usuarios, productos, servicios, carrito, pedidos, cupones,
contacto, roles), cada uno con su método coloreado (GET en azul,
POST en verde, PUT en naranja, DELETE en rojo, PATCH en morado).

### Paso 1 — Iniciar sesión y obtener el token

1. Busca la sección **auth** → `POST /api/auth/login`.
2. Clic en la fila para desplegarla → botón **"Try it out"**.
3. En el cuadro de texto del body, reemplaza el ejemplo por:
   ```json
   {
     "correo": "tu_admin@correo.com",
     "password": "tu_contraseña"
   }
   ```
4. Clic en **"Execute"**.
5. En la respuesta (código `200`), copia el valor completo de
   `access_token` (sin las comillas).

### Paso 2 — Autorizar Swagger con ese token

1. Sube al botón verde **"Authorize"** (arriba a la derecha, con un
   ícono de candado).
2. En el campo **Value**, pega: `Bearer TU_TOKEN_COPIADO`
   (la palabra `Bearer`, un espacio, y el token — así completo).
3. Clic en **"Authorize"** y luego en **"Close"**.
4. Desde este momento, todos los endpoints protegidos que pruebes
   en esta pestaña ya llevan el header `Authorization` puesto
   automáticamente — no hay que repetirlo por cada uno.

### Paso 3 — Un endpoint de ejemplo por método

Usa esta tabla como guía rápida (puedes usar otros, pero estos ya
están pensados para no necesitar datos previos):

| Método | Endpoint sugerido | Notas |
|---|---|---|
| **GET** | `GET /api/productos` | Público, no necesita "Authorize". |
| **POST** | `POST /api/productos` | Requiere admin/empleado autorizado (Paso 2). |
| **PUT** | `PUT /api/productos/{producto_id}` | Usa el `id` que te devolvió el POST anterior. |
| **PATCH** | `PATCH /api/productos/{producto_id}/estado` | `activo` va como parámro de query (`true`/`false`), no en el body. |
| **DELETE** | `DELETE /api/productos/{producto_id}` | Solo admin. Si el producto ya tiene pedidos, responde 409 — usa uno recién creado. |

Para cada uno:

1. Despliega el endpoint → **"Try it out"**.
2. Completa el body/parámetros (Swagger ya trae un ejemplo generado
   a partir del schema; ajusta los valores).
3. **"Execute"**.
4. Antes de la captura, asegúrate de que en pantalla se vean:
   - El método y la ruta (arriba del todo, ej. `POST /api/productos`).
   - El **"Curl"**/**"Request body"** que se envió.
   - El **"Code"** de respuesta (200/201/204/4xx) y el **"Response body"**.
5. Toma la captura de esa sección completa (no hace falta capturar
   toda la ventana del navegador, basta con el bloque del endpoint
   expandido).

### Paso 4 — Guardar las capturas

Sugerencia de nombre de archivo, para que quede ordenado:

```
evidencia-01-get-productos.png
evidencia-02-post-productos.png
evidencia-03-put-productos.png
evidencia-04-patch-productos-estado.png
evidencia-05-delete-productos.png
```

Puedes guardarlas donde ya estés centralizando las evidencias del
avance (ej. una carpeta `evidencias/` en la raíz del proyecto, o
directo en el documento/informe que estés armando).

---

## Opción B — Postman (si prefieres esta herramienta)

1. Importa `backend/postman-fastapi/ESSENTIA-FastAPI.postman_collection.json`
   y su environment (ver `backend/postman-fastapi/LEEME.md` si no lo
   has hecho todavía).
2. Corre **"1. Auth / Usuarios" → POST Login admin** — el token queda
   guardado solo.
3. Corre, en orden, dentro de **"3. Productos"**:
   - `POST Crear producto` (guarda el `producto_id` solo)
   - `GET Detalle de producto`
   - `PUT Actualizar producto (reemplazo completo)`
   - `PATCH Cambiar estado (publicar/despublicar)`
   - `DELETE Eliminar producto`
4. Para cada una, antes de la captura, asegúrate de que se vean:
   método + URL (barra superior), pestaña **Body** con lo enviado (si
   aplica), y la parte de abajo con el código de estado y el
   **Response Body**.
5. Mismo criterio de nombres de archivo que en la Opción A.

---

## Checklist final

- [ ] Captura de **GET** con código 200.
- [ ] Captura de **POST** con código 201 (o 200 si el endpoint no crea
      un recurso, ej. login).
- [ ] Captura de **PUT** con código 200.
- [ ] Captura de **PATCH** con código 200.
- [ ] Captura de **DELETE** con código 200 (este backend no usa 204;
      siempre devuelve un `{"mensaje": "..."}`).
- [ ] (Opcional, recomendado) Una captura extra de un **error real**
      manejado por la API — por ejemplo, `POST /api/auth/login` con
      contraseña incorrecta (401) o `DELETE` de un producto con
      pedidos asociados (409) — para demostrar que también se
      documentaron los casos de error, no solo el camino feliz.
