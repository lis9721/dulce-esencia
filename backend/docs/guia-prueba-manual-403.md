# Guía de prueba manual — 403 por rol incorrecto

Complementa `matriz-acceso-roles.md`. Sirve para repetir la verificación
a mano (sin script ni Postman), por ejemplo directo en Swagger UI
(`http://localhost:8000/docs`) o con `curl`.

## 0. Preparación

Necesitas **tres cuentas ya creadas y verificadas** en la base de datos,
una por rol (`cliente`, `empleado`, `admin`). Si no existen:

1. Crea una cuenta normal por `POST /api/usuarios/registro` (queda como
   `cliente`).
2. Verifícala (revisa la consola del backend: en desarrollo el enlace de
   verificación se imprime ahí, no se envía correo real).
3. Para tener un `empleado` y un `admin`, edita el campo `rol` de esos
   usuarios directamente en la tabla `usuarios` de MySQL (no hay endpoint
   público para auto-asignarse un rol, por diseño).

## 1. Consigue un token por rol

```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"correo":"cliente@correo.com","password":"tu_password"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])"
```

Repite cambiando correo/password para `empleado` y `admin`. Guarda los
tres tokens en variables de shell:

```bash
TOKEN_CLIENTE="..."
TOKEN_EMPLEADO="..."
TOKEN_ADMIN="..."
```

## 2. Prueba sin token → debe dar 401 (no 403)

```bash
curl -i http://localhost:8000/api/usuarios
```

Esperado: `401 Unauthorized`, cuerpo con
`"No se proporcionó un token..."`. Si en vez de eso deja pasar la
petición o responde `200`, hay un endpoint sin proteger — repórtalo.

## 3. Prueba con rol incorrecto → debe dar 403

Ejemplo: un `cliente` intentando listar usuarios (ruta admin+empleado):

```bash
curl -i http://localhost:8000/api/usuarios \
  -H "Authorization: Bearer $TOKEN_CLIENTE"
```

Esperado: `403 Forbidden`, cuerpo con
`"No tienes permisos para realizar esta acción."`.

Repite este mismo patrón para cada fila 👑/👔 de `matriz-acceso-roles.md`,
usando siempre el rol que **no** está permitido. Casos mínimos
recomendados (los que más importa que no se cuelen):

| Prueba | Comando | Esperado |
|---|---|---|
| Cliente borra un usuario | `curl -i -X DELETE http://localhost:8000/api/usuarios/1 -H "Authorization: Bearer $TOKEN_CLIENTE"` | 403 |
| Empleado borra un producto | `curl -i -X DELETE http://localhost:8000/api/productos/1 -H "Authorization: Bearer $TOKEN_EMPLEADO"` | 403 (borrar es solo admin) |
| Cliente crea un producto | `curl -i -X POST http://localhost:8000/api/productos -H "Authorization: Bearer $TOKEN_CLIENTE" -H "Content-Type: application/json" -d '{}'` | 403 (antes de validar el body) |
| Cliente lista roles | `curl -i http://localhost:8000/api/roles -H "Authorization: Bearer $TOKEN_CLIENTE"` | 403 |
| Empleado crea un cupón | `curl -i -X POST http://localhost:8000/api/cupones -H "Authorization: Bearer $TOKEN_EMPLEADO" -H "Content-Type: application/json" -d '{}'` | 403 (crear cupón es solo admin) |
| Cliente A ve el pedido de Cliente B | login como cliente A, `curl -i http://localhost:8000/api/pedidos/<id_de_otro_cliente> -H "Authorization: Bearer $TOKEN_CLIENTE_A"` | 403 |

> Nota sobre el orden de validación: `requiere_rol` corre **antes** de que
> la función toque la base de datos, así que un `403` debe llegar incluso
> con un `id` inexistente en la URL (ej. `/api/productos/999999`) o un
> body vacío. Si en cambio ves un `404` o un `422` antes que el `403`,
> significa que la ruta NO está protegida con `requiere_rol` y el error
> viene de más adelante en la función — ese es un hallazgo real a
> corregir.

## 4. Prueba con el rol correcto → NO debe dar 403

Confirma también el caso positivo, para no terminar con una ruta
sobre-restringida:

```bash
curl -i -X DELETE http://localhost:8000/api/productos/999999 \
  -H "Authorization: Bearer $TOKEN_ADMIN"
```

Esperado: `404 Not Found` ("Producto no encontrado"), **no** `403`. El
`404` aquí es la señal de que sí pasó el chequeo de rol y llegó a la
lógica de negocio.

## 5. Registra el resultado

Marca en tu checklist de Parte 6:

- [x] Matriz de acceso admin/empleado/cliente — verificada (ver
  `matriz-acceso-roles.md`).
- [x] Prueba manual de `403` por URL directa sin el rol correcto —
  pasos de esta guía, o automatizada con
  `backend/tests/test_endpoint_roles_403.py` /
  `backend/postman-403-roles/`.
