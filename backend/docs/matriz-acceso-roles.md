# Matriz de acceso por rol — Parte 6 / Prioridad 6

> Estado: **verificada contra el código real** de `backend/app/routes/*.py`
> y `backend/app/auth.py` (no contra la especificación, sino contra lo que
> el servidor efectivamente ejecuta). Cada fila indica el archivo y la
> línea donde vive la protección para que se pueda re-verificar en 10
> segundos si el código cambia.
>
> Mecanismo: `app/auth.py` → `get_current_user` (exige `Authorization:
> Bearer <token>` válido y re-lee `rol`/`activo` desde la BD en cada
> petición) + `requiere_rol(*roles)` (403 si el rol autenticado no está en
> la lista). `401` = no autenticado / token inválido. `403` = autenticado
> pero sin permiso.

Roles existentes (`app/models/usuario.py::RolUsuario`): `cliente`,
`empleado`, `admin`.

## Leyenda

- 🌐 **Pública** — no requiere token.
- 🔒 **Autenticada** — requiere login, cualquier rol vale.
- 👑 **admin** — solo `admin`.
- 👔 **admin+empleado** — `admin` o `empleado`.
- 🙋 **dueño o admin+empleado** — chequeo de propiedad en el cuerpo de la función, no en `requiere_rol`.

## `/api/auth` y `/api/usuarios`

| Método | Ruta | Acceso | Dónde está aplicado |
|---|---|---|---|
| POST | `/api/auth/login` | 🌐 Pública | `routes/usuarios.py:135` |
| POST | `/api/usuarios/registro` | 🌐 Pública | `routes/usuarios.py:74` |
| POST | `/api/usuarios/recuperar` | 🌐 Pública | `routes/usuarios.py:179` |
| POST | `/api/usuarios/restablecer` | 🌐 Pública | `routes/usuarios.py:~204` |
| POST | `/api/usuarios/reenviar-verificacion` | 🌐 Pública | `routes/usuarios.py:247` |
| GET | `/api/usuarios` | 👔 admin+empleado | `routes/usuarios.py:276` |
| GET | `/api/usuarios/{id}` | 👔 admin+empleado | `routes/usuarios.py:307-310` |
| PUT | `/api/usuarios/{id}` | 👑 admin | `routes/usuarios.py:326-329` |
| PATCH | `/api/usuarios/{id}/estado` | 👑 admin | `routes/usuarios.py:362` |
| DELETE | `/api/usuarios/{id}` | 👑 admin | `routes/usuarios.py:396` |

## `/api/productos`

| Método | Ruta | Acceso | Dónde está aplicado |
|---|---|---|---|
| GET | `/api/productos` | 🌐 Pública (solo `activo=True`) | `routes/productos.py:26` |
| GET | `/api/productos/admin/todos` | 👔 admin+empleado | `routes/productos.py:60-64` |
| GET | `/api/productos/{id}` | 🌐 Pública | `routes/productos.py:93` |
| POST | `/api/productos` | 👔 admin+empleado | `routes/productos.py:102-107` |
| PUT | `/api/productos/{id}` | 👔 admin+empleado | `routes/productos.py:124-128` |
| PATCH | `/api/productos/{id}/estado` | 👔 admin+empleado | `routes/productos.py:154-158` |
| DELETE | `/api/productos/{id}` | 👑 admin | `routes/productos.py:177-181` |

## `/api/servicios`

| Método | Ruta | Acceso | Dónde está aplicado |
|---|---|---|---|
| GET | `/api/servicios` | 🌐 Pública | `routes/servicios.py:21` |
| GET | `/api/servicios/admin/todos` | 👔 admin+empleado | `routes/servicios.py:50-54` |
| GET | `/api/servicios/{id}` | 🌐 Pública | `routes/servicios.py:80` |
| POST | `/api/servicios` | 👔 admin+empleado | `routes/servicios.py:89-94` |
| PUT | `/api/servicios/{id}` | 👔 admin+empleado | `routes/servicios.py:111-115` |
| PATCH | `/api/servicios/{id}/estado` | 👔 admin+empleado | `routes/servicios.py:137-141` |
| DELETE | `/api/servicios/{id}` | 👑 admin | `routes/servicios.py:157-161` |

