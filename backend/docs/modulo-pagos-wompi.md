# Módulo de pagos (Wompi Colombia — Sandbox)

Este documento complementa `README.md`: solo cubre lo específico del
módulo de pagos (`/api/pagos`, `/api/webhooks/wompi`). El resto de la
instalación (XAMPP, `.env`, `schema_fastapi.sql`, etc.) es la misma que ya
describe el README principal.

## 1. Qué se agregó

- `POST /api/pagos` — crea un pago y genera un enlace de **Checkout Web de
  Wompi** (redirección firmada; el backend nunca toca datos de tarjeta).
- `GET /api/pagos/{id}` y `GET /api/pagos/referencia/{referencia}` — consulta
  un pago ya creado.
- `POST /api/pagos/{id}/sync` — le pregunta directamente a Wompi el estado
  actual de la transacción y actualiza el registro local.
- `POST /api/webhooks/wompi` — recibe las notificaciones automáticas de Wompi
  cuando cambia el estado de una transacción.
- `GET /health` y `GET /health/db`.

Arquitectura interna: `router → service → repository → base de datos`, y
`service → PaymentProvider (Wompi) → API de Wompi`, con el proveedor detrás
de una interfaz (`app/services/pagos/payment_provider.py`) para poder agregar
Mercado Pago, ePayco, PayU o Stripe más adelante sin tocar `PaymentService`.

## 2. Variables de entorno

Agrega esto a tu `backend/.env` (ver `.env.example`):

```
PAYMENT_ENV=sandbox
WOMPI_PUBLIC_KEY=pub_test_xxxxxxxxxxxxxxxxxxxxxxxx
WOMPI_PRIVATE_KEY=prv_test_xxxxxxxxxxxxxxxxxxxxxxxx
WOMPI_EVENTS_SECRET=test_events_xxxxxxxxxxxxxxxxxxxxxxxx
WOMPI_INTEGRITY_SECRET=test_integrity_xxxxxxxxxxxxxxxxxxxxxxxx
WOMPI_API_URL=https://sandbox.wompi.co/v1
WOMPI_CHECKOUT_URL=https://checkout.wompi.co/p/
```

### Cómo obtener las credenciales de Sandbox

1. Crea una cuenta de comercio en <https://comercios.wompi.co/> (o pide que te
   agreguen como usuario al comercio de pruebas del proyecto).
2. En el Dashboard de Comercios, ve a **Configuración → Desarrolladores**
   para copiar `WOMPI_PUBLIC_KEY` (empieza con `pub_test_`) y
   `WOMPI_PRIVATE_KEY` (empieza con `prv_test_`).
3. En la misma sección, en **"Secretos para integración técnica"**, copia por
   separado el **secreto de eventos** (`WOMPI_EVENTS_SECRET`) y el **secreto
   de integridad** (`WOMPI_INTEGRITY_SECRET`) — son dos valores distintos, no
   uses el mismo para ambos.
4. En **"URL de eventos"** registra `http://TU_DOMINIO/api/webhooks/wompi`
   (en local necesitas exponerlo con algo como `ngrok http 8000` para que
   Wompi pueda llamarte — `localhost` no es alcanzable desde internet).

## 3. Cómo probar desde Swagger

1. Levanta el backend como siempre: `uvicorn app.main:app --reload`.
2. Abre <http://localhost:8000/docs>.
3. Inicia sesión con `POST /api/auth/login`, copia el `access_token`.
4. Haz clic en **Authorize** y pega `Bearer <token>`.
5. Prueba `POST /api/pagos` con un body como:

   ```json
   {
     "monto": 50000,
     "moneda": "COP",
     "correo_cliente": "cliente@example.com",
     "nombre_cliente": "Cliente Demo",
     "descripcion": "Pago de prueba"
   }
   ```

