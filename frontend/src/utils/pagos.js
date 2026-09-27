import { crearPago } from "./api";

/**
 * Inicia el pago con tarjeta de un pedido en Wompi y redirige al Web
 * Checkout. Si algo falla lanza un Error con el mensaje del servidor
 * (el pedido sigue "pendiente" y se puede reintentar desde su detalle).
 *
 * - El monto sale del total del pedido y el backend lo vuelve a validar:
 *   si alguien lo alterara desde el navegador, el servidor lo rechaza.
 * - `idempotencyKey`: misma clave = mismo pago (protege del doble clic).
 *   Cada reintento deliberado usa una clave nueva.
 */
export async function iniciarPagoConWompi(pedido, usuario, idempotencyKey = crypto.randomUUID()) {
  const nombre = [usuario?.nombre, usuario?.apellido].filter(Boolean).join(" ");
  const pago = await crearPago(
    {
      monto: Number(pedido.total),
      moneda: "COP",
      correoCliente: usuario.correo,
      nombreCliente: nombre || undefined,
      descripcion: `Pedido #${pedido.id}`,
      pedidoId: pedido.id,
      // Wompi devuelve al cliente aquí; el backend agrega ?referencia=...
      urlRedireccion: `${window.location.origin}/pago/resultado`,
    },
    `pedido-${pedido.id}-${idempotencyKey}`
  );
  window.location.assign(pago.checkoutUrl);
}