## `/api/roles`

| Método | Ruta | Acceso | Dónde está aplicado |
|---|---|---|---|
| GET | `/api/roles` | 👑 admin | `routes/roles.py:18-22` (protección a nivel de router completo) |
| GET | `/api/roles/{id}` | 👑 admin | ídem |

## `/api/cupones`

| Método | Ruta | Acceso | Dónde está aplicado |
|---|---|---|---|
| POST | `/api/cupones/validar` | 🔒 Autenticada (cualquier rol) | `routes/cupones.py:30-36` |
| GET | `/api/cupones` | 👔 admin+empleado | `routes/cupones.py:58` |
| GET | `/api/cupones/{id}` | 👔 admin+empleado | `routes/cupones.py:80-84` |
| POST | `/api/cupones` | 👑 admin | `routes/cupones.py:93-98` |
| PUT | `/api/cupones/{id}` | 👑 admin | `routes/cupones.py:115-119` |
| PATCH | `/api/cupones/{id}/estado` | 👑 admin | `routes/cupones.py:141-145` |
| DELETE | `/api/cupones/{id}` | 👑 admin | `routes/cupones.py:161-165` |

## `/api/pedidos`

| Método | Ruta | Acceso | Dónde está aplicado |
|---|---|---|---|
| POST | `/api/pedidos` | 🔒 Autenticada (cualquier rol) | `routes/pedidos.py:26-30` |
| GET | `/api/pedidos` | 🔒 Autenticada — `cliente` solo ve los suyos, admin/empleado ven todos | `routes/pedidos.py:147` (filtro, no 403) |
| GET | `/api/pedidos/{id}` | 🙋 Dueño o admin+empleado | `routes/pedidos.py:170-171` (chequeo manual → **403** si no aplica) |
| PATCH | `/api/pedidos/{id}/estado` | 👔 admin+empleado | `routes/pedidos.py:176-179` |

## `/api/carrito`

| Método | Ruta | Acceso | Dónde está aplicado |
|---|---|---|---|
| GET / POST / PUT / DELETE (todas) | `/api/carrito*` | 🔒 Autenticada (cualquier rol; el carrito siempre es "el mío") | `routes/carrito.py` (todas usan `get_current_user`) |

## `/api/contacto`

| Método | Ruta | Acceso | Dónde está aplicado |
|---|---|---|---|
| POST | `/api/contacto` | 🌐 Pública | `routes/contacto.py:21` |
| GET | `/api/contacto` | 👔 admin+empleado | `routes/contacto.py:31` |
| GET | `/api/contacto/{id}` | 👔 admin+empleado | `routes/contacto.py:57-60` |
| DELETE | `/api/contacto/{id}` | 👔 admin+empleado | `routes/contacto.py:70-73` |

---

## Conclusión de la verificación

Contra lo que decía el checklist de Parte 6 ("aún no aplicada a ningún
endpoint real"), **la protección por rol ya está aplicada en el 100% de
los endpoints que la necesitan**, en el código Python entregado en este
zip. No se modificó ningún archivo de `app/` para esta entrega: esta
matriz es un documento de verificación, no un parche.

Lo único que sí faltaba y se entrega ahora junto con esta matriz:

1. Este documento (verificación escrita, punto pendiente 1).
2. `backend/tests/test_endpoint_roles_403.py` — script automático de
   prueba de `403` por rol incorrecto (punto pendiente 2).
3. `backend/docs/guia-prueba-manual-403.md` — pasos para repetir la
   misma prueba a mano con curl/Swagger, y una colección Postman en
   `backend/postman-403-roles/`.
