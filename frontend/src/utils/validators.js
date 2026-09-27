/**
 * inicio de sesión, recuperación de contraseña y registro.
 * Cada función recibe el valor actual (y opcionalmente todos los
 * valores del formulario) y retorna un mensaje de error o "" si es válido.
 */

const REGEX_SOLO_LETRAS = /^[A-Za-zÁÉÍÓÚÑÜáéíóúñü\s]+$/;
const REGEX_CORREO = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const REGEX_SOLO_NUMEROS = /^[0-9]+$/;

/**
 * Límite máximo de la contraseña, en BYTES (no caracteres) — debe
 * coincidir con backend/utils/validadores.js. El límite técnico real
 * de bcrypt es 72 bytes (ver esa constante en el backend para el
 * detalle), pero acá se usa un tope más tradicional para el contador
 * visible del formulario. Sigue estando muy por encima del mínimo (8),
 * así que no restringe passphrases razonablemente largas.
 * Se mide en bytes UTF-8, no con .length, porque un emoji o una letra
 * con tilde puede ocupar más de 1 byte.
 */
const MAX_BYTES_PASSWORD = 32;

function bytesUtf8(valor) {
  return new TextEncoder().encode(valor).length;
}

function mensajeLargoPassword() {
  return `La contraseña es demasiado larga (máximo ${MAX_BYTES_PASSWORD} caracteres aproximadamente).`;
}

/**
 * Valida un nombre con un largo máximo configurable, para poder
 * reutilizar la misma regla de "solo letras y espacios" en columnas
 * de distinto tamaño (usuarios.nombre es VARCHAR(40), mientras que
 * mensajes_contacto.nombre es VARCHAR(60)).
 */
function validarNombreConLargoMaximo(value, largoMaximo) {
  const valor = (value || "").trim();
  if (!valor) return "Este campo es obligatorio.";
  if (valor.length < 2) return "Debe tener al menos 2 caracteres.";
  if (valor.length > largoMaximo) return `Debe tener máximo ${largoMaximo} caracteres.`;
  if (!REGEX_SOLO_LETRAS.test(valor)) return "Solo se permiten letras y espacios.";
  return "";
}

/**
 * Nombre/apellido de usuarios. La columna (usuarios.nombre /
 * usuarios.apellido) es VARCHAR(40), pero 30 ya cubre con margen
 * cualquier nombre real; un tope más chico que la columna es una
 * restricción de UX, no una limitación técnica.
 */
export function validarNombre(value) {
  return validarNombreConLargoMaximo(value, 30);
}

/** Nombre del formulario de contacto (mensajes_contacto.nombre es VARCHAR(60), acotado a 40 por UX). */
export function validarNombreContacto(value) {
  return validarNombreConLargoMaximo(value, 40);
}

export function validarCorreo(value) {
  const valor = (value || "").trim();
  if (!valor) return "El correo electrónico es obligatorio.";
  if (valor.length > 60) return "Debe tener máximo 60 caracteres.";
  if (!REGEX_CORREO.test(valor)) return "Ingresa un correo electrónico válido.";
  return "";
}

export function validarTelefono(value) {
  const valor = (value || "").trim();
  if (!valor) return "El teléfono es obligatorio.";
  if (!REGEX_SOLO_NUMEROS.test(valor)) return "El teléfono solo debe contener números.";
  if (valor.length < 7 || valor.length > 15) return "Debe tener entre 7 y 15 dígitos.";
  return "";
}

export function validarDocumento(value) {
  const valor = (value || "").trim();
  if (!valor) return "El número de documento es obligatorio.";
  if (!REGEX_SOLO_NUMEROS.test(valor)) return "El documento solo debe contener números.";
  if (valor.length < 5 || valor.length > 15) return "Debe tener entre 5 y 15 dígitos.";
  return "";
}

export function validarDireccion(value) {
  const valor = (value || "").trim();
  if (!valor) return "La dirección es obligatoria.";
  if (valor.length < 5) return "Debe tener al menos 5 caracteres.";
  if (valor.length > 80) return "Debe tener máximo 80 caracteres.";
  return "";
}

export function validarSeleccion(value) {
  if (!value) return "Selecciona una opción.";
  return "";
}

