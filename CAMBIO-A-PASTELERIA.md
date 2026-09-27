# Adaptación del proyecto a una pastelería

Este proyecto era la tienda de perfumería **Essentia**. Ahora es **Dulce Esencia
Pastelería** (nombre provisional: se cambia con un reemplazo global de
`Dulce Esencia` y `dulceesencia`).

## Qué cambió en los datos

| Antes (perfumería) | Ahora (pastelería) |
|---|---|
| `FamiliaOlfativa`: florales, amaderadas, cítricas, orientales, acuáticas, especiadas | `FamiliaProducto`: tortas, cupcakes, galletas, postres, hojaldres, panadería |
| `productos.volumen_ml` | `productos.peso_g` (gramos, 1–10 000) |
| Proveedores: fragancias, envases, empaques, insumos, logística | materias primas, lácteos, empaques, insumos, logística |
| 8 perfumes en el seed | 10 productos (mismos ids, precios y stock que el carrusel del home) |
| Sección "Notas olfativas" | Sección "Cómo se arma una torta" (`components/AnatomiaTorta.jsx`) |
| Sección "Colecciones" | "Nuestra vitrina" |
| Chatbot: familias olfativas y perfumes | Chatbot: categorías y productos de pastelería |
| Logo, favicon, og-image, `img1…img10.jpg` | Ilustraciones **provisionales** (ver abajo) |

El campo se sigue llamando `familia` en la API (`?familia=tortas`); en la interfaz
se muestra como "Categoría".

## Cómo aplicarlo en una base de datos existente

Los valores de los ENUM y la columna `peso_g` cambiaron, así que lo más simple es
**recrear la base**: ejecutar `backend/database/schema_fastapi.sql` sobre una base
vacía y luego `python seed.py`.

Usuarios de demo (todos con contraseña `Dulce2026!`):
`admin@dulceesencia.com`, `empleado@dulceesencia.com`, `cliente@dulceesencia.com`.

## Correcciones de errores que ya tenía el proyecto

- Los NIT del seed y de los tests tenían un dígito de verificación DIAN incorrecto
  (15 tests de `test_proveedores.py` fallaban). Ahora son válidos.
- Los correos de demo terminaban en `.test`, dominio que `EmailStr` rechaza, por lo
  que ese login nunca habría funcionado. Ahora usan `@dulceesencia.com`.

## Lo que NO se cambió a propósito (para no romper entornos existentes)

- Nombre de la base de datos (`essentia_db`, `essentia_db_fastapi`).
- Claves de `localStorage`/eventos (`essentia_token`, `essentia-theme`, …).
- Prefijo de la referencia de pago Wompi (`ESSENTIA-YYYYMMDD-XXXXXXXX`).
- Nombres de archivo de las colecciones de Postman y la imagen Docker de ejemplo.

## Pendiente de tu parte

- **Imágenes:** `frontend/src/assets/images/img1…img10.jpg` (carrusel y hero),
  `logo1.webp`, `public/favicon.png` y `public/og-image.jpg` son ilustraciones
  generadas como sustituto. Reemplázalas con fotos reales conservando los nombres.
  Orden: 1 Torta de chocolate · 2 Torta de fresas (hero) · 3 Cupcakes de vainilla ·
  4 Red velvet · 5 Galletas con chips · 6 Macarons · 7 Cheesecake · 8 Croissants ·
  9 Pan de bono · 10 Tres leches.
- Los productos sembrados apuntan a `backend/uploads/productos/*.jpg` (mismas ilustraciones,
  con nombres descriptivos como `torta-chocolate-intenso.jpg`). Reemplaza esos archivos por
  fotos reales o sube nuevas desde el panel de productos.
- Teléfono, dirección, horario y redes sociales son datos de ejemplo.
