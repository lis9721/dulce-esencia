/**
 * Formato de moneda usado en toda la app para mostrar `productos.precio`
 * (guardado como número/COP sin decimales de más). Centralizado acá para
 * que el carrusel, el panel y cualquier tarjeta de producto futura
 * (catálogo, carrito, checkout) muestren el precio siempre igual.
 */
const formateadorCOP = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

/**
 * Recibe un precio (número o string numérico, como llega desde la API
 * — mysql2 puede devolver DECIMAL como string) y devuelve el texto
 * formateado, ej. "$ 189.000". Si el valor no es un número válido,
 * devuelve "" en vez de "$ NaN".
 */
/**
 * `productos.imagen` puede traer dos formas distintas:
 *   - Una ruta relativa del backend (ej. "/uploads/productos/abc.jpg"),
 *     generada por la subida real de archivos (ver
 *     GestionProductos.jsx / POST /api/productos/imagen). Esa ruta
 *     vive en el servidor del backend, no en el del frontend, así que
 *     hay que anteponerle el origen del backend o el navegador la
 *     buscaría (mal) en el propio origen del frontend.
 *   - Un nombre suelto escrito a mano (ej. "img1.jpg"), como quedaron
 *     los productos sembrados en schema.sql antes de que existiera la
 *     subida real — esos se dejan tal cual (ver nota en README sobre
 *     el ícono de repuesto cuando el archivo no existe).
 */
export function resolverUrlImagen(ruta) {
  if (!ruta) return ruta;
  if (/^https?:\/\//i.test(ruta)) return ruta;
  // Si es un nombre de archivo suelto de la BD original
  if (!ruta.startsWith("/") && !ruta.startsWith("data:")) {
    return `/uploads/productos/${ruta}`;
  }
  return ruta;
}

export function formatearPrecio(precio) {
  const numero = Number(precio);
  if (Number.isNaN(numero)) return "";
  return formateadorCOP.format(numero);
}

/** Recibe pedidos.creado_en (string DATETIME de MySQL) y devuelve "24 ago 2026, 3:41 p. m.". */
export function formatearFecha(fecha) {
  const valor = new Date(fecha);
  if (Number.isNaN(valor.getTime())) return "";
  return new Intl.DateTimeFormat("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(valor);
}

/**
 * Texto y color para cada valor de pedidos.estado — usado en
 * MisPedidos.jsx, GestionPedidos.jsx y PedidoDetalle.jsx para que la
 * misma "insignia" de estado se vea siempre igual en toda la app.
 */
const ESTADOS_PEDIDO = {
  pendiente: { texto: "Pendiente", color: "#a16207", fondo: "#fef3c7" },
  pagado: { texto: "Pagado", color: "#1d4ed8", fondo: "#dbeafe" },
  enviado: { texto: "Enviado", color: "#7e22ce", fondo: "#f3e8ff" },
  entregado: { texto: "Entregado", color: "#15803d", fondo: "#dcfce7" },
  cancelado: { texto: "Cancelado", color: "#b91c1c", fondo: "#fee2e2" },
};

export function obtenerEstadoPedido(estado) {
  return ESTADOS_PEDIDO[estado] || { texto: estado, color: "#374151", fondo: "#f3f4f6" };
}

/** Mismo criterio de "insignia" que ESTADOS_PEDIDO, para ventas.estado (Quinto Avance). */
const ESTADOS_VENTA = {
  completada: { texto: "Completada", color: "#15803d", fondo: "#dcfce7" },
  anulada: { texto: "Anulada", color: "#b91c1c", fondo: "#fee2e2" },
};

export function obtenerEstadoVenta(estado) {
  return ESTADOS_VENTA[estado] || { texto: estado, color: "#374151", fondo: "#f3f4f6" };
}

/** Para pqr.estado. */
const ESTADOS_PQR = {
  pendiente: { texto: "Pendiente", color: "#a16207", fondo: "#fef3c7" },
  en_proceso: { texto: "En proceso", color: "#1d4ed8", fondo: "#dbeafe" },
  respondida: { texto: "Respondida", color: "#7e22ce", fondo: "#f3e8ff" },
  cerrada: { texto: "Cerrada", color: "#15803d", fondo: "#dcfce7" },
};

export function obtenerEstadoPQR(estado) {
  return ESTADOS_PQR[estado] || { texto: estado, color: "#374151", fondo: "#f3f4f6" };
}

/** Etiqueta legible para pqr.tipo. */
const TIPOS_PQR = {
  peticion: "Petición",
  queja: "Queja",
  reclamo: "Reclamo",
  sugerencia: "Sugerencia",
};

export function obtenerTipoPQR(tipo) {
  return TIPOS_PQR[tipo] || tipo;
}

/** Configuración visual y etiquetas de los métodos de pago. */
export const METODOS_PAGO = {
  tarjeta: {
    nombre: "Tarjeta (Wompi)",
    icono: "💳",
    descripcion: "Tarjeta crédito / débito (Pasarela Wompi)",
    badge: "Wompi Bancolombia",
    badgeClase: "bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-800",
  },
  transferencia: {
    nombre: "Transferencia",
    icono: "🏦",
    descripcion: "Bancolombia, Nequi, Daviplata o PSE",
    badge: "Bancolombia / Nequi",
    badgeClase: "bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-800",
  },
  contraentrega: {
    nombre: "Contraentrega",
    icono: "💵",
    descripcion: "Efectivo o datáfono al recibir",
    badge: "Pago al recibir",
    badgeClase: "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-800",
  },
};

export function obtenerMetodoPago(metodo) {
  return (
    METODOS_PAGO[metodo] || {
      nombre: metodo || "No especificado",
      icono: "🪙",
      descripcion: "",
      badge: metodo || "Otro",
      badgeClase: "bg-slate-100 text-slate-800",
    }
  );
}