/**
 * Dirección de envío del checkout (pedidos.direccion_envio es
 * VARCHAR(150) — más larga que usuarios.direccion, VARCHAR(100),
 * porque acá puede incluir referencias de entrega). Debe coincidir con
 * backend/utils/validadores.js#validarDireccionEnvio.
 */
export function validarDireccionEnvio(value) {
  const valor = (value || "").trim();
  if (!valor) return "La dirección de envío es obligatoria.";
  if (valor.length < 5) return "Debe tener al menos 5 caracteres.";
  if (valor.length > 120) return "Debe tener máximo 120 caracteres.";
  return "";
}

/**
 * Validación completa de contraseña, usada en el formulario de
 * registro. NO prohíbe espacios: una passphrase con espacios
 * ("correcto caballo bateria grapa") es una contraseña válida y más
 * fácil de recordar que una "compleja" de 8 caracteres.
 */
export function validarPassword(value) {
  const valor = value || "";
  if (!valor) return "La contraseña es obligatoria.";
  if (valor.length < 8) return "Debe tener al menos 8 caracteres.";
  if (bytesUtf8(valor) > MAX_BYTES_PASSWORD) return mensajeLargoPassword();
  if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])/.test(valor)) {
    return "Debe incluir una mayúscula, una minúscula y un número.";
  }
  return "";
}

/** Validación simple de contraseña, usada en el formulario de inicio de sesión. */
export function validarPasswordLogin(value) {
  const valor = value || "";
  if (!valor) return "La contraseña es obligatoria.";
  if (valor.length < 8) return "Debe tener al menos 8 caracteres.";
  if (bytesUtf8(valor) > MAX_BYTES_PASSWORD) return mensajeLargoPassword();
  return "";
}

export function validarConfirmarPassword(value, valores) {
  const valor = value || "";
  if (!valor) return "Confirma tu contraseña.";
  if (valor !== valores.password) return "Las contraseñas no coinciden.";
  return "";
}

const REGEX_CODIGO_OTP = /^\d{6}$/;

/**
 * Código OTP de 6 dígitos enviado por correo (verificación de cuenta
 * y recuperación de contraseña). Debe coincidir con
 * backend/app/schemas/auth.py#REGEX_CODIGO_OTP.
 */
export function validarCodigoOtp(value) {
  const valor = (value || "").trim();
  if (!valor) return "Ingresa el código de 6 dígitos que te enviamos por correo.";
  if (!REGEX_CODIGO_OTP.test(valor)) return "El código debe tener exactamente 6 dígitos numéricos.";
  return "";
}

/* ------------------------- Validadores del panel (CRUD) ------------------------- */

export function validarTitulo(value) {
  const valor = (value || "").trim();
  if (!valor) return "El título es obligatorio.";
  if (valor.length < 3) return "Debe tener al menos 3 caracteres.";
  if (valor.length > 60) return "Debe tener máximo 60 caracteres.";
  return "";
}

export function validarDescripcionProducto(value) {
  const valor = (value || "").trim();
  if (!valor) return "La descripción es obligatoria.";
  if (valor.length < 10) return "Debe tener al menos 10 caracteres.";
  if (valor.length > 180) return "Debe tener máximo 180 caracteres.";
  return "";
}

export function validarImagen(value) {
  const valor = (value || "").trim();
  if (!valor) return "El nombre del archivo de imagen es obligatorio.";
  if (!/\.(jpg|jpeg|png|webp)$/i.test(valor)) {
    return "Debe terminar en .jpg, .jpeg, .png o .webp.";
  }
  return "";
}

export function validarOrden(value) {
  const valor = String(value ?? "").trim();
  if (valor === "") return ""; // opcional, el backend lo pone en 0 por defecto
  if (!/^\d+$/.test(valor)) return "El orden debe ser un número entero.";
  return "";
}

/** Debe coincidir con backend/utils/validadores.js#validarPrecio. */
export function validarPrecio(value) {
  const valor = String(value ?? "").trim();
  if (valor === "") return "El precio es obligatorio.";
  const numero = Number(valor);
  if (Number.isNaN(numero)) return "El precio debe ser un número.";
  if (numero < 0) return "El precio no puede ser negativo.";
  if (numero > 99999999.99) return "El precio es demasiado grande.";
  return "";
}

