# Parte 6 — Qué falta (revisión de `parte6-verificacion-roles.md`)

Revisé el documento de verificación contra el código real de las rutas
(`app/routes/usuarios.py`, `productos.py`, etc.). La cobertura es muy
buena, pero encontré **3 endpoints protegidos que no están en la
matriz** y confirmé los pendientes que el propio documento ya
reconocía. Vas completo hasta acá:

- [x] Infraestructura `requiere_rol()`.
- [x] Matriz admin/empleado/cliente para 27 endpoints.
- [x] Prueba real de `401` (sin token) y `403` (rol incorrecto).

Esto es lo que falta:

---

## 1. Endpoints protegidos que faltan en la matriz (gap real, no solo de forma)

El documento dice *"100% de los endpoints protegidos"*, pero comparando
contra el código hay 3 que quedaron fuera de la tabla:

| Endpoint | Método | Roles permitidos | Por qué falta |
|---|---|---|---|
| `/api/usuarios` | **POST** | admin | `crear_usuario` (creación de usuarios desde el panel admin) — la tabla solo prueba `GET /api/usuarios`, no el `POST`. |
| `/api/usuarios/{id}/rol` | **PUT** | admin | `cambiar_rol_usuario` — endpoint dedicado y **distinto** de `PUT /api/usuarios/{id}` (que sí está en la matriz); cambia solo el campo `rol`. |
| `/api/productos/imagen` | **POST** | admin, empleado | `subir_imagen_producto` — la tabla cubre el resto del CRUD de productos pero no la subida de imagen. |

**Acción sugerida:** correr los mismos 3 escenarios (sin token / rol
incorrecto / rol correcto) contra estos 3 endpoints y agregar las filas
a la tabla. Para `POST /api/usuarios/imagen` necesitas un archivo real
(`.jpg/.jpeg/.png/.webp`) en el `form-data`, igual que en Postman.

---

## 2. Pendientes que el propio documento ya señala (limpieza de datos de prueba)

Estos no son huecos de seguridad — el control de rol ya se demostró —
pero quedaron sin el `200` final:

- [ ] **`PATCH /api/usuarios/{id}/estado`** — repetirlo con el body
  real que espera `UsuarioEstadoEntrada` (`{"activo": true}` o
  `{"activo": false}`) en vez de `?activo=true` por query. La prueba
  anterior dio `422` porque el body no tenía la forma correcta, no
  porque el rol fallara.
- [ ] **`PATCH /api/pedidos/{id}/estado`** — repetirlo contra un
  `pedido_id` que sí exista (crear uno de prueba con
  `POST /api/pedidos` primero). La prueba anterior dio `404` por
  probar contra `999999`.

---

## 3. Verificado solo por lectura de código, no por petición real

El documento es honesto sobre esto para pedidos, pero vale la pena
convertirlo en prueba real si el enunciado pide "evidencia de
ejecución" y no solo auditoría de código:

- [ ] **Autorización a nivel de fila en pedidos**: loguearte como
  `cliente@test.com`, tomar el `id` de un pedido de **otro** usuario
  (o de `empleado`/`admin`), y confirmar que
  `GET /api/pedidos/{id}` responde `403` (no `404`) — así queda
  demostrado que el filtro es "no es tuyo" y no "no existe".
- [ ] **Candados de auto-modificación** (ya están en el código, no
  probados aún):
  - Un admin intentando `PUT /api/usuarios/{su_propio_id}/rol` →
    debe dar `400` ("No puedes cambiar el rol de tu propia cuenta").
  - Un admin intentando `PATCH /api/usuarios/{su_propio_id}/estado` →
    `400` ("No puedes cambiar el estado de tu propia cuenta").
  - Un admin intentando `DELETE /api/usuarios/{su_propio_id}` →
    `400` ("No puedes eliminar tu propia cuenta desde aquí").

---

## 4. Fuera del alcance de Parte 6, pero relacionado (mencionar si el enunciado lo pide)

- El documento no prueba los códigos `409` de conflicto (ej. eliminar
  un producto/servicio/usuario que ya tiene pedidos asociados). Eso
  valida integridad referencial, no roles — probablemente pertenece a
  otra parte del enunciado, pero si tu rúbrica de Parte 6 pide
  "manejo de errores" en general, sería fácil sumarlo ahora que ya
  tienes el entorno de prueba armado (`test_matriz_roles.py`).

---

## Resumen rápido

| Categoría | Cantidad pendiente |
|---|---|
| Endpoints protegidos sin probar | 3 |
| Pruebas a repetir con datos correctos | 2 |
| Verificaciones de código aún no confirmadas por petición real | 4 |

Nada de esto es un hueco de seguridad — el mecanismo (`requiere_rol`,
filtro por fila, candados de auto-modificación) ya está implementado y
se ve correcto en el código. Es trabajo de **evidencia**: extender el
mismo script `test_matriz_roles.py` para que también cubra estos 9
casos y quede una Parte 6 con cobertura del 100% real, no del 100%
sobre el subconjunto que ya se probó.
