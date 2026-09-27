import { useEffect, useState } from "react";
import { useParams, useLocation, Link } from "react-router-dom";
import Icon from "../components/ui/Icon";
import ICON_PATHS from "../components/ui/iconPaths";
import useDocumentTitle from "../hooks/useDocumentTitle";
import { obtenerPedido, descargarFacturaPedido } from "../utils/api";
import { iniciarPagoConWompi } from "../utils/pagos";
import { useAuth } from "../hooks/useAuth";
import { formatearPrecio, formatearFecha, obtenerEstadoPedido } from "../utils/formato";

const ETIQUETA_METODO_PAGO = {
  tarjeta: "Tarjeta",
  transferencia: "Transferencia",
  contraentrega: "Pago contraentrega",
};

function PedidoDetalle() {
  const { id } = useParams();
  const ubicacion = useLocation();
  const reciénCreado = Boolean(ubicacion.state?.reciénCreado);
  const { usuario } = useAuth();
  const [errorPago, setErrorPago] = useState(ubicacion.state?.errorPago || "");
  const [pagando, setPagando] = useState(false);

  const [pedido, setPedido] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [descargando, setDescargando] = useState(false);
  const [errorFactura, setErrorFactura] = useState("");

  useDocumentTitle(
    reciénCreado ? "¡Pedido confirmado!" : `Pedido #${id}`,
    "Detalle de tu pedido en Dulce Esencia Pastelería.",
    `/pedidos/${id}`,
    true
  );

  // No hace falta setCargando(true)/setError("") acá: useState ya
  // arranca en (true, "") arriba, igual que en MisPedidos.jsx.
  useEffect(() => {
    obtenerPedido(id)
      .then(setPedido)
      .catch((err) => setError(err.message))
      .finally(() => setCargando(false));
  }, [id]);

  if (cargando) {
    return (
      <main className="mx-auto min-h-[60vh] max-w-2xl px-4 py-10 sm:px-6">
        <div className="h-40 animate-pulse rounded-2xl bg-section" aria-hidden="true" />
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto min-h-[60vh] max-w-2xl px-4 py-10 text-center sm:px-6">
        <p className="rounded-lg bg-peligro px-4 py-3 text-sm text-peligro-fuerte">{error}</p>
        <Link
          to="/panel/mis-pedidos"
          className="mt-4 inline-block text-sm font-medium text-primary underline underline-offset-2"
        >
          Volver a mis pedidos
        </Link>
      </main>
    );
  }

  if (!pedido) return null;

  const estado = obtenerEstadoPedido(pedido.estado);

  const handleDescargarFactura = async () => {
    setErrorFactura("");
    setDescargando(true);
    try {
      await descargarFacturaPedido(pedido.id);
    } catch (err) {
      setErrorFactura(err.message);
    } finally {
      setDescargando(false);
    }
  };

  const puedePagarConTarjeta = pedido.metodoPago === "tarjeta" && pedido.estado === "pendiente";

  const handlePagar = async () => {
    setErrorPago("");
    setPagando(true);
    try {
      await iniciarPagoConWompi(pedido, usuario); // redirige a Wompi
    } catch (err) {
      setErrorPago(err.message);
      setPagando(false);
    }
  };

  return (
    <main className="mx-auto min-h-[60vh] max-w-2xl px-4 py-10 sm:px-6">
      {puedePagarConTarjeta && (
        <div className="mb-6 rounded-2xl bg-aviso px-5 py-4 text-aviso-fuerte">
          <p className="font-semibold">Falta el pago de este pedido</p>
          <p className="text-sm">Paga con tarjeta de forma segura en Wompi para que empecemos a prepararlo.</p>
          {errorPago && (
            <p role="alert" className="mt-2 text-sm text-peligro-fuerte">
              {errorPago}
            </p>
          )}
          <button
            type="button"
            onClick={handlePagar}
            disabled={pagando}
            className="mt-3 rounded-full bg-primary px-5 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {pagando ? "Redirigiendo a Wompi..." : "Pagar con tarjeta"}
          </button>
        </div>
      )}

      {reciénCreado && !puedePagarConTarjeta && (
        <div className="mb-6 flex items-center gap-3 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 px-5 py-4 text-emerald-800 dark:text-emerald-300">
          <Icon path={ICON_PATHS.check} className="h-6 w-6 flex-shrink-0" />
          <div>
            <p className="font-semibold">¡Gracias por tu compra!</p>
            <p className="text-sm">Tu pedido quedó registrado y en breve empezaremos a prepararlo.</p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-primary sm:text-3xl">Pedido #{pedido.id}</h1>
        <span
          className="rounded-full px-3 py-1 text-xs font-semibold"
          style={{ color: estado.color, backgroundColor: estado.fondo }}
        >
          {estado.texto}
        </span>
      </div>
      <div className="mt-1 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-primary/70">{formatearFecha(pedido.creadoEn)}</p>
        <button
          type="button"
          onClick={handleDescargarFactura}
          disabled={descargando}
          className="inline-flex items-center gap-2 rounded-lg border border-beige/60 px-3 py-1.5 text-sm font-medium text-primary transition hover:bg-section disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Icon path={ICON_PATHS.download} className="h-4 w-4" />
          {descargando ? "Generando factura..." : "Descargar factura"}
        </button>
      </div>
      {errorFactura && (
        <p className="mt-2 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorFactura}</p>
      )}

      <div className="mt-6 rounded-2xl border border-beige/60 bg-cream p-5">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-primary/70">Productos</h2>
        <ul className="flex flex-col gap-3">
          {pedido.items.map((item) => (
            <li key={item.productoId} className="flex justify-between gap-3 text-sm">
              <span className="text-primary/80">
                {item.titulo} <span className="text-primary/70">× {item.cantidad}</span>
              </span>
              <span className="whitespace-nowrap font-medium text-primary">
                {formatearPrecio(item.subtotal)}
              </span>
            </li>
          ))}
        </ul>
        <div className="mt-4 flex flex-col gap-1 border-t border-beige/60 pt-3 text-sm text-primary/70">
          <div className="flex justify-between">
            <span>Subtotal</span>
            <span>{formatearPrecio(pedido.subtotal)}</span>
          </div>
          {Number(pedido.descuento) > 0 && (
            <div className="flex justify-between">
              <span>Descuento{pedido.cuponCodigo ? ` (${pedido.cuponCodigo})` : ""}</span>
              <span>-{formatearPrecio(pedido.descuento)}</span>
            </div>
          )}
          <div className="flex justify-between text-base font-bold text-primary">
            <span>Total</span>
            <span>{formatearPrecio(pedido.total)}</span>
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-4 rounded-2xl border border-beige/60 bg-cream p-5 sm:grid-cols-2">
        <div>
          <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-primary/70">
            Dirección de envío
          </h2>
          <p className="text-sm text-primary/80">{pedido.direccionEnvio}</p>
          <p className="text-sm text-primary/80">{pedido.telefonoContacto}</p>
        </div>
        <div>
          <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-primary/70">
            Método de pago
          </h2>
          <p className="text-sm text-primary/80">
            {ETIQUETA_METODO_PAGO[pedido.metodoPago] || pedido.metodoPago}
          </p>
        </div>
      </div>

      <Link
        to="/panel/mis-pedidos"
        className="mt-6 inline-block text-sm font-medium text-primary underline underline-offset-2"
      >
        ← Volver a mis pedidos
      </Link>
    </main>
  );
}

export default PedidoDetalle;
