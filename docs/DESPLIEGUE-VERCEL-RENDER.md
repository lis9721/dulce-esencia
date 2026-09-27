# Guía de despliegue — Dulce Esencia (Vercel + Render + BD en la nube)

Revisé tu proyecto: es un **backend FastAPI (Python)** en `backend/` +
un **frontend React/Vite** en `frontend/`, con MySQL/MariaDB corriendo
hoy en XAMPP local. Esta guía explica los conceptos previos y los
pasos concretos para desplegarlo con **frontend en Vercel, backend en
Render y base de datos en un proveedor en la nube**.

> ⚠️ **Aviso importante sobre tu propio repo**: ya existe un
> `docs/DEPLOY.md` y un `vercel.json` en tu proyecto, pero están
> escritos para una arquitectura **distinta** a la que pediste: un
> único proyecto de Vercel con "Services" (frontend Y backend juntos
> en Vercel) + base de datos TiDB, todo mismo dominio, sin CORS. Lo que
> tú quieres (backend en Render, aparte) es una topología diferente y
> válida, pero significa que **no vas a usar el `vercel.json` actual
> tal cual**, y sí vas a necesitar configurar CORS explícitamente
> (cosa que ese documento decía que no hacía falta, precisamente
> porque asumía el otro escenario). Esta guía te lleva por el camino
> de Vercel + Render que pediste.

---

## Parte 1 — Conceptos previos (qué es "desplegar" y por qué importa)

**Desplegar (deploy)** es tomar tu proyecto, que hoy solo corre en tu
computador, y ponerlo en un servidor accesible por internet las 24
horas, para que cualquiera pueda entrar sin que tu PC esté encendido.

Unos conceptos que vas a necesitar sí o sí:

- **Entorno local vs. producción**: en tu PC, el backend habla con
  MySQL en `127.0.0.1` (XAMPP) y el frontend con
  `http://localhost:8000`. En producción no existe ni "localhost" ni
  XAMPP — cada pieza vive en un servidor distinto, con su propia
  dirección pública (URL).
- **Variables de entorno**: son los datos que cambian entre tu PC y el
  servidor (contraseña de la BD, claves secretas, URLs) y que **nunca**
  se escriben directo en el código ni se suben a GitHub. Se configuran
  por fuera, en el panel de cada plataforma (Vercel, Render). Tu
  proyecto ya sigue esta práctica — mira `backend/.env.example`.
- **Repositorio Git**: Vercel y Render despliegan **desde GitHub**, no
  subiendo un ZIP a mano. Necesitas tu código en un repo (público o
  privado) antes de poder conectar nada.
- **CORS (Cross-Origin Resource Sharing)**: por seguridad, un
  navegador bloquea que el frontend (`https://tuapp.vercel.app`) le
  hable a un backend en otro dominio (`https://tuapp.onrender.com`) *a
  menos que* el backend lo autorice explícitamente. Como vas a tener
  frontend y backend en dominios distintos, esto **sí** te va a tocar
  configurar (variable `CORS_ORIGIN` en tu backend).
- **TLS/SSL hacia la base de datos**: casi todo proveedor de BD en la
  nube exige conexión cifrada (a diferencia de XAMPP local). Tu
  proyecto ya tiene esto resuelto con la variable `DB_SSL` en
  `backend/app/database.py` — solo hay que ponerla en `true`.
- **Cold start / hibernación en planes gratis**: en el plan free de
  Render, tu backend se "duerme" tras ~15 min sin tráfico y tarda unos
  segundos en despertar en la próxima petición. Es normal, no es un
  error.
- **Filesystem efímero**: Render (igual que casi cualquier plataforma
  moderna) **borra los archivos** que tu app escriba en disco cada vez
  que se reinicia o se redespliega. Tu backend guarda imágenes subidas
  en `backend/uploads/productos/` y `backend/uploads/servicios/` — eso
  **no sobrevive** un redeploy en Render. Lo cubro en la Parte 4.

