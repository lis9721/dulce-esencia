# Seguridad informática — Inyección SQL

## 1. ¿Qué es?

Ocurre cuando lo que escribe el usuario **se pega dentro del texto de la consulta SQL** y la base de datos lo
interpreta como código. Ejemplo clásico en un login:

```python
# ❌ VULNERABLE (concatenación)
sql = "SELECT * FROM usuarios WHERE correo = '" + correo + "' AND clave = '" + clave + "'"
# Si correo = ' OR 1=1 --   la consulta queda:
# SELECT * FROM usuarios WHERE correo = '' OR 1=1 --' AND clave = '...'
# → 1=1 siempre es verdadero y "--" comenta el resto: entra sin contraseña.
```

## 2. Cómo se resuelve en Dulce Esencia: defensa en profundidad (3 capas + 1)

| Capa | Dónde | Qué hace |
|---|---|---|
| **1. Frontend escalonado** | `frontend/src/pages/Login.jsx` | El login se separa en **dos formularios**: paso 1 solo el correo (se valida el *formato*: `' OR 1=1` no es un correo y no avanza); paso 2 la contraseña. El backend solo se llama en el paso 2, así que el paso 1 tampoco revela qué correos existen. |
| **2. Validación en el backend** | `schemas/auth.py` (`EmailStr`, longitudes) | Aunque alguien salte el frontend (Postman, curl), un correo con comillas o espacios responde **422** y nunca llega a la BD. |
| **3. Consulta preparada** | `repositories/usuario_repository.py` | El valor del usuario viaja como **parámetro ligado** (`bindparam`), separado del texto SQL. |
| **+ Hash de contraseña** | `app/auth.py` (bcrypt) | La contraseña **no se compara dentro del SQL**: se busca al usuario por correo y luego `verificar_hash()` compara en Python contra un hash con sal. |

> El frontend es una **capa de comodidad, no de seguridad**: cualquiera puede saltárselo. Por eso la defensa real
> está en el backend (capas 2 y 3).

## 3. La consulta preparada (PREPARED STATEMENT)

Equivalente al ejemplo visto en clase:

```sql
SELECT * FROM usuarios WHERE correo = ?      -- SET 1 = correo
```

En este proyecto (`backend/app/repositories/usuario_repository.py`):

```python
_SELECT_USUARIO_POR_CORREO = select(Usuario).where(Usuario.correo == bindparam("correo"))

def buscar_por_correo(db, correo):
    return db.execute(_SELECT_USUARIO_POR_CORREO, {"correo": correo}).scalars().first()
```

- El texto SQL se define **una vez** con un "hueco" (`:correo`).
- El valor se envía **aparte**; el motor lo trata siempre como dato, jamás como instrucción.
- Con `' OR 1=1 --` como correo, la BD busca un usuario cuyo correo sea *literalmente* esa cadena → no existe → `None`.

**Diferencia con el ejemplo del profesor (`AND CLAVE = ?`):** el ejemplo compara la clave dentro del SQL, lo que
implica guardarla en texto plano o comparar hashes directamente en la consulta. Dulce Esencia guarda **bcrypt** y
verifica en Python; así, ni con una inyección exitosa el atacante vería contraseñas legibles.

`login` usa el repositorio (`routes/usuarios.py`) y también `get_current_user` (`app/auth.py`); el resto de las rutas
usan el ORM de SQLAlchemy, que **siempre** parametriza. Se revisó todo `backend/app`: no hay SQL armado con datos del
usuario. Las únicas f-strings con SQL (`database.py`, `ALTER TABLE` al sincronizar el esquema) usan nombres de tablas y
columnas de los propios modelos, nunca datos de entrada.

## 4. Evidencia: pruebas automáticas

`backend/tests/test_seguridad_sqli.py` (27 casos). Ejecutar:

```bash
cd backend && python -m pytest tests/test_seguridad_sqli.py -v
```

Prueba, con 7 payloads clásicos (`' OR 1=1 --`, `'; DROP TABLE usuarios; --`, `UNION SELECT…`, `SLEEP(5)`…):

1. En el correo → **422**, no llega a la BD.
2. En la contraseña con un correo real → no inicia sesión.
3. Saltando la validación (llamando directo al repositorio) → devuelve `None` y **la tabla sigue intacta**.
4. El texto SQL contiene el marcador `:correo` y **no** el payload; en ejecución el payload aparece en los *parámetros*, no en la sentencia.
5. La búsqueda del catálogo y los ids de ruta también resisten payloads.

**Prueba de que las pruebas sirven (mutación):** reemplacé temporalmente la consulta por una versión con
concatenación de cadenas y **7 pruebas fallaron** (con la versión segura pasan las 27). Es decir, si alguien introduce
una consulta vulnerable, el CI se pone en rojo.

## 5. Otras medidas relacionadas ya presentes

- **Rate limiting** en login: 10 intentos / 15 min por IP → 429 (frena fuerza bruta).
- Mismo mensaje y código (401) para "correo inexistente" y "contraseña incorrecta": no se puede enumerar usuarios.
- Comodines de `LIKE` escapados (`utils/busqueda.py`): buscar `%` ya no devuelve todo el catálogo.
- El registro público nunca crea administradores (rol forzado a `cliente`).
- Contraseñas bcrypt; tokens JWT con `token_version` para revocarlos al cambiar la contraseña.

## 6. Preguntas típicas de sustentación

- **¿Qué es una consulta preparada y por qué evita la inyección?** Separa código SQL y datos; el motor nunca ejecuta el dato como código.
- **¿Por qué dos formularios en el login?** Añade una capa (validar formato antes de enviar) y evita revelar si el correo existe; pero no reemplaza al backend.
- **¿Basta con validar en el frontend?** No: se salta con cualquier cliente HTTP. Se valida y parametriza siempre en el servidor.
- **¿El ORM protege?** Sí, porque parametriza; se vuelve vulnerable si se usa `text(f"...{dato}...")` con datos del usuario.
