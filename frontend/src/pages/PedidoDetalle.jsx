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
  tarjeta: "Tarjeta de crédito / débito (Pasarela Wompi)",
  transferencia: "Transferencia bancaria (Bancolombia / Nequi)",
  contraentrega: "Pago contraentrega (Efectivo o Datáfono)",
};

function PedidoDetalle() {
  const { id } = useParams();
  const ubicacion = useLocation();
  const reciénCreado = Boolean(ubicacion.state?.reciénCreado);
  const { usuario } = useAuth();
  const [errorPago, setErrorPago] = useState(ubicacion.state?.errorPago || "");
  const [pagando, setPagando] = useState(false);
  const [copiado, setCopiado] = useState("");

  const copiarAlPortapapeles = (texto, clave) => {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(texto);
      setCopiado(clave);
      setTimeout(() => setCopiado(""), 2500);
    }
  };

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
  const esTransferenciaPendiente = pedido.metodoPago === "transferencia" && pedido.estado === "pendiente";
  const esContraentregaPendiente = pedido.metodoPago === "contraentrega" && pedido.estado === "pendiente";
  const esPagado = pedido.estado === "pagado";

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
      {/* 1. Tarjeta Wompi pendiente */}
      {puedePagarConTarjeta && (
        <div className="mb-6 rounded-2xl bg-aviso px-5 py-5 text-aviso-fuerte border border-amber-300/60 shadow-sm">
          <div className="flex items-center gap-2">
            <span className="text-xl">💳</span>
            <div>
              <p className="font-bold text-base">Falta el pago de este pedido</p>
              <p className="text-xs mt-0.5">Paga con tarjeta de forma segura en Wompi para que empecemos a prepararlo.</p>
            </div>
          </div>
          {errorPago && (
            <p role="alert" className="mt-2 text-sm text-peligro-fuerte bg-white/70 dark:bg-slate-900/60 p-2 rounded-lg">
              {errorPago}
            </p>
          )}
          <button
            type="button"
            onClick={handlePagar}
            disabled={pagando}
            className="mt-4 rounded-full bg-primary px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:opacity-60 shadow-md flex items-center gap-2"
          >
            <span>🔒</span>
            {pagando ? "Redirigiendo a Wompi..." : "Pagar con Wompi (Tarjeta / Sandbox)"}
          </button>
        </div>
      )}

      {/* 2. Transferencia bancaria pendiente */}
      {esTransferenciaPendiente && (
        <div className="mb-6 rounded-2xl border border-blue-200/80 bg-blue-50/80 dark:border-blue-900/60 dark:bg-blue-950/40 p-5 text-blue-950 dark:text-blue-100 shadow-sm">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">🏦</span>
            <div>
              <h2 className="font-bold text-base text-blue-900 dark:text-blue-200">
                Esperando transferencia bancaria
              </h2>
              <p className="text-xs text-blue-800/80 dark:text-blue-300/80">
                Transfiere el valor exacto y envíanos tu comprobante para iniciar la preparación.
              </p>
            </div>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {/* Bancolombia */}
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/70 p-3.5 border border-blue-200/60 dark:border-blue-900/40 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Bancolombia Ahorros</span>
                  <span className="rounded bg-amber-500/15 text-amber-700 dark:text-amber-300 px-1.5 py-0.5 text-[10px] font-bold">Cero costo</span>
                </div>
                <p className="font-mono text-sm font-semibold text-slate-900 dark:text-white mt-1">
                  102-938475-12
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Dulce Esencia S.A.S. · NIT 901.458.789-1
                </p>
              </div>
              <button
                type="button"
                onClick={() => copiarAlPortapapeles("10293847512", "cuentaBancolombia")}
                className="mt-2 inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1 text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition"
              >
                {copiado === "cuentaBancolombia" ? "✓ ¡Copiado!" : "Copiar cuenta"}
              </button>
            </div>

            {/* Nequi / Daviplata */}
            <div className="rounded-xl bg-white/80 dark:bg-slate-900/70 p-3.5 border border-blue-200/60 dark:border-blue-900/40 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Nequi / Daviplata</span>
                  <span className="rounded bg-purple-500/15 text-purple-700 dark:text-purple-300 px-1.5 py-0.5 text-[10px] font-bold">Inmediato</span>
                </div>
                <p className="font-mono text-sm font-semibold text-slate-900 dark:text-white mt-1">
                  300 111 2233
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Titular: Valentina Ospina (Dulce Esencia)
                </p>
              </div>
              <button
                type="button"
                onClick={() => copiarAlPortapapeles("3001112233", "nequi")}
                className="mt-2 inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1 text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition"
              >
                {copiado === "nequi" ? "✓ ¡Copiado!" : "Copiar número"}
              </button>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-blue-200/50 dark:border-blue-900/40 flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs">
              <span className="text-slate-600 dark:text-slate-400 block">Total exacto a transferir:</span>
              <span className="text-lg font-extrabold text-blue-900 dark:text-blue-200">
                {formatearPrecio(pedido.total)}
              </span>
            </div>

            <a
              href={`https://wa.me/573001112233?text=${encodeURIComponent(
                `Hola Dulce Esencia Pastelería 👋, adjunto comprobante de transferencia para el Pedido #${pedido.id} por valor de ${formatearPrecio(pedido.total)} a nombre de ${usuario?.nombre || "Cliente"}.`
              )}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-4 py-2 text-xs transition shadow-sm"
            >
              <span>💬</span>
              Enviar comprobante por WhatsApp
            </a>
          </div>
        </div>
      )}

      {/* 3. Contraentrega pendiente */}
      {esContraentregaPendiente && (
        <div className="mb-6 rounded-2xl border border-amber-200/80 bg-amber-50/80 dark:border-amber-900/60 dark:bg-amber-950/40 p-5 text-amber-950 dark:text-amber-100 shadow-sm">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">🛵</span>
            <div>
              <h2 className="font-bold text-base text-amber-900 dark:text-amber-200">
                Pedido confirmado — Pago contraentrega
              </h2>
              <p className="text-xs text-amber-800/80 dark:text-amber-300/80">
                Tu pedido ya está en cola de cocina. Pagarás al momento de recibirlo.
              </p>
            </div>
          </div>

          <div className="mt-4 rounded-xl bg-white/80 dark:bg-slate-900/70 p-4 border border-amber-200/60 dark:border-amber-900/40 text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Total a pagar al repartidor:</span>
              <span className="font-bold text-amber-800 dark:text-amber-300 text-sm">{formatearPrecio(pedido.total)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Medios recibidos por el domiciliario:</span>
              <span className="font-medium text-slate-800 dark:text-slate-200">Efectivo o Datáfono inalámbrico</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Dirección registrada:</span>
              <span className="font-medium text-slate-800 dark:text-slate-200 text-right">{pedido.direccionEnvio}</span>
            </div>
          </div>
        </div>
      )}

      {/* 4. Pedido Pagado */}
      {esPagado && (
        <div className="mb-6 flex items-center gap-3 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200/60 dark:border-emerald-800/40 px-5 py-4 text-emerald-800 dark:text-emerald-300 shadow-sm">
          <Icon path={ICON_PATHS.check} className="h-6 w-6 flex-shrink-0 text-emerald-600 dark:text-emerald-400" />
          <div className="text-xs">
            <p className="font-bold text-sm">¡Pago verificado y confirmado!</p>
            <p className="text-emerald-700 dark:text-emerald-400">
              Tu pago fue registrado exitosamente con {ETIQUETA_METODO_PAGO[pedido.metodoPago] || pedido.metodoPago}. Estamos preparando tus productos.
            </p>
          </div>
        </div>
      )}

      {reciénCreado && !puedePagarConTarjeta && !esTransferenciaPendiente && !esContraentregaPendiente && !esPagado && (
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