/** Debe coincidir con backend/utils/validadores.js#validarStock. */
export function validarStock(value) {
  const valor = String(value ?? "").trim();
  if (valor === "") return ""; // opcional, el backend lo pone en 0 por defecto
  if (!/^\d+$/.test(valor)) return "El stock debe ser un número entero no negativo.";
  return "";
}

/** Debe coincidir con backend/utils/validadores.js#validarSku. */
export function validarSku(value) {
  const valor = (value || "").trim();
  if (!valor) return ""; // opcional
  if (valor.length > 20) return "Debe tener máximo 20 caracteres.";
  if (!/^[A-Za-z0-9-_]+$/.test(valor)) {
    return "Solo letras, números, guiones y guiones bajos.";
  }
  return "";
}

/** Debe coincidir con backend/app/schemas/producto.py (categoría = `familia`). */
export function validarFamilia(value) {
  const valor = (value || "").trim();
  if (!valor) return "La categoría es obligatoria.";
  return "";
}

/** Debe coincidir con backend/app/schemas/producto.py#validar_peso_g. */
export function validarPesoG(value) {
  const valor = String(value ?? "").trim();
  if (valor === "") return ""; // opcional
  if (!/^\d+$/.test(valor)) return "Debe ser un número entero de gramos.";
  const numero = Number(valor);
  if (numero < 1) return "Debe ser mayor a 0 g.";
  if (numero > 10000) return "Es demasiado grande para un producto de pastelería (máximo 10000 g).";
  return "";
}

export function validarPasswordNueva(value) {
  return validarPassword(value);
}

/** servicios.nombre es VARCHAR(80), igual que productos.titulo. */
export function validarNombreServicio(value) {
  const valor = (value || "").trim();
  if (!valor) return "El nombre es obligatorio.";
  if (valor.length < 3) return "Debe tener al menos 3 caracteres.";
  if (valor.length > 60) return "Debe tener máximo 60 caracteres.";
  return "";
}

/** Debe coincidir con backend/utils/validadores.js#validarDescripcionServicio. */
export function validarDescripcionServicio(value) {
  const valor = (value || "").trim();
  if (!valor) return "La descripción es obligatoria.";
  if (valor.length < 10) return "Debe tener al menos 10 caracteres.";
  if (valor.length > 180) return "Debe tener máximo 180 caracteres.";
  return "";
}

/**
 * servicios.imagen es opcional (a diferencia de productos.imagen, que
 * es obligatoria) — no todos los servicios tienen una imagen propia.
 */
export function validarImagenServicio(value) {
  const valor = (value || "").trim();
  if (!valor) return ""; // opcional
  if (!/\.(jpg|jpeg|png|webp)$/i.test(valor)) {
    return "Debe terminar en .jpg, .jpeg, .png o .webp.";
  }
  return "";
}

/** Debe coincidir con backend/utils/validadores.js#validarDuracionMinutos. */
export function validarDuracionMinutos(value) {
  const valor = String(value ?? "").trim();
  if (valor === "") return ""; // opcional, NULL = no aplica
  if (!/^\d+$/.test(valor)) return "La duración debe ser un número entero de minutos.";
  if (Number(valor) < 1) return "La duración debe ser de al menos 1 minuto.";
  if (Number(valor) > 1440) return "La duración no puede superar 1440 minutos (24 horas).";
  return "";
}

/** Debe coincidir con backend/utils/validadores.js#validarCodigoServicio. */
export function validarCodigoServicio(value) {
  const valor = (value || "").trim();
  if (!valor) return ""; // opcional
  if (valor.length > 20) return "Debe tener máximo 20 caracteres.";
  if (!/^[A-Za-z0-9-_]+$/.test(valor)) {
    return "Solo letras, números, guiones y guiones bajos.";
  }
  return "";
}

/* -------------------------------- Cupones --------------------------------- */

const REGEX_CODIGO_CUPON = /^[A-Za-z0-9_-]+$/;

