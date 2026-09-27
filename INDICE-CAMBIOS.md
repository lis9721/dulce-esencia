# Índice de esta entrega

Todo lo que está dentro de este .zip mantiene la **misma ruta relativa**
que tiene en tu proyecto original: solo tienes que copiar
cada carpeta/archivo encima de la tuya, respetando la ruta.

`mejoras-cuarto-avance.md` (en esta misma carpeta) es el documento de
planeación completo con el detalle y el razonamiento de cada punto; esta
lista es solo el mapa rápido de qué archivo corresponde a qué petición.

## 1. Header fijo (sticky)
- `frontend/src/components/Header.jsx` — modificado
- `frontend/src/index.css` — modificado (scroll-padding-top)

## 2. Menú de cuenta desplegable
- `frontend/src/components/Header.jsx` — modificado (mismo archivo del punto 1)
- `frontend/src/components/UserMenu.jsx` — **nuevo**
- `frontend/src/components/ui/iconPaths.js` — modificado (ícono chevronDown)

## 3. Footer profesional
- `frontend/src/components/Footer.jsx` — modificado
- `frontend/src/constants/enlacesNav.js` — **nuevo**
- `frontend/src/components/Header.jsx` — modificado (usa el nuevo enlacesNav.js)
- `frontend/src/components/ui/iconPaths.js` — modificado (íconos instagram/facebook/tiktok)

## 4. Postman automatizado con Newman
- `backend/package.json` — modificado (scripts postman / postman:html / test:e2e)
- `README.md` — modificado (documentación del nuevo flujo)
- `.gitignore` — modificado (ignora el reporte HTML generado)

  **Corrección importante tras tu prueba real:** al instalar `newman` como
  devDependency, `npm audit` marcó 20 vulnerabilidades (1 crítica, vía
  `handlebars` dentro del propio runtime de Newman) — problema de las
  dependencias internas de Postman, no de nada que hiciéramos. Por eso los
  scripts ya NO instalan `newman` como dependencia fija: lo corren con
  `npx --yes newman@6.2.2 ...`, que lo descarga/ejecuta al vuelo sin
  dejarlo en `package.json`/`package-lock.json`. Con esto, **no necesitas
  instalar nada de Newman a mano** — solo corre `npm install` (para que
  entre `start-server-and-test`, que sí es una dependencia normal, sin
  problemas) y los scripts `postman`/`postman:html`/`test:e2e` funcionan
  directo. La primera vez que los corras necesitas internet (npx descarga
  Newman una vez y lo cachea).

## 5. Panel con sidebar (admin/empleado/cliente)
- `frontend/src/pages/Panel.jsx` — modificado

## 6. Desvanecido al hacer scroll (Reveal bidireccional)
- `frontend/src/components/Reveal.jsx` — modificado

## 7. Animación en las tarjetas de producto
- `frontend/src/pages/Tienda.jsx` — modificado

---

## Todos los archivos de este .zip, de un vistazo

| Archivo | Estado |
|---|---|
| `frontend/src/components/Header.jsx` | modificado |
| `frontend/src/components/Footer.jsx` | modificado |
| `frontend/src/components/Reveal.jsx` | modificado |
| `frontend/src/components/UserMenu.jsx` | **nuevo** |
| `frontend/src/components/ui/iconPaths.js` | modificado |
| `frontend/src/constants/enlacesNav.js` | **nuevo** |
| `frontend/src/pages/Panel.jsx` | modificado |
| `frontend/src/pages/Tienda.jsx` | modificado |
| `frontend/src/index.css` | modificado |
| `backend/package.json` | modificado |
| `README.md` | modificado |
| `.gitignore` | modificado |

No se tocó ningún otro archivo del proyecto (rutas del backend, modelos,
controladores, `App.jsx`, `AuthProvider`, etc. quedan exactamente igual).
