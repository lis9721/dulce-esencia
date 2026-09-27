# Quinto Avance — Resumen de cambios

Este documento resume TODO lo que se agregó al proyecto existente (React + Vite →
FastAPI → SQL) para cumplir los requerimientos del quinto avance. No se tocó nada
de lo ya construido en avances anteriores (auth, roles, productos, servicios,
carrito, pedidos, cupones) salvo para conectar los módulos nuevos.

## 1. Base de datos

`backend/database/schema_fastapi.sql` ahora incluye 7 tablas nuevas al final,
antes de los datos semilla:

- `ventas` / `detalle_ventas`
- `facturas` / `detalle_facturas`
- `pqr`
- `conversaciones` / `mensajes`

Ejecuta de nuevo todo el script en phpMyAdmin (usa `CREATE TABLE IF NOT EXISTS`,
así que no rompe lo que ya existe) o deja que SQLAlchemy las cree solas al
arrancar el backend (`sincronizar_esquema` en `app/database.py` ya las
detectará porque están registradas en `app/models/__init__.py`).

## 2. Backend (FastAPI)

### Módulos nuevos
| Archivo | Qué hace |
|---|---|
| `app/models/venta.py` | `Venta` + `DetalleVenta` (productos y/o servicios) |
| `app/models/factura.py` | `Factura` + `DetalleFactura` (generada desde una venta) |
| `app/models/pqr.py` | `PQR` (petición/queja/reclamo/sugerencia) |
| `app/models/chatbot.py` | `Conversacion` + `Mensaje` |
| `app/schemas/venta.py`, `factura.py`, `pqr.py`, `chatbot.py`, `estadisticas.py` | Validación Pydantic de cada módulo |
| `app/routes/ventas.py` | `POST/GET /api/ventas`, `POST /api/ventas/desde-pedido/{id}`, `PATCH /api/ventas/{id}/estado` |
| `app/routes/facturas.py` | `POST/GET /api/facturas`, `GET /api/facturas/{id}/pdf` |
| `app/routes/reportes.py` | `GET /api/reportes/ventas/diario` (+ `/pdf`, `/excel`) |
| `app/routes/pqr.py` | `POST/GET/PATCH /api/pqr` |
| `app/routes/chatbot.py` | `POST /api/chatbot/mensaje`, `GET /api/chatbot/conversaciones/{id}` |
| `app/routes/estadisticas.py` | `GET /api/estadisticas/admin`, `GET /api/estadisticas/ventas` |
| `app/utils/factura_venta.py` | PDF de una factura de venta (reportlab) |
| `app/utils/reportes.py` | Reporte diario en JSON/PDF/Excel (reportlab + openpyxl) |
| `app/services/chatbot/ai_service.py` | Llamada al proveedor de IA (OpenAI-compatible) |

### Decisión de diseño: `Venta` vs `Pedido`
El proyecto ya tenía `Pedido`/`PedidoItem` (checkout del sitio). En vez de
duplicar esa lógica, `Venta` es el módulo de **punto de venta** que:
- Permite vender **productos Y servicios** juntos (Pedido solo maneja productos).
- Lo puede registrar directamente un admin/empleado (venta presencial/telefónica).
- También puede **generarse automáticamente** desde un pedido ya pagado del
  sitio web: `POST /api/ventas/desde-pedido/{pedido_id}`. Así el historial de
  ventas/reportes/dashboards también refleja las compras normales del sitio.

### Seguridad
- Todas las rutas de gestión (`POST/PATCH` de ventas, facturas, reportes,
  gestión de PQR) están protegidas con `requiere_rol("admin", "empleado")`,
  igual que el resto del proyecto.
- `POST /api/pqr` y `POST /api/chatbot/mensaje` son accesibles para cualquier
  usuario (la segunda incluso sin sesión — un invitado también puede chatear).
- La API Key de IA se lee **solo** de la variable de entorno
  `OPENAI_API_KEY` (nunca hardcodeada, nunca recibida por parámetro). Si no
  está configurada, el chatbot responde con un mensaje amable en vez de
  romperse, y el resto de la API sigue funcionando normal.