---

## Parte 2 — Requisitos previos (antes de tocar nada)

- [ ] Cuenta de **GitHub**, con tu proyecto subido a un repositorio
      (`git init`, `git add`, `git commit`, `git push`). Si nunca lo
      has hecho, dime y te doy los comandos exactos.
- [ ] Cuenta en **[vercel.com](https://vercel.com)** (gratis, plan
      Hobby).
- [ ] Cuenta en **[render.com](https://render.com)** (gratis, plan
      Free para Web Services).
- [ ] Cuenta en el proveedor de base de datos que elijas (Parte 3).
- [ ] phpMyAdmin de tu XAMPP funcionando, para exportar tu BD actual
      (`essentia_db`).
- [ ] Tus claves reales a mano: `SECRET_KEY`, credenciales de Wompi,
      `OPENAI_API_KEY`, SMTP — todo lo que ves listado en
      `backend/.env.example`. Ninguna de estas va al repo; solo a los
      paneles de Render/Vercel.

---

## Parte 3 — Base de datos: sacarla de XAMPP

XAMPP corre MySQL/MariaDB **solo en tu máquina**; no es algo que se
"suba" — hay que migrar los datos a un proveedor que lo aloje 24/7.

### 3.1 Elegir proveedor

Cualquiera de estos sirve porque tu backend usa un `DATABASE_URL`
estándar `mysql+pymysql://` (ver `backend/app/config.py`), así que
solo necesitas un MySQL/MariaDB compatible:

| Proveedor | Gratis sin tarjeta | Notas |
|---|---|---|
| **Railway** | Sí (con límite de horas/uso) | MySQL con un clic |
| **Aiven** | Sí (trial) | MySQL administrado |
| **Clever Cloud** | Sí | MySQL con plan gratis pequeño |
| **TiDB Cloud Serverless** | Sí | Es lo que ya usa el `DEPLOY.md` de tu propio repo — compatible con MySQL, pero no es 100% "drop-in" (ver notas de compatibilidad ahí) |

Si tu BD no es muy grande y no te preocupa una capa gratis con
límites, **Railway** o **Clever Cloud** suelen ser los más simples
para un MySQL "de verdad" (sin las particularidades de TiDB).

### 3.2 Exportar desde XAMPP

1. Abre `http://localhost/phpmyadmin`.
2. Selecciona la base `essentia_db` (o el nombre que le hayas puesto).
3. Pestaña **Exportar** → método **Rápido** → formato **SQL** →
   Exportar. Esto descarga un `.sql` con estructura + datos.

### 3.3 Crear la base en el proveedor elegido

1. Crea la instancia/cluster MySQL en el panel del proveedor.
2. Anota: **host**, **puerto**, **usuario**, **contraseña**, **nombre
   de la base**.
3. Importa el `.sql` que exportaste — cada proveedor trae su propia
   forma (un botón de "Import", o conectándote por línea de comandos
   con `mysql -h HOST -P PUERTO -u USUARIO -p NOMBRE_BD < archivo.sql`).

> Si prefieres no importar el `.sql` a mano, tu proyecto también trae
> `backend/seed.py` y una sincronización automática de esquema
> (`sincronizar_esquema()` en `app/database.py`) que crea las tablas
> solas la primera vez que el backend arranca contra la BD nueva —
> pero en ese caso partes con la base vacía, sin tus datos actuales de
> XAMPP.

---

## Parte 4 — Backend en Render

1. En Render → **New** → **Web Service** → conecta tu repo de GitHub.
2. **Root Directory**: `backend`
3. **Runtime**: Python 3
4. **Build Command**:
   ```
   pip install -r requirements.txt
   ```
5. **Start Command**:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
   (Render inyecta `$PORT` automáticamente; no uses el 8000 fijo).
6. **Health Check Path**: `/health` (tu proyecto ya trae ese endpoint
   en `app/routes/health.py`).
