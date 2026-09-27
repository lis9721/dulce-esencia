# Normalización de la base de datos — cambios aplicados

Se corrigieron los dos puntos de deuda técnica en 3FN que ya estaban identificados
en `docs/NORMALIZACION-BD.md` (sección 3, tabla de 3FN):

## 1. `usuarios.rol`: de ENUM redundante a llave foránea real

**Antes:** `usuarios.rol` era `ENUM('cliente','empleado','admin')`, un dominio
duplicado del que ya describía la tabla `roles`, sin ninguna llave foránea entre
ambos.

**Ahora:** `usuarios.rol` es `VARCHAR(20)` con
`CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol) REFERENCES roles(nombre)
ON UPDATE CASCADE ON DELETE RESTRICT`. `roles.nombre` (ya `UNIQUE`) pasa a ser la
única fuente de verdad del dominio: MySQL rechaza cualquier `rol` que no exista en
`roles`, y ya no se puede borrar una fila de `roles` que algún usuario tenga
asignada.

Archivos tocados:
- `backend/database/schema_fastapi.sql` — columna + `ALTER TABLE ... ADD CONSTRAINT fk_usuarios_rol` (después de crear `roles`), más una nota de migración para bases ya existentes.
- `backend/app/models/usuario.py` — columna `rol` pasa de `Enum(RolUsuario)` a `String(20)` + `ForeignKey`. `RolUsuario` se conserva solo como validador en los esquemas Pydantic.
- `backend/app/database.py` — nuevo `_sembrar_roles_base()`, llamado en cada arranque (`sincronizar_esquema()`): siembra `admin/empleado/cliente` en `roles` con `INSERT IGNORE` para que una base de datos nueva (creada solo con `create_all()`, sin correr el `.sql` a mano) pueda aceptar el primer usuario.
- `backend/app/routes/usuarios.py` — `usuario.rol.value` → `usuario.rol` (ya es un `str`, no un `Enum`).
- `backend/tests/test_auth.py` — mismos dos ajustes de `.rol.value` → `.rol`.
- `backend/app/models/rol.py`, `backend/app/schemas/rol.py`, `backend/app/routes/roles.py` — docstrings actualizados (ya no dicen "tabla documental sin FK").

Nada más cambia: `requiere_rol()`, los checks `usuario.rol not in (...)` de cada
router y el JWT (`{"role": usuario.rol}`) siguen funcionando igual porque siguen
comparando strings.

## 2. `facturas.cliente_id`: dependencia transitiva eliminada

**Antes:** `facturas.cliente_id` duplicaba, vía `factura → venta → cliente`, un
dato que ya vive en `ventas.cliente_id` — una dependencia transitiva textbook.

**Ahora:** se eliminó la columna `cliente_id` (y su FK) de la tabla `facturas`. En
el ORM se reemplazó por `cliente_id = association_proxy("venta", "cliente_id")`:
`factura.cliente_id` se sigue leyendo igual en Python, y `Factura.cliente_id ==
valor` se sigue pudiendo usar en filtros de consulta (SQLAlchemy lo traduce a un
`JOIN`/`EXISTS` contra `ventas`) — pero sin guardar el dato dos veces.

Archivos tocados:
- `backend/database/schema_fastapi.sql` — columna y `CONSTRAINT fk_facturas_cliente` eliminadas de `CREATE TABLE facturas`, más la misma nota de migración.
- `backend/app/models/factura.py` — `cliente_id`/`cliente` pasan de columna/relationship a `association_proxy`.
- `backend/app/routes/facturas.py` — ya no se pasa `cliente_id=venta.cliente_id` al crear la factura (se lee solo, vía `venta_id`).

La API pública no cambia: `GET /api/facturas`, el filtro `?cliente_id=`, y el
campo `cliente_id` en `FacturaSalida` siguen funcionando exactamente igual.

## Verificación

- `pytest tests/ -q` (excepto `test_endpoint_roles_403.py` y `test_chatbot_local.py`,
  que necesitan un servidor real levantado): **130 passed**, incluidos los 30 de
  `test_auth.py`.
- Prueba manual con SQLite + `PRAGMA foreign_keys=ON`: confirma que insertar un
  usuario con un `rol` que no existe en `roles` lanza `IntegrityError`, que
  `factura.cliente_id` lee correctamente a través de `venta`, y que un filtro
  `Factura.cliente_id == id` sigue encontrando la factura.

## Si ya tenías la base de datos creada

No hace falta recrearla. Corre esto en phpMyAdmin (o consulta la nota al inicio
de `backend/database/schema_fastapi.sql`):

```sql
INSERT IGNORE INTO roles (nombre, descripcion) VALUES
  ('admin',    'Control total: usuarios, productos, servicios, pedidos, cupones y mensajes.'),
  ('empleado', 'Gestión operativa de productos, servicios, usuarios y pedidos, sin cupones.'),
  ('cliente',  'Acceso a su propio perfil, carrito, pedidos y catálogo público.');

ALTER TABLE usuarios MODIFY COLUMN rol VARCHAR(20) NOT NULL DEFAULT 'cliente';
ALTER TABLE usuarios
  ADD CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol) REFERENCES roles (nombre)
  ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE facturas DROP FOREIGN KEY fk_facturas_cliente;
ALTER TABLE facturas DROP COLUMN cliente_id;
```
