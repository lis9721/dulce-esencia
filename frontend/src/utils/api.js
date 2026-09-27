const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

/* ============================================================================
 * Conexión con el backend FastAPI (Python) — backend/app/*
 * ============================================================================
 * Este archivo hablaba con un backend Node (JWT en cookie httpOnly,
 * `credentials: "include"`, errores en `datos.error`, bodies en camelCase).
 * El backend real es FastAPI, que invierte varias de esas decisiones a
 * propósito (ver app/auth.py, app/routes/usuarios.py):
 *
 *   1. El JWT NO viaja en una cookie httpOnly: viaja en el body de la
 *      respuesta del login (`access_token`). Se guarda en `localStorage`
 *      y se reenvía a mano en cada petición como
 *      "Authorization: Bearer <token>".
 *   2. El login vive en /auth/login (no /usuarios/login).
 *   3. Los errores llegan como {"detail": "..."} (string) o, en una
 *      validación 422 de Pydantic, {"detail": [{"msg": ..., "loc": ...}]}
 *      (arreglo) — nunca como {"error": "..."}.
 *   4. Los endpoints reales del carrito viven bajo /carrito/items/...
 *      (no /carrito/...) y cambiar el estado de un usuario o un pedido
 *      es PATCH, no PUT.
 *   5. TODOS los bodies del backend están en snake_case
 *      (tipo_documento, numero_documento, peso_g, direccion_envio,
 *      password_nueva, ...) mientras que cada página de este frontend
 *      sigue arma/lee los datos en camelCase (tipoDocumento, pesoG,
 *      etc.), que es la convención con la que está escrito todo el
 *      resto de la app. En vez de reescribir cada página, este archivo
 *      hace la traducción de forma automática: cualquier objeto que se
 *      mande como body se convierte a snake_case antes de salir, y
 *      cualquier respuesta JSON se convierte a camelCase antes de
 *      devolverse — así el resto del frontend no se entera del cambio.
 * ==========================================================================*/

const CLAVE_TOKEN = "essentia_token";

/** Lee el JWT guardado (o `null` si no hay sesión). */
function obtenerToken() {
  return localStorage.getItem(CLAVE_TOKEN);
}

/** Guarda el JWT tras un login exitoso. */
function guardarToken(token) {
  localStorage.setItem(CLAVE_TOKEN, token);
}

/** Olvida el JWT (logout, o token rechazado por el backend). */
function borrarToken() {
  localStorage.removeItem(CLAVE_TOKEN);
}

/* --------------------- camelCase <-> snake_case automático --------------------- */

function esObjetoPlano(valor) {
  return (
    valor !== null &&
    typeof valor === "object" &&
    !Array.isArray(valor) &&
    !(valor instanceof File) &&
    !(valor instanceof Blob) &&
    !(valor instanceof Date)
  );
}

function snakeACamel(clave) {
  return clave.replace(/_([a-z0-9])/g, (_, letra) => letra.toUpperCase());
}

function camelASnake(clave) {
  return clave.replace(/[A-Z]/g, (letra) => `_${letra.toLowerCase()}`);
}

/** Recorre objetos/arreglos anidados renombrando cada clave con `convertidor`. Los valores (strings, números, fechas) nunca se tocan, solo los nombres de campo. */
function convertirClaves(valor, convertidor) {
  if (Array.isArray(valor)) return valor.map((item) => convertirClaves(item, convertidor));
  if (esObjetoPlano(valor)) {
    return Object.fromEntries(
      Object.entries(valor).map(([clave, val]) => [convertidor(clave), convertirClaves(val, convertidor)])
    );
  }
  return valor;
}

const aSnakeProfundo = (valor) => convertirClaves(valor, camelASnake);
const aCamelProfundo = (valor) => convertirClaves(valor, snakeACamel);

/**
 * FastAPI responde errores como {"detail": "..."} (string) o, en una
 * validación 422 de Pydantic, {"detail": [{"msg": "...", "loc": [...]}, ...]}
 * (arreglo). Este helper entiende ambas formas para poder mostrar un
 * mensaje legible en los formularios.
 */
