# Parte 5 — Endpoints faltantes del backend Python

Contexto: al revisar `frontend/src/utils/api.js` (Parte 7) contra las
rutas reales de `backend/app/routes/*.py` quedaron anotados varios
`// TODO Parte 8` de rutas que el frontend llama pero que **no existían
en el backend**. Esta parte cierra esas rutas — es la que desbloquea
tanto la prueba end-to-end registro→login→navbar→logout como el uso
real de los paneles admin/empleado/cliente contra la API.

## El hallazgo más importante

**Sin `POST /api/usuarios/verificar-correo`, ningún usuario recién
registrado podía iniciar sesión jamás.** `POST /registro` deja la
cuenta con `verificado=False` y `POST /auth/login` la rechaza con 403
mientras siga así — y la ruta que la marca como verificada no existía
en el backend Python (solo se habían migrado recuperar/restablecer de
contraseña). Esto bloqueaba la prueba e2e desde el primer paso, antes
de siquiera llegar a "login".

## Endpoints nuevos

| Método | Ruta | Rol | Qué hace |
|---|---|---|---|
| POST | `/api/usuarios/verificar-correo` | pública | Confirma el enlace de verificación de `/registro`. Sin esto, ningún registro llegaba nunca a poder loguearse. |
| GET | `/api/usuarios/perfil` | cualquiera autenticado | Datos del usuario logueado — lo necesita `AuthContext.jsx` para saber si hay sesión al montar la app, y para poblar el navbar/menú de cuenta. |
| PUT | `/api/usuarios/perfil` | cualquiera autenticado | Edita nombre/apellido/dirección/teléfono propios (nunca correo, documento, password ni rol). |
| PUT | `/api/usuarios/perfil/password` | cualquiera autenticado | Cambia la contraseña propia, confirmando la actual. |
| POST | `/api/usuarios` | admin | Crea un usuario desde el panel con el rol que indique el admin (a diferencia de `/registro`, que siempre fuerza `cliente` y deja la cuenta sin verificar); esta cuenta queda activa y verificada de inmediato. |
| PUT | `/api/usuarios/{id}/rol` | admin | Cambia el rol de un usuario. No se puede usar sobre la propia cuenta (mismo candado que ya existía en `/estado`). |
| POST | `/api/carrito/fusionar` | cualquiera autenticado | Fusiona el carrito de invitado (localStorage) con el de la BD al iniciar sesión. Un ítem sin stock suficiente se ajusta al máximo disponible en vez de abortar toda la fusión. |
| POST | `/api/productos/imagen` | admin/empleado | Sube el archivo de imagen de un producto a `uploads/productos/` y devuelve el nombre generado. |

## Dependencia nueva

`requirements.txt` ahora incluye `python-multipart==0.0.20` —
**obligatoria** para que FastAPI pueda parsear el `multipart/form-data`
de `POST /productos/imagen`. Sin reinstalar, esa ruta específica falla
al arrancar el proceso de subida (las demás rutas de este mismo avance
no la necesitan). Correr de nuevo:

```
pip install -r requirements.txt
```

## Lo que se dejó FUERA de esta parte (a propósito)

- **`GET /pedidos/{id}/factura` (PDF de factura):** no hay ninguna
  librería de generación de PDF en `requirements.txt` (ni reportlab,
  ni weasyprint, ni fpdf2). Agregar una es una decisión de dependencia
  que preferí no tomar por ti sin preguntarte — dime cuál prefieres (o
  si no importa cuál) y la implemento en la próxima parte. No bloquea
  ni el flujo e2e ni los paneles: es un botón de "descargar factura",
  no algo que impida navegar/usar el panel de pedidos.
- **La traducción de contrato de datos completa** (`snake_case` vs
  `camelCase`, verbos/paths distintos como `/carrito/items` vs
  `/carrito`, `idempotency_key` en body vs header) sigue siendo
  responsabilidad de la Parte 8, marcada con `// TODO Parte 8` en
  `frontend/src/utils/api.js`. Los endpoints nuevos de esta parte
  **ya responden en `snake_case`** consistente con el resto del
  backend — `subirImagenProducto()` del frontend, por ejemplo, sigue
  leyendo `datos.rutaImagen` (camelCase) y hoy recibiría `undefined`
  hasta que la Parte 8 lo ajuste; quedó anotado con un TODO en el
  propio código del backend para que no se pierda ese detalle.

## Cómo probarlo

1. `pip install -r requirements.txt` (por `python-multipart`).
2. `uvicorn app.main:app --reload`.
3. Con Swagger UI (`/docs`) o Postman:
   - `POST /api/usuarios/registro` → copia el `tokenVerificacion` que
     devuelve en modo desarrollo (o el enlace impreso en la consola
     del servidor).
   - `POST /api/usuarios/verificar-correo` con `{correo, token}` →
     debería responder 200.
   - `POST /api/auth/login` con esas credenciales → ahora sí debería
     devolver el `access_token` (antes de esta parte, daba 403 sin
     importar qué hicieras).
   - Con ese token: `GET /api/usuarios/perfil` debería devolver el
     usuario recién creado.
4. Como admin: `POST /api/usuarios` con un `rol` distinto de
   `cliente`, y `PUT /api/usuarios/{id}/rol` sobre un usuario que no
   seas tú mismo.
