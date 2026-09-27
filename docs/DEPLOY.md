# Despliegue — Vercel (Services) + TiDB Cloud Starter

Runbook para desplegar **Dulce Esencia Pastelería** (frontend React/Vite +
backend FastAPI, en un solo proyecto de Vercel) con base de datos en
TiDB Serverless. Costo: **$0, sin tarjeta de crédito**, uso no comercial
(plan Hobby de Vercel).

> Repositorio asumido: `lis9721/dulce-esencia`, rama de producción `main`.
> Si le pones otro nombre al repo o usas otra rama, ajusta esos dos
> valores en `.github/workflows/ci.yml` y `.github/workflows/deploy.yml`
> (los `branches: [main]`) y en las URLs de este documento.

## Plan (flujo de ramas y qué dispara qué)

1. Trabajas en una rama o directo en `main` → abres/actualizas un PR.
2. `ci.yml` corre en el PR: ruff + pytest + contrato OpenAPI (backend),
   lint + build (frontend). Cambios solo en `frontend/` no disparan la
   suite de Python y viceversa.
3. Al hacer merge a `main`, `ci.yml` corre otra vez sobre `main`.
4. Si `ci.yml` termina en verde sobre `main`, `deploy.yml` se dispara
   solo: tests → sincroniza el esquema en la TiDB de producción →
   `vercel deploy --prod` → verifica `/health/db` con reintentos.
5. Cada Pull Request además recibe un **Preview Deployment automático**
   de Vercel (nativo de la plataforma, no lo dispara GitHub Actions) —
   apunta a una base de datos de TiDB **separada** (ver paso 4 abajo),
   nunca a la de producción.

Secretos que hacen falta — de una sola vez, salvo que roten credenciales:

| Dónde se guarda | Nombre | Para qué |
|---|---|---|
| GitHub Secrets | `VERCEL_TOKEN` | Autenticar la Vercel CLI desde Actions |
| GitHub Secrets | `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` | Identificar el proyecto (salen de `vercel link`) |
| GitHub Secrets | `PROD_DB_HOST`, `PROD_DB_PORT`, `PROD_DB_NAME`, `PROD_DB_USER`, `PROD_DB_PASSWORD` | Que el paso de "migración" del pipeline pueda conectarse a la TiDB de producción |
| Variables de entorno del proyecto en Vercel (Production) | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSL`, `SKIP_SCHEMA_SYNC`, `SECRET_KEY`, `WOMPI_*`, `OPENAI_API_KEY`, `SMTP_*`, `VITE_API_URL` | Que la app en sí funcione en runtime — ver `.env.example` en la raíz |
| Variables de entorno del proyecto en Vercel (Preview) | Los mismos nombres, con una TiDB **distinta** y llaves de Wompi Sandbox | Que los Preview Deployments de cada PR no toquen producción |

Los mismos valores de `PROD_DB_*` (GitHub Secrets) y `DB_*` (Vercel,
Production) apuntan a la misma TiDB — viven duplicados a propósito
porque el pipeline (GitHub Actions) y la app en runtime (Vercel) son
dos sistemas distintos; ninguno de los dos debe leer secretos del otro.

Ningún token, contraseña ni cadena de conexión va al repositorio, ni
siquiera en `.env.example` con un valor "casi real".

## Checklist de configuración manual

### Una sola vez

- [ ] **Crear el repositorio** `lis9721/dulce-esencia` en GitHub (privado o
      público, a tu gusto — nada de este pipeline depende de eso) y
      subir este proyecto.
- [ ] **TiDB Cloud** → crear cuenta en [tidbcloud.com](https://tidbcloud.com)
      → crear un clúster **Serverless** en el plan **Starter** (no pide
      tarjeta). Crear dos bases de datos/clústeres separados: uno para
      producción y otro para previews (o, como mínimo, dos esquemas
      distintos dentro del mismo clúster).
- [ ] En cada clúster, botón **Connect** → copiar host, puerto (4000),
      usuario y generar una contraseña → estos son tus `DB_HOST`,
      `DB_PORT`, `DB_USER`, `DB_PASSWORD`.
- [ ] **Vercel** → crear cuenta en [vercel.com](https://vercel.com) (plan
      **Hobby**, sin tarjeta) → `vercel login` local, luego dentro del
      repo: `vercel link` → esto crea el proyecto y te da
      `VERCEL_ORG_ID` y `VERCEL_PROJECT_ID` (quedan en
      `.vercel/project.json`, que **no** se commitea).
- [ ] **Vercel** → generar un token personal: Account Settings → Tokens
      → este es tu `VERCEL_TOKEN`.
- [ ] **Desactivar el auto-deploy nativo de Vercel**: Project Settings →
      Git → desconectar la integración de Git (o dejar un *Ignored
      Build Step* que siempre devuelva `exit 1`). Sin esto, un push
      directo a `main` desplegaría sin pasar por `ci.yml`/`deploy.yml`.
- [ ] Cargar los **GitHub Secrets** de la tabla de arriba: repo →
      Settings → Secrets and variables → Actions.
- [ ] Cargar las **variables de entorno del proyecto en Vercel**, una
      vez para *Production* (TiDB de producción, llaves Wompi
      reales/sandbox según corresponda) y otra vez para *Preview* (TiDB
      de preview, llaves Wompi Sandbox siempre).
- [ ] Confirmar en el dashboard de Vercel que el proyecto reconoce
      `vercel.json` con **Services** (frontend Vite en `frontend/`,
      backend FastAPI en `backend/`) — la sintaxis exacta de este campo
      cambia entre versiones de la plataforma; si Vercel la rechaza al
      hacer `vercel build`, revisa la documentación vigente de
      "Vercel Services" y ajusta `vercel.json` en consecuencia (root,
      `entrypoint`, forma de las `rewrites`), sin tocar el resto del
      pipeline.

### Cada vez que haga falta (rotación de credenciales, etc.)

- [ ] Rotar `WOMPI_PRIVATE_KEY`/`WOMPI_EVENTS_SECRET`/`WOMPI_INTEGRITY_SECRET`
      al pasar de Sandbox a producción real (ver
      `backend/docs/modulo-pagos-wompi.md`) — solo se actualizan las
      variables de entorno en Vercel, nunca el código.
- [ ] Rotar `VERCEL_TOKEN` si expira o se expone por error.
- [ ] Rotar la contraseña de TiDB si se sospecha una fuga — actualizar
      tanto el GitHub Secret `PROD_DB_PASSWORD` como la variable
      `DB_PASSWORD` en Vercel.

## Por qué frontend y backend NO necesitan CORS

Al vivir bajo el mismo dominio de Vercel (un solo proyecto, con
`vercel.json` enrutando `/api/*` al servicio `backend` y todo lo demás
al servicio `frontend`), cada petición del frontend a `/api/...` es
*same-origin* — por eso `VITE_API_URL=/api` (ruta relativa) y no una URL
absoluta. `CORS_ORIGIN` queda vacío en producción.

Si en algún momento el repo se separara en dos proyectos de Vercel
(frontend y backend cada uno con su propio dominio), ahí sí hay que
resolver CORS explícitamente en `CORS_ORIGIN` (nunca con `allow_origins=["*"]`,
ver `backend/app/config.py`) — pero mientras se mantenga como un solo
proyecto con Services, no hace falta tocar nada de CORS.

## Arranque en frío (cold start)

Vercel escala la función del backend con el tráfico; una función sin
invocaciones recientes sufre cold start en la primera petición,
especialmente al reabrir el pool de conexión hacia TiDB. Mitigaciones
ya aplicadas en este proyecto:

- La conexión a la base de datos se abre perezosamente (SQLAlchemy no
  conecta hasta el primer uso; ver `backend/app/database.py`).
- **`SKIP_SCHEMA_SYNC=true` en Vercel**: la sincronización de esquema
  (`sincronizar_esquema()`) ya NO corre en cada cold start del
  `lifespan` — corre una única vez desde `deploy.yml`, antes del
  deploy. Antes de este cambio, cada cold start repetía varias
  consultas `SHOW COLUMNS`/`ALTER TABLE` de forma innecesaria.

No existe forma gratuita de mantener la función permanentemente
caliente. Un *warm-up cron* por GitHub Actions es una opción, pero los
workflows programados de GitHub se desactivan solos tras 60 días sin
actividad en el repo — no es una solución permanente sin mantenimiento,
así que deliberadamente no se agregó uno aquí.

## TLS hacia TiDB

TiDB Cloud Starter usa certificados públicamente confiables (cadena
Let's Encrypt/pública) — no hace falta descargar ni guardar un CA
propio como secreto. `backend/app/database.py` centraliza esto en una
sola función (`_connect_args()`): si `DB_SSL=true`, usa
`ssl.create_default_context()` (verificación de identidad completa);
si `DB_SSL=false` (desarrollo local con XAMPP), no aplica TLS. Este
proyecto no usa Alembic, así que no hay un `env.py` separado que
pudiera desincronizarse de esta configuración — hay un único punto de
verdad.

## Suspensión / escalado a cero de TiDB Serverless

TiDB Serverless escala a cero tras inactividad; la primera consulta
después de ese período puede tardar más mientras el clúster despierta.
El paso final de `deploy.yml` (verificación de `/health/db`) reintenta
con backoff (5s, 10s, 15s...) en vez de fallar el deploy por un timeout
que se resuelve solo en segundos.

## Migraciones (por qué no hay Alembic)

Este proyecto no usa Alembic: la sincronización de esquema vive en
`app.database.sincronizar_esquema()` (crea tablas nuevas, agrega
columnas que falten). Adaptando el requisito de "migrar antes de
desplegar, nunca después":

- En Vercel, `SKIP_SCHEMA_SYNC=true` desactiva esa sincronización en el
  arranque normal de la función.
- `deploy.yml` la ejecuta una única vez, como paso explícito
  (`backend/scripts/sync_schema.py`), **antes** de `vercel deploy --prod`.
- Si ese paso falla, el job se detiene ahí — el deploy nunca llega a
  correr con un esquema a medio actualizar.

Si el proyecto migra a Alembic más adelante, ese mismo script es el
lugar natural para reemplazar la llamada por `alembic upgrade head`,
reutilizando el `_connect_args()` centralizado de `database.py`.

## Compatibilidad TiDB vs. MySQL

TiDB no es un MySQL "drop-in". Cosas a revisar en este esquema en
particular (`backend/database/schema_fastapi.sql`, modelos en
`backend/app/models/`):

- **Llaves foráneas**: TiDB las soporta desde varias versiones atrás,
  pero verifica que las definidas en los modelos (`ForeignKey(...)`)
  se creen sin error al correr `sync_schema.py` contra la TiDB real por
  primera vez — revisa la salida de ese paso en el log de `deploy.yml`.
- **Auto-incremento distribuido**: TiDB no garantiza IDs
  estrictamente consecutivos (son únicos, pero pueden tener saltos) —
  ningún código de este proyecto asume consecutividad, así que no
  debería haber impacto, pero es lo primero a revisar si algo asume
  "el siguiente ID es el actual + 1".
- **Triggers / procedimientos almacenados**: este proyecto no usa
  ninguno (toda la lógica vive en la capa de Python), así que no aplica.
- Como red de seguridad, la primera vez que `deploy.yml` corra contra
  la TiDB real de producción, revisa el log del paso "Sincronizar
  esquema en TiDB" con atención — es el momento en que cualquier
  incompatibilidad real (no solo teórica) va a aparecer.

## Migraciones fallidas

Si `backend/scripts/sync_schema.py` falla a mitad de camino: el paso
"Sincronizar esquema en TiDB (producción)" del job termina con código
distinto de 0, y GitHub Actions aborta el resto del job — los pasos de
`vercel deploy` y verificación de `/health` **no** corren. El código
viejo sigue sirviendo tráfico en Vercel (no hubo deploy nuevo); hay que
revisar el log de ese paso, corregir el problema (normalmente una
columna/tabla que no se pudo alterar) y volver a disparar `deploy.yml`
(`workflow_dispatch` o un nuevo push a `main`).

## Cómo probar cada pieza

- **CI en un PR**: abre cualquier PR contra `main` y revisa la pestaña
  Actions — jobs `backend` y `frontend` (o solo el que corresponda,
  según qué carpeta tocaste).
- **Preview Deployment**: Vercel comenta automáticamente el PR con la
  URL de preview — pruébala contra la TiDB de preview.
- **Deploy a producción**: se dispara solo al mergear a `main`. Para
  forzarlo manualmente sin un push nuevo: pestaña Actions → workflow
  **Deploy** → *Run workflow*.
- **Rollback**: si un deploy queda mal, usa el dashboard de Vercel
  (Deployments → ⋯ → *Promote to Production* sobre el deploy anterior)
  — no hace falta revertir el commit para volver atrás de inmediato.