/** Debe coincidir con backend/utils/validadores.js#validarCodigoCupon. */
export function validarCodigoCupon(value) {
  const valor = (value || "").trim();
  if (!valor) return "El código del cupón es obligatorio.";
  if (valor.length < 3) return "Debe tener al menos 3 caracteres.";
  if (valor.length > 20) return "Debe tener máximo 20 caracteres.";
  if (!REGEX_CODIGO_CUPON.test(valor)) {
    return "Solo puede contener letras, números, guiones y guiones bajos.";
  }
  return "";
}

const TIPOS_CUPON_VALIDOS = ["porcentaje", "monto_fijo"];

/** Debe coincidir con backend/utils/validadores.js#validarTipoCupon. */
export function validarTipoCupon(value) {
  if (!TIPOS_CUPON_VALIDOS.includes(value)) {
    return "El tipo debe ser porcentaje o monto fijo.";
  }
  return "";
}

/**
 * cupones.valor: el rango válido depende de `tipo` (el otro campo del
 * mismo formulario), por eso recibe también `valores` — igual que
 * useForm ya le pasa (valor, todosLosValores) a cada validador.
 * Debe coincidir con backend/utils/validadores.js#validarValorCupon.
 */
export function validarValorCupon(value, valores) {
  if (value === undefined || value === null || value === "") return "El valor del cupón es obligatorio.";
  const valor = Number(value);
  if (Number.isNaN(valor)) return "El valor debe ser un número.";
  if (valor <= 0) return "El valor debe ser mayor que cero.";
  if (valores?.tipo === "porcentaje" && valor > 100) {
    return "Un cupón de porcentaje no puede superar 100.";
  }
  if (valor > 99999999.99) return "El valor es demasiado grande.";
  return "";
}

/** Debe coincidir con backend/utils/validadores.js#validarMontoMinimoCupon. */
export function validarMontoMinimoCupon(value) {
  const valor = String(value ?? "").trim();
  if (valor === "") return ""; // opcional, el backend lo pone en 0 por defecto
  const numero = Number(valor);
  if (Number.isNaN(numero)) return "El monto mínimo debe ser un número.";
  if (numero < 0) return "El monto mínimo no puede ser negativo.";
  if (numero > 99999999.99) return "El monto mínimo es demasiado grande.";
  return "";
}

/** Debe coincidir con backend/utils/validadores.js#validarUsosMaximosCupon. */
export function validarUsosMaximosCupon(value) {
  const valor = String(value ?? "").trim();
  if (valor === "") return ""; // opcional, NULL = ilimitado
  if (!/^\d+$/.test(valor)) return "Los usos máximos deben ser un número entero positivo.";
  if (Number(valor) < 1) return "Los usos máximos deben ser al menos 1.";
  if (Number(valor) > 2147483647) return "Los usos máximos son demasiado grandes.";
  return "";
}

function fechaValida(valor) {
  if (!valor) return null;
  const fecha = new Date(valor);
  return Number.isNaN(fecha.getTime()) ? null : fecha;
}

/** Debe coincidir con backend/utils/validadores.js#validarValidoDesde. */
export function validarValidoDesde(value) {
  if (!value) return "La fecha de inicio es obligatoria.";
  if (!fechaValida(value)) return "La fecha de inicio no es válida.";
  return "";
}

/**
 * cupones.valido_hasta: obligatoria y posterior a `validoDesde` (el
 * otro campo del mismo formulario).
 * Debe coincidir con backend/utils/validadores.js#validarValidoHasta.
 */
export function validarValidoHasta(value, valores) {
  if (!value) return "La fecha de fin es obligatoria.";
  const hasta = fechaValida(value);
  if (!hasta) return "La fecha de fin no es válida.";
  const desde = fechaValida(valores?.validoDesde);
  if (desde && hasta <= desde) {
    return "La fecha de fin debe ser posterior a la fecha de inicio.";
  }
  return "";
}

/* -------------------------------- Proveedores ------------------------------
 * Válidos "por UX": el backend (app/schemas/proveedor.py) es la fuente
 * de verdad real y revalida todo con las mismas reglas de negocio
 * (dígito de verificación del NIT, correo corporativo, coherencia
 * crédito/cupo). Estas funciones solo evitan un viaje redondo al
 * servidor para el error más obvio.
 * --------------------------------------------------------------------- */