### Variables de entorno nuevas (`backend/.env` / `.env.example`)
```
OPENAI_API_KEY=       # tu clave — nunca la subas a GitHub
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=      # vacío = OpenAI; o el endpoint de otro proveedor compatible
```

### Dependencias nuevas (`requirements.txt`)
```
openai==1.109.1
openpyxl==3.1.5
```
Instala con:
```
cd backend
pip install -r requirements.txt --break-system-packages   # o dentro de tu venv
```

## 3. Frontend (React + Vite)

### Nuevo en `utils/api.js`
Funciones para ventas, facturas, reportes, estadísticas, PQR y chatbot
(con descarga de PDF/Excel), siguiendo el mismo patrón camelCase↔snake_case
ya usado en todo el archivo.

### Componentes nuevos
- `components/charts/BarChart.jsx` y `LineChart.jsx`: gráficos livianos en
  SVG puro, **sin agregar ninguna librería nueva** al `package.json`.
- `components/ui/StatCard.jsx`: tarjeta de indicador para los dashboards.
- `components/Chatbot.jsx`: widget flotante de chat, montado globalmente en
  `App.jsx` (igual que el botón de WhatsApp) — funciona con o sin sesión.

### Páginas nuevas (`pages/panel/`)
- `Dashboard.jsx`: cards administrativas (solo admin) + gráficos de ventas
  con filtros de fecha/agrupación/producto/servicio/estado/cliente (admin y
  empleado).
- `GestionVentas.jsx`: formulario para registrar una venta (cliente + ítems
  producto/servicio + cantidades), historial con filtros, botón para
  facturar/anular, y descarga del reporte diario en PDF/Excel.
- `Facturas.jsx`: listado/búsqueda de facturas y descarga en PDF. Un cliente
  ve solo las suyas; admin/empleado ven todas.
- `GestionPQR.jsx`: un cliente registra y ve sus PQR; admin/empleado ven
  todas, filtran por estado y responden.

### Rutas y navegación
`constants/rolesPanel.js`, `pages/Panel.jsx` y `App.jsx` quedaron
actualizados con las pestañas y rutas nuevas:
- `/panel/dashboard` y `/panel/ventas` — solo admin/empleado.
- `/panel/facturas` y `/panel/pqr` — cualquier usuario autenticado (el
  backend ya filtra "solo lo mío" para un cliente).

## 4. Cómo probar rápido (Postman / Swagger)

1. Levanta el backend (`uvicorn app.main:app --reload`) y entra a
   `http://localhost:8000/docs`.
2. Inicia sesión como admin (`POST /api/auth/login`) y usa el token en
   "Authorize".
3. Registra una venta: `POST /api/ventas` con un `cliente_id` real y al
   menos un ítem (`producto_id` o `servicio_id`, nunca ambos).
4. Genera su factura: `POST /api/facturas` con el `venta_id` devuelto.
5. Descarga el PDF: `GET /api/facturas/{id}/pdf`.
6. Consulta el reporte del día: `GET /api/reportes/ventas/diario` (o
   `/pdf`, `/excel`).
7. Revisa los dashboards: `GET /api/estadisticas/admin` y
   `GET /api/estadisticas/ventas`.
8. Prueba el chatbot: `POST /api/chatbot/mensaje` con
   `{"mensaje": "hola"}` (si no configuraste `OPENAI_API_KEY`, responde con
   el mensaje de "no disponible" en vez de fallar).
9. Registra y gestiona una PQR: `POST /api/pqr`, luego
   `PATCH /api/pqr/{id}` (como admin/empleado) para responder.

## 5. Pendiente de tu parte (no es código, es configuración/infraestructura)

- Configurar `OPENAI_API_KEY` real en `backend/.env` para que el chatbot
  responda con IA de verdad.
- Ejecutar `pip install -r requirements.txt` y `npm install` (por si hiciera
  falta) en tus máquinas locales — este entorno de trabajo no tenía acceso a
  internet para instalarlas y probarlas en caliente, así que revisa la
  primera corrida con calma.
- Despliegue en producción (Railway u otra plataforma): sigue usando el
  mismo `backend/.env` / variables de entorno del servidor, agregando las
  nuevas (`OPENAI_API_KEY`, etc.) junto a las que ya tenías.