function extraerMensajeError(datos) {
  const { detail, error } = datos || {};
  // El módulo de pagos responde { success: false, error: { code, message } }.
  if (error && typeof error.message === "string" && error.message) return error.message;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join(" ");
  }
  return "Ocurrió un error inesperado. Intenta de nuevo.";
}

/**
 * Pequeño helper sobre fetch para hablar con el backend.
 *
 * `opciones.datos`, si viene, es un objeto JS en camelCase: se
 * convierte a snake_case y se manda como body JSON. Si en cambio ya
 * viene `opciones.body` armado a mano (ej. FormData), se respeta tal
 * cual. La respuesta exitosa se convierte de snake_case a camelCase
 * antes de devolverse.
 *
 * Lanza un Error con el mensaje que venga del backend si la
 * respuesta no es exitosa, para poder mostrarlo en los formularios.
 */
async function apiRequest(ruta, opciones = {}) {
  const { datos, headers, ...resto } = opciones;
  const token = obtenerToken();

  const respuesta = await fetch(`${API_URL}${ruta}`, {
    ...resto,
    body: datos !== undefined ? JSON.stringify(aSnakeProfundo(datos)) : opciones.body,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  const crudo = await respuesta.json().catch(() => ({}));

  if (respuesta.status === 401) {
    // El token ya no es válido (expiró, se cerró sesión en otra
    // pestaña, el backend lo rechazó, etc.): se olvida localmente y se
    // avisa a AuthProvider para que actualice el estado de inmediato,
    // no solo la próxima vez que se recargue la página.
    borrarToken();
    window.dispatchEvent(new Event("essentia:token-invalido"));
  }

  if (!respuesta.ok) {
    const error = new Error(extraerMensajeError(crudo));
    // Se adjunta el status HTTP para que quien llama pueda distinguir,
    // por ejemplo, "credenciales incorrectas" (401) de "correo sin
    // verificar" (403) y reaccionar distinto en cada caso (ver Login.jsx).
    error.status = respuesta.status;
    Object.assign(error, aCamelProfundo(crudo));
    throw error;
  }

  return aCamelProfundo(crudo);
}

/* ---------------------------- Usuarios / Auth --------------------------- */

export function registrarUsuario(datos) {
  return apiRequest("/usuarios/registro", { method: "POST", datos });
}

/** Segundo paso del registro: confirma el código OTP de 6 dígitos enviado por correo. */
export function verificarCorreo(datos) {
  return apiRequest("/usuarios/verificar-correo", { method: "POST", datos });
}

/** Pide un nuevo código de verificación (si el original expiró, se perdió o se agotaron los intentos). */
export function reenviarVerificacion(datos) {
  return apiRequest("/usuarios/reenviar-verificacion", { method: "POST", datos });
}

/**
 * Login: el backend Python lo monta en /auth/login (no /usuarios/login)
 * y devuelve { access_token, token_type, usuario } en vez de dejar una
 * cookie httpOnly — el token se guarda a mano para que las siguientes
 * peticiones lo reenvíen como Bearer.
 */
export async function iniciarSesion(datos) {
  const respuesta = await apiRequest("/auth/login", { method: "POST", datos });
  guardarToken(respuesta.accessToken);
  return respuesta;
}

/**
 * "Cierra sesión": con Bearer no hay cookie que el backend pueda
 * borrar ni un endpoint de logout server-side para un JWT sin estado
 * como este (no existe POST /usuarios/logout en el backend Python) —
 * "cerrar sesión" es simplemente olvidar el token en el cliente.
 */
export async function cerrarSesion() {
  borrarToken();
}

/** Paso 1 de "olvidé mi contraseña": pide al backend que genere un código OTP y lo envíe por correo. */
export function recuperarPassword(datos) {
  return apiRequest("/usuarios/recuperar", { method: "POST", datos });
}

/**
 * Pide un nuevo código de recuperación (si el original expiró, se
 * perdió o se agotaron los intentos). Es el mismo endpoint que
 * recuperarPassword (POST /usuarios/recuperar es idempotente: siempre
 * genera un código nuevo), expuesto con otro nombre para que se lea
 * con claridad desde ResetPassword.jsx, donde el correo ya se conoce
 * y lo que se pide es "reenviar", no "iniciar" la recuperación.
 */
export function reenviarCodigoRecuperacion(datos) {
  return recuperarPassword(datos);
}

/** Paso 2 de "olvidé mi contraseña": envía el código OTP recibido por correo junto con la nueva contraseña. */
export function restablecerPassword(datos) {
  return apiRequest("/usuarios/restablecer", { method: "POST", datos });
}

export function obtenerPerfil() {
  return apiRequest("/usuarios/perfil");
}

export function actualizarPerfil(datos) {
  return apiRequest("/usuarios/perfil", { method: "PUT", datos });
}

export function cambiarPassword(datos) {
  return apiRequest("/usuarios/perfil/password", { method: "PUT", datos });
}

/**
 * Solo admin/empleado: lista los usuarios registrados, paginados.
 * Devuelve { datos: Usuario[], paginacion: { pagina, limite, total, totalPaginas } }.
 */
export function listarUsuarios({ pagina = 1, limite = 10 } = {}) {
  return apiRequest(`/usuarios?page=${pagina}&limit=${limite}`);
}

/** Solo admin: cambia el rol de un usuario (cliente/empleado/admin). */
export function cambiarRolUsuario(id, rol) {
  return apiRequest(`/usuarios/${id}/rol`, { method: "PUT", datos: { rol } });
}

/**
 * Solo admin: activa o desactiva un usuario (en vez de eliminarlo),
 * para conservar su historial. `activo` es un booleano. El backend
 * Python expone esto como PATCH (actualización parcial de un solo
 * campo), no PUT.
 */
export function cambiarEstadoUsuario(id, activo) {
  return apiRequest(`/usuarios/${id}/estado`, { method: "PATCH", datos: { activo } });
}

/** Solo admin: elimina un usuario. */
export function eliminarUsuario(id) {
  return apiRequest(`/usuarios/${id}`, { method: "DELETE" });
}

/**
 * Solo admin: crea un usuario directamente desde el panel (a diferencia
 * de `registrarUsuario`, que es pública y siempre crea un `cliente`).
 * `datos` debe incluir el mismo shape que el registro público, más `rol`.
 */
export function crearUsuario(datos) {
  return apiRequest("/usuarios", { method: "POST", datos });
}

/* -------------------------------- Productos ------------------------------ */

/**
 * Lista el catálogo, paginado. `familia` y `orden` son opcionales:
 * - familia: uno de los valores de constants/familiasProducto.js
 * - orden: "precio_asc" | "precio_desc"
 */
export function listarProductos({ pagina = 1, limite = 10, familia, orden } = {}) {
  const params = new URLSearchParams({ page: pagina, limit: limite });
  if (familia) params.set("familia", familia);
  if (orden) params.set("orden", orden);
  return apiRequest(`/productos?${params.toString()}`);
}

export function obtenerProducto(id) {
  return apiRequest(`/productos/${id}`);
}

/**
 * Admin/empleado: lista TODO el catálogo (activos e inactivos) para
 * GestionProductos.jsx. A diferencia de `listarProductos` (pública,
 * solo activos), esta usa /productos/admin/todos — sin ella el panel
 * no puede ver ni reactivar un producto que ya fue desactivado.
 */
export function listarProductosAdmin({ pagina = 1, limite = 10 } = {}) {
  const params = new URLSearchParams({ page: pagina, limit: limite });
  return apiRequest(`/productos/admin/todos?${params.toString()}`);
}

/**
 * Admin/empleado: sube el archivo de imagen de un producto y devuelve
 * la ruta pública (`rutaImagen`) ya lista para guardar como el campo
 * `imagen` del producto. A diferencia de `apiRequest`, NO fija
 * `Content-Type` a mano: FormData necesita que el navegador ponga su
 * propio boundary multipart, algo que un header manual rompería. Sí
 * manda el token Bearer, porque esta ruta está protegida.
 */
export async function subirImagenProducto(archivo) {
  const formData = new FormData();
  formData.append("imagen", archivo);
  const token = obtenerToken();

  const respuesta = await fetch(`${API_URL}/productos/imagen`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  const datos = await respuesta.json().catch(() => ({}));

  if (!respuesta.ok) {
    throw new Error(extraerMensajeError(datos));
  }

  return aCamelProfundo(datos);
}

/** Admin/empleado: sube una imagen de servicio. */
export async function subirImagenServicio(archivo) {
  const formData = new FormData();
  formData.append("imagen", archivo);
  const token = obtenerToken();

  const respuesta = await fetch(`${API_URL}/servicios/imagen`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  const datos = await respuesta.json().catch(() => ({}));

  if (!respuesta.ok) {
    throw new Error(extraerMensajeError(datos));
  }

  return aCamelProfundo(datos);
}

/** Admin/empleado: crea un producto. */
export function crearProducto(datos) {
  return apiRequest("/productos", { method: "POST", datos });
}

/** Admin/empleado: edita un producto (reemplazo completo de los campos editables). */
export function actualizarProducto(id, datos) {
  return apiRequest(`/productos/${id}`, { method: "PUT", datos });
}

/** Solo admin: elimina un producto. */
export function eliminarProducto(id) {
  return apiRequest(`/productos/${id}`, { method: "DELETE" });
}

/* -------------------------------- Proveedores ----------------------------- */

/**
 * Admin/empleado: lista proveedores, paginado y con los filtros del
 * panel (categoria, estado, ciudad, buscar, diasCreditoMaximo). Solo se
 * agregan a la query string los que vengan definidos.
 */
export function listarProveedores({
  pagina = 1,
  limite = 10,
  categoria,
  estado,
  ciudad,
  buscar,
  diasCreditoMaximo,
} = {}) {
  const params = new URLSearchParams({ page: pagina, limit: limite });
  if (categoria) params.set("categoria", categoria);
  if (estado) params.set("estado", estado);
  if (ciudad) params.set("ciudad", ciudad);
  if (buscar) params.set("buscar", buscar);
  if (diasCreditoMaximo !== undefined && diasCreditoMaximo !== "") {
    params.set("dias_credito_maximo", diasCreditoMaximo);
  }
  return apiRequest(`/proveedores?${params.toString()}`);
}

export function obtenerProveedor(id) {
  return apiRequest(`/proveedores/${id}`);
}

/** Admin/empleado: crea un proveedor. */
export function crearProveedor(datos) {
  return apiRequest("/proveedores", { method: "POST", datos });
}

/** Admin/empleado: reemplaza por completo un proveedor (PUT). */
export function actualizarProveedor(id, datos) {
  return apiRequest(`/proveedores/${id}`, { method: "PUT", datos });
}

/** Solo admin: elimina un proveedor (falla con 409 si todavía surte productos). */
export function eliminarProveedor(id) {
  return apiRequest(`/proveedores/${id}`, { method: "DELETE" });
}

/** Admin/empleado: suspende un proveedor y retira su catálogo de la tienda. */
export function suspenderProveedor(id, motivo) {
  return apiRequest(`/proveedores/${id}/suspensiones`, { method: "POST", datos: { motivo } });
}

/** Admin/empleado: reactiva un proveedor suspendido. */
export function reactivarProveedor(id) {
  return apiRequest(`/proveedores/${id}/reactivaciones`, { method: "POST", datos: {} });
}

/* -------------------------------- Servicios ------------------------------ */

/** Lista los servicios del catálogo, paginados. */
export function listarServicios({ pagina = 1, limite = 10 } = {}) {
  return apiRequest(`/servicios?page=${pagina}&limit=${limite}`);
}

export function obtenerServicio(id) {
  return apiRequest(`/servicios/${id}`);
}

/** Admin/empleado: lista TODOS los servicios (activos e inactivos) para GestionServicios.jsx. */
export function listarServiciosAdmin({ pagina = 1, limite = 10 } = {}) {
  return apiRequest(`/servicios/admin/todos?page=${pagina}&limit=${limite}`);
}

/** Admin/empleado: crea un servicio. */
export function crearServicio(datos) {
  return apiRequest("/servicios", { method: "POST", datos });
}

/** Admin/empleado: edita un servicio. */
export function actualizarServicio(id, datos) {
  return apiRequest(`/servicios/${id}`, { method: "PUT", datos });
}

/** Solo admin: elimina un servicio. */
export function eliminarServicio(id) {
  return apiRequest(`/servicios/${id}`, { method: "DELETE" });
}

/* -------------------------------- Carrito --------------------------------- */

/**
 * El backend Python devuelve cada ítem con `stock_disponible` (no
 * `stock`), que es el nombre que usan Carrito.jsx/Checkout.jsx y el
 * carrito de invitado en localStorage. Se renombra acá, en un solo
 * lugar, para que el resto del frontend no tenga que distinguir entre
 * "carrito real" y "carrito de invitado".
 */
function normalizarCarrito(carrito) {
  return {
    ...carrito,
    items: (carrito.items || []).map(({ stockDisponible, ...item }) => ({
      ...item,
      stock: stockDisponible,
    })),
  };
}

/**
 * Devuelve { items: [...], total } del carrito del usuario autenticado.
 * Cada item trae productoId, cantidad, título, imagen, precio ACTUAL,
 * stock y subtotal ya calculado por el backend.
 */
export async function obtenerCarrito() {
  return normalizarCarrito(await apiRequest("/carrito"));
}

/** Agrega un producto al carrito (o suma cantidad si ya estaba). */
export async function agregarAlCarrito(productoId, cantidad = 1) {
  return normalizarCarrito(
    await apiRequest("/carrito/items", { method: "POST", datos: { productoId, cantidad } })
  );
}

/** Reemplaza la cantidad de un producto ya presente en el carrito. */
export async function actualizarCantidadCarrito(productoId, cantidad) {
  return normalizarCarrito(
    await apiRequest(`/carrito/items/${productoId}`, { method: "PUT", datos: { cantidad } })
  );
}

/** Quita un solo producto del carrito. */
export async function quitarDelCarrito(productoId) {
  return normalizarCarrito(await apiRequest(`/carrito/items/${productoId}`, { method: "DELETE" }));
}

/** Vacía el carrito completo. */
export async function vaciarCarrito() {
  return normalizarCarrito(await apiRequest("/carrito", { method: "DELETE" }));
}

/**
 * Fusiona el carrito de invitado (guardado en localStorage antes de
 * iniciar sesión) con el que el usuario ya tuviera en la BD.
 * `items` es un arreglo de { productoId, cantidad }.
 */
export async function fusionarCarrito(items) {
  return normalizarCarrito(await apiRequest("/carrito/fusionar", { method: "POST", datos: { items } }));
}

/* -------------------------------- Contacto -------------------------------- */

export function enviarMensajeContacto(datos) {
  return apiRequest("/contacto", { method: "POST", datos });
}

/* -------------------------------- Pedidos --------------------------------- */

/**
 * Checkout: crea el pedido a partir del carrito actual.
 * `idempotencyKey` no viaja como header (el backend Python la lee del
 * BODY, campo `idempotency_key` — ver schemas/pedido.py): Checkout.jsx
 * genera uno solo una vez por visita a /checkout y lo reenvía en cada
 * intento, para que un doble clic o un reintento de red nunca cree un
 * pedido duplicado.
 */
export function crearPedido(datos, idempotencyKey) {
  return apiRequest("/pedidos", {
    method: "POST",
    datos: idempotencyKey ? { ...datos, idempotencyKey } : datos,
  });
}

/**
 * Lista pedidos paginados. Un cliente ve solo los propios; admin/empleado
 * ven los de todos.
 * Devuelve { datos: [...], paginacion: { pagina, limite, total, totalPaginas } }.
 */
export function listarPedidos({ pagina = 1, limite = 10 } = {}) {
  return apiRequest(`/pedidos?page=${pagina}&limit=${limite}`);
}

/** Detalle completo (cabecera + items) de un pedido propio, o cualquiera si es admin/empleado. */
export function obtenerPedido(id) {
  return apiRequest(`/pedidos/${id}`);
}

/** Solo admin/empleado: cambia el estado de un pedido (PATCH: actualización parcial). */
export function cambiarEstadoPedido(id, estado) {
  return apiRequest(`/pedidos/${id}/estado`, { method: "PATCH", datos: { estado } });
}

/**
 * Descarga el PDF de la factura de un pedido y dispara la descarga en
 * el navegador.
 *
 * NOTA: esta ruta (`GET /api/pedidos/{id}/factura`) todavía no existe
 * en el backend Python (backend/app/routes/pedidos.py) — el botón que
 * usa esta función devolverá 404 hasta que se agregue del lado del
 * servidor. Se deja aquí ya adaptada a Bearer (en vez de la cookie
 * httpOnly de Node) para que funcione sin más cambios en cuanto la
 * ruta exista.
 */
export async function descargarFacturaPedido(id) {
  const token = obtenerToken();

  const respuesta = await fetch(`${API_URL}/pedidos/${id}/factura`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (respuesta.status === 401) {
    borrarToken();
    window.dispatchEvent(new Event("essentia:token-invalido"));
  }

  if (!respuesta.ok) {
    const datos = await respuesta.json().catch(() => ({}));
    throw new Error(extraerMensajeError(datos));
  }

  const disposicion = respuesta.headers.get("Content-Disposition") || "";
  const coincidencia = disposicion.match(/filename="?([^"]+)"?/);
  const nombreArchivo = coincidencia ? coincidencia[1] : `factura-pedido-${id}.pdf`;

  const blob = await respuesta.blob();
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombreArchivo;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* -------------------------------- Cupones --------------------------------- */

/**
 * Valida un código de cupón contra el subtotal ACTUAL del carrito. Es
 * solo un preview: no gasta un uso del cupón — eso solo ocurre cuando
 * el pedido se confirma de verdad (crearPedido, enviando cuponCodigo).
 * Devuelve { valido: true, codigo, descuento } o lanza un Error (400)
 * con el motivo si no aplica.
 */
export function validarCupon(codigo, subtotal) {
  return apiRequest("/cupones/validar", { method: "POST", datos: { codigo, subtotal } });
}

/** Solo admin/empleado: lista todos los cupones (activos e inactivos), paginados. */
export function listarCupones({ pagina = 1, limite = 10 } = {}) {
  return apiRequest(`/cupones?page=${pagina}&limit=${limite}`);
}

/** Solo admin: crea un cupón. */
export function crearCupon(datos) {
  return apiRequest("/cupones", { method: "POST", datos });
}

/** Solo admin: edita un cupón existente. */
export function actualizarCupon(id, datos) {
  return apiRequest(`/cupones/${id}`, { method: "PUT", datos });
}

/** Solo admin: elimina un cupón. */
export function eliminarCupon(id) {
  return apiRequest(`/cupones/${id}`, { method: "DELETE" });
}

/* ---------------------------------- Ventas --------------------------------- */
/* Quinto Avance: módulo de gestión comercial (ver backend/app/routes/ventas.py). */

/** Solo admin/empleado: registra una venta directa de punto de venta (productos y/o servicios). */
export function registrarVenta(datos) {
  return apiRequest("/ventas", { method: "POST", datos });
}

/** Solo admin/empleado: genera (o recupera) la venta correspondiente a un pedido ya pagado del sitio web. */
export function generarVentaDesdePedido(pedidoId) {
  return apiRequest(`/ventas/desde-pedido/${pedidoId}`, { method: "POST" });
}

/**
 * Historial de ventas paginado y filtrable. Un cliente solo ve las
 * suyas; admin/empleado ven todas. `filtros` puede incluir
 * fechaInicio, fechaFin, clienteId, productoId, servicioId, estado.
 */
export function listarVentas({ pagina = 1, limite = 10, ...filtros } = {}) {
  const params = new URLSearchParams({ page: pagina, limit: limite });
  Object.entries(filtros).forEach(([clave, valor]) => {
    if (valor !== undefined && valor !== null && valor !== "") params.set(camelASnakeParam(clave), valor);
  });
  return apiRequest(`/ventas?${params.toString()}`);
}

export function obtenerVenta(id) {
  return apiRequest(`/ventas/${id}`);
}

/** Solo admin/empleado: cambia el estado de una venta (completada/anulada). */
export function cambiarEstadoVenta(id, estado) {
  return apiRequest(`/ventas/${id}/estado`, { method: "PATCH", datos: { estado } });
}

/* -------------------------------- Facturas --------------------------------- */

/** Solo admin/empleado: genera la factura de una venta ya registrada. */
export function generarFactura(ventaId) {
  return apiRequest("/facturas", { method: "POST", datos: { ventaId } });
}

export function listarFacturas({ pagina = 1, limite = 10, ...filtros } = {}) {
  const params = new URLSearchParams({ page: pagina, limit: limite });
  Object.entries(filtros).forEach(([clave, valor]) => {
    if (valor !== undefined && valor !== null && valor !== "") params.set(camelASnakeParam(clave), valor);
  });
  return apiRequest(`/facturas?${params.toString()}`);
}

export function obtenerFactura(id) {
  return apiRequest(`/facturas/${id}`);
}

/** Descarga el PDF de una factura de venta y dispara la descarga en el navegador. */
export async function descargarFacturaVenta(id, numero) {
  await descargarArchivo(`/facturas/${id}/pdf`, numero ? `${numero}.pdf` : `factura-${id}.pdf`);
}

/* -------------------------------- Reportes ---------------------------------- */
/* Solo admin/empleado. Requerimientos 4-6 del quinto avance. */

/** Reporte diario de ventas en JSON, para mostrarlo dentro del panel. `fecha` en formato YYYY-MM-DD. */
export function obtenerReporteDiario(fecha) {
  const params = fecha ? `?fecha=${fecha}` : "";
  return apiRequest(`/reportes/ventas/diario${params}`);
}

/** Descarga el reporte diario de ventas en PDF. */
export async function descargarReporteDiarioPdf(fecha) {
  await descargarArchivo(`/reportes/ventas/diario/pdf?fecha=${fecha}`, `reporte-ventas-${fecha}.pdf`);
}

/** Descarga el reporte diario de ventas en Excel (.xlsx). */
export async function descargarReporteDiarioExcel(fecha) {
  await descargarArchivo(`/reportes/ventas/diario/excel?fecha=${fecha}`, `reporte-ventas-${fecha}.xlsx`);
}

/* ------------------------------ Estadísticas / Dashboards -------------------------------- */

/** Solo admin: totales para las cards del dashboard administrativo. */
export function obtenerEstadisticasAdmin() {
  return apiRequest("/estadisticas/admin");
}

/**
 * Solo admin/empleado: serie de ventas agrupada por día/semana/mes
 * para los gráficos del dashboard de ventas, con los mismos filtros
 * que el historial.
 */
export function obtenerEstadisticasVentas({ agrupacion = "dia", ...filtros } = {}) {
  const params = new URLSearchParams({ agrupacion });
  Object.entries(filtros).forEach(([clave, valor]) => {
    if (valor !== undefined && valor !== null && valor !== "") params.set(camelASnakeParam(clave), valor);
  });
  return apiRequest(`/estadisticas/ventas?${params.toString()}`);
}

/* ----------------------------------- PQR ------------------------------------- */

/** Cualquier usuario autenticado: registra una PQR propia. */
export function crearPQR(datos) {
  return apiRequest("/pqr", { method: "POST", datos });
}

/** Un cliente ve solo las suyas; admin/empleado ven todas (con filtro opcional por estado). */
export function listarPQR({ pagina = 1, limite = 10, estado } = {}) {
  const params = new URLSearchParams({ page: pagina, limit: limite });
  if (estado) params.set("estado", estado);
  return apiRequest(`/pqr?${params.toString()}`);
}

export function obtenerPQR(id) {
  return apiRequest(`/pqr/${id}`);
}

/** Solo admin/empleado: cambia el estado y/o agrega la respuesta de una PQR. */
export function gestionarPQR(id, datos) {
  return apiRequest(`/pqr/${id}`, { method: "PATCH", datos });
}

/* --------------------------------- Chatbot ------------------------------------ */

/**
 * Envía un mensaje al chatbot con IA. Ruta pública: funciona con o
 * sin sesión iniciada (ver backend/app/routes/chatbot.py). `sesionId`
 * solo aplica para visitantes sin cuenta, para mantener el mismo hilo
 * de conversación entre mensajes.
 */
export function enviarMensajeChatbot({ mensaje, conversacionId, sesionId }) {
  return apiRequest("/chatbot/mensaje", {
    method: "POST",
    datos: { mensaje, conversacionId, sesionId },
  });
}

export function obtenerConversacionChatbot(id) {
  return apiRequest(`/chatbot/conversaciones/${id}`);
}

/* ------------------------------ Helpers internos de este archivo -------------------------------- */

/** camelCase de un solo nombre de parámetro de query (no de un objeto anidado) -> snake_case. */
function camelASnakeParam(clave) {
  return clave.replace(/[A-Z]/g, (letra) => `_${letra.toLowerCase()}`);
}

/** Descarga genérica de un archivo binario (PDF/Excel) protegido por Bearer, con el nombre sugerido por el backend o `nombrePorDefecto`. */
async function descargarArchivo(ruta, nombrePorDefecto) {
  const token = obtenerToken();

  const respuesta = await fetch(`${API_URL}${ruta}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (respuesta.status === 401) {
    borrarToken();
    window.dispatchEvent(new Event("essentia:token-invalido"));
  }

  if (!respuesta.ok) {
    const datos = await respuesta.json().catch(() => ({}));
    throw new Error(extraerMensajeError(datos));
  }

  const disposicion = respuesta.headers.get("Content-Disposition") || "";
  const coincidencia = disposicion.match(/filename="?([^"]+)"?/);
  const nombreArchivo = coincidencia ? coincidencia[1] : nombrePorDefecto;

  const blob = await respuesta.blob();
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombreArchivo;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default apiRequest;


/* ------------------------------ Pagos (Wompi) ---------------------------- */

/**
 * Crea el pago de un pedido y devuelve { paymentId, reference, checkoutUrl }.
 * El navegador debe redirigir a `checkoutUrl` (Web Checkout de Wompi, donde
 * el cliente escribe los datos de su tarjeta: NUNCA pasan por nuestros
 * servidores). El backend valida que `monto` sea igual al total del pedido.
 * `idempotencyKey` evita crear dos pagos si el usuario hace doble clic.
 */
export function crearPago(datos, idempotencyKey) {
  return apiRequest("/pagos", {
    method: "POST",
    datos,
    headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {},
  });
}

/** Consulta un pago propio por la referencia que va en la URL de retorno. */
export function obtenerPagoPorReferencia(referencia) {
  return apiRequest(`/pagos/referencia/${encodeURIComponent(referencia)}`);
}

/**
 * Pide al backend que confirme el estado con Wompi. `transactionId` es el
 * `?id=` que Wompi agrega a la URL de retorno; el servidor lo verifica antes
 * de usarlo (funciona aunque el webhook aún no haya llegado).
 */
export function sincronizarPago(pagoId, transactionId) {
  const consulta = transactionId ? `?transaction_id=${encodeURIComponent(transactionId)}` : "";
  return apiRequest(`/pagos/${pagoId}/sync${consulta}`, { method: "POST" });
}