const REGEX_NIT = /^\d{9,10}(-\d)?$/;
const REGEX_TELEFONO_PROVEEDOR = /^\+?[\d\s\-()]{7,20}$/;
const DOMINIOS_PERSONALES = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "icloud.com"];

export function validarRazonSocial(value) {
  const valor = (value || "").trim();
  if (!valor) return "La razón social es obligatoria.";
  if (valor.length < 3) return "Debe tener al menos 3 caracteres.";
  if (valor.length > 120) return "Debe tener máximo 120 caracteres.";
  return "";
}

export function validarNit(value) {
  const valor = (value || "").trim();
  if (!valor) return "El NIT es obligatorio.";
  if (!REGEX_NIT.test(valor)) return "Formato de NIT inválido (ej. 900123456-7).";
  return "";
}

export function validarCategoriaProveedor(value) {
  if (!value) return "Selecciona una categoría.";
  return "";
}

export function validarContactoNombre(value) {
  const valor = (value || "").trim();
  if (!valor) return "El nombre de contacto es obligatorio.";
  if (valor.length < 3) return "Debe tener al menos 3 caracteres.";
  if (valor.length > 80) return "Debe tener máximo 80 caracteres.";
  return "";
}

export function validarCorreoProveedor(value) {
  const valor = (value || "").trim();
  if (!valor) return "El correo es obligatorio.";
  if (!REGEX_CORREO.test(valor)) return "El correo no tiene un formato válido.";
  const dominio = valor.split("@")[1]?.toLowerCase();
  if (DOMINIOS_PERSONALES.includes(dominio)) {
    return "Usa el correo corporativo del proveedor, no una cuenta personal.";
  }
  return "";
}

export function validarTelefonoProveedor(value) {
  const valor = (value || "").trim();
  if (!valor) return "El teléfono es obligatorio.";
  if (!REGEX_TELEFONO_PROVEEDOR.test(valor)) return "El teléfono no tiene un formato válido.";
  return "";
}

export function validarCiudadProveedor(value) {
  const valor = (value || "").trim();
  if (!valor) return "La ciudad es obligatoria.";
  if (valor.length < 2) return "Debe tener al menos 2 caracteres.";
  if (valor.length > 60) return "Debe tener máximo 60 caracteres.";
  return "";
}

export function validarDireccionProveedor(value) {
  const valor = (value || "").trim();
  if (valor.length > 160) return "Debe tener máximo 160 caracteres.";
  return "";
}

export function validarSitioWebProveedor(value) {
  const valor = (value || "").trim();
  if (!valor) return "";
  if (!/^https?:\/\//i.test(valor)) return "Debe empezar por http:// o https://";
  if (valor.length > 160) return "Debe tener máximo 160 caracteres.";
  return "";
}

export function validarDiasCredito(value) {
  const valor = String(value ?? "").trim();
  if (valor === "") return "Los días de crédito son obligatorios (usa 0 para contado).";
  if (!/^\d+$/.test(valor)) return "Debe ser un número entero.";
  if (Number(valor) > 180) return "El máximo permitido es 180 días.";
  return "";
}

export function validarCupoCredito(value, valores) {
  const valor = String(value ?? "").trim();
  if (valor === "") return "El cupo de crédito es obligatorio (usa 0 si no aplica).";
  if (Number.isNaN(Number(valor)) || Number(valor) < 0) return "Debe ser un número mayor o igual a 0.";

  const dias = Number(valores?.diasCredito ?? 0);
  const cupo = Number(valor);
  if (dias > 0 && cupo <= 0) return "Con días de crédito mayores a 0, el cupo debe ser mayor a 0.";
  if (cupo > 0 && dias <= 0) return "Con un cupo mayor a 0, los días de crédito deben ser mayores a 0.";
  return "";
}

export function validarMotivoSuspension(value) {
  const valor = (value || "").trim();
  if (!valor) return "Describe el motivo de la suspensión.";
  if (valor.length < 10) return "Debe tener al menos 10 caracteres.";
  if (valor.length > 200) return "Debe tener máximo 200 caracteres.";
  if (valor.split(/\s+/).length < 3) return "Describe el motivo con al menos tres palabras.";
  return "";
}