7. Variables de entorno (Render → Environment), tomando como base
   `backend/.env.example`:

   | Variable | Valor en Render |
   |---|---|
   | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Los del proveedor de BD (Parte 3) |
   | `DB_SSL` | `true` |
   | `SKIP_SCHEMA_SYNC` | `false` la primera vez (para que cree las tablas), luego puedes pasarlo a `true` si quieres evitar que corra en cada arranque |
   | `SECRET_KEY` | Genera una propia: `python -c "import secrets; print(secrets.token_hex(48))"` — nunca la de ejemplo |
   | `ALGORITHM` | `HS256` |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` |
   | `NODE_ENV` | `production` |
   | `CORS_ORIGIN` | La URL de tu frontend en Vercel, ej. `https://tu-proyecto.vercel.app` (sin barra final) |
   | `APP_URL` | La URL pública que te da Render, ej. `https://tu-backend.onrender.com` |
   | `PAYMENT_ENV`, `WOMPI_*` | Tus claves reales de Wompi (sandbox o producción) |
   | `OPENAI_API_KEY`, `OPENAI_MODEL` | Tu clave real, si usas el chatbot |
   | `SMTP_*` | Tus datos de correo saliente, si los usas |

8. Despliega y prueba `https://tu-backend.onrender.com/health` y
   `https://tu-backend.onrender.com/docs` (Swagger) antes de tocar el
   frontend.

### Nota sobre las imágenes subidas (`backend/uploads/`)

Render borra archivos escritos en disco en cada redeploy. Como tu
backend guarda ahí las fotos de productos/servicios subidas desde el
panel, **las perderás en el próximo deploy**. Para producción real,
la solución correcta es mover ese guardado a almacenamiento externo
(Cloudinary, AWS S3, o similar) en vez de disco local. Si por ahora
solo quieres probar el despliegue, puedes dejarlo así y resolverlo
después — solo ten en cuenta que no es persistente.

---

## Parte 5 — Frontend en Vercel

1. En Vercel → **Add New** → **Project** → importa el mismo repo.
2. **Root Directory**: `frontend`
3. Framework detectado: **Vite** (automático, gracias a
   `frontend/vite.config.js`).
4. **Build Command**: `npm run build` (o el que Vercel autodetecte).
5. **Output Directory**: `dist` (por defecto de Vite).
6. Variable de entorno en Vercel:

   | Variable | Valor |
   |---|---|
   | `VITE_API_URL` | `https://tu-backend.onrender.com/api` (URL **absoluta**, no `/api` — a diferencia de lo que asume el `.env.example` de la raíz de tu repo, que es para cuando frontend y backend comparten dominio) |

7. Despliega.

---

## Parte 6 — Conectar las piezas y probar

1. Confirma que `CORS_ORIGIN` en Render tiene **exactamente** la URL
   de Vercel (revisa `app/config.py`: en producción, `CORS_ORIGIN` se
   separa por comas y se usa tal cual, sin comodines `*`).
2. Abre tu sitio de Vercel, intenta iniciar sesión o cargar productos,
   y revisa la pestaña **Network** del navegador: si ves errores CORS,
   el dominio en `CORS_ORIGIN` no coincide exactamente (revisa http vs
   https, y que no sobre una barra `/` al final).
3. Primera petición puede tardar unos segundos si el backend en Render
   estaba dormido (plan free) — es normal.

---

## Resumen del flujo

```
XAMPP (local)  →  exportar .sql  →  importar en proveedor de BD en la nube
Backend FastAPI  →  Render (Web Service, root: backend/)
Frontend Vite    →  Vercel (root: frontend/, VITE_API_URL absoluto)
```

Si en algún momento quieres seguir el camino que tu propio repo ya
documentó (un solo proyecto de Vercel con "Services" + TiDB, sin CORS
que configurar), usa en cambio `docs/DEPLOY.md` — es una alternativa
completa y ya escrita, solo que es un enfoque distinto al que pediste
aquí.