6. Copia el `checkout_url` de la respuesta y ábrelo en el navegador: ahí
   Wompi te deja pagar con las [tarjetas y cuentas de prueba de
   Sandbox](https://docs.wompi.co/docs/colombia/prueba-tu-integracion/)
   (Sandbox nunca hace un cobro real).
7. Cuando termines el pago, Wompi llama a tu webhook automáticamente. Si no
   tienes el webhook expuesto a internet, usa `POST /api/pagos/{id}/sync`
   para consultar el estado directamente.

## 4. Cómo probar con Postman

Importa `postman-fastapi/ESSENTIA-Pagos-Wompi.postman_collection.json`
(además de la colección principal, para el login). Configura `base_url` y,
tras hacer login en la colección principal, pega el token en la variable de
entorno `token`. El request "Crear pago" guarda automáticamente `payment_id`
y `reference` para las siguientes peticiones de la colección.

## 5. Cómo probar el webhook manualmente

El request "Webhook Wompi" de la colección de Postman trae un checksum de
ejemplo que **no es válido** (no se puede calcular sin tu
`WOMPI_EVENTS_SECRET` real). Para simular un evento válido:

```python
import hashlib

def checksum(id_transaccion, status, amount_in_cents, timestamp, secreto):
    cadena = f"{id_transaccion}{status}{amount_in_cents}{timestamp}{secreto}"
    return hashlib.sha256(cadena.encode()).hexdigest()

print(checksum("1234-1610641025-49201", "APPROVED", 5000000, 1530291411, "TU_WOMPI_EVENTS_SECRET"))
```

Pega ese valor en `signature.checksum` del body y ajusta `data.transaction.reference`
para que coincida con la `reference` de un pago que ya hayas creado.

## 6. Cómo ejecutar los tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/test_pagos.py -v
```

No necesitas MySQL/XAMPP levantado ni credenciales reales de Wompi: estos
tests usan SQLite en memoria y mockean cualquier llamada HTTP a Wompi (ver
`tests/conftest.py`). El test existente `tests/test_endpoint_roles_403.py`
(que sí necesita el servidor real corriendo) no se ve afectado.

## 7. Pasar de Sandbox a Producción

1. En el Dashboard de Comercios, activa el comercio en modo Producción
   (Wompi requiere validar la cuenta bancaria del negocio).
2. Reemplaza en `backend/.env`:
   - `WOMPI_PUBLIC_KEY` / `WOMPI_PRIVATE_KEY` por las de producción
     (`pub_prod_...` / `prv_prod_...`).
   - `WOMPI_EVENTS_SECRET` / `WOMPI_INTEGRITY_SECRET` por los de producción.
   - `WOMPI_API_URL=https://production.wompi.co/v1`
   - `PAYMENT_ENV=production`
3. `WOMPI_CHECKOUT_URL` normalmente no cambia (el dominio de Checkout es el
   mismo; Wompi identifica sandbox vs. producción por el prefijo de la llave
   pública).
4. Verifica en el Dashboard que la URL de eventos apunte a tu dominio real
   (HTTPS) y no a `ngrok`/`localhost`.
5. Prueba con un cobro real de bajo monto antes de anunciar el cambio.

## 8. Decisiones de diseño (por qué no es igual al PDF original)

Este módulo se adaptó al backend real del proyecto en vez de introducir un
stack paralelo:

- **MySQL + SQLAlchemy síncrono**, no PostgreSQL + async: todo el resto del
  backend (`app/routes/pedidos.py`, `app/database.py`, etc.) ya es síncrono
  sobre MySQL/XAMPP.
- **Sin Alembic ni Docker**: el proyecto ya sincroniza el esquema con
  `sincronizar_esquema()` en `app/database.py` (crea tablas/columnas que
  falten al arrancar) y corre sobre XAMPP en desarrollo — se agregó la tabla
  `pagos` a `database/schema_fastapi.sql` en vez de introducir un sistema de
  migraciones y contenedores nuevos.
- **PK entero autoincremental**, no UUID: mismo criterio que el resto de las
  tablas del proyecto (`usuarios`, `pedidos`, `productos`).
- **Web Checkout de Wompi** en vez de `POST /transactions` directo: evita
  que el backend tenga que manejar tokens de tarjeta, que solo deberían
  generarse en el navegador del cliente con la llave pública.
