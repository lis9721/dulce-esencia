import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Icon from "../components/ui/Icon";
import ICON_PATHS from "../components/ui/iconPaths";
import useDocumentTitle from "../hooks/useDocumentTitle";
import { obtenerPagoPorReferencia, sincronizarPago } from "../utils/api";
import { formatearPrecio } from "../utils/formato";

const INTERVALO_MS = 4000;
const MAX_INTENTOS = 8; // ~32 s esperando el webhook / la confirmación de Wompi

const FALLIDOS = ["DECLINED", "ERROR", "VOIDED", "EXPIRED"];

/**
 * Página a la que Wompi devuelve al cliente (?id=<transacción>&referencia=<REF>).
 * NO decide nada con lo que trae la URL: le pregunta a NUESTRO backend por el
 * estado real del pago, y el backend lo confirma con Wompi antes de responder.
 */
function PagoResultado() {
  const [params] = useSearchParams();
  const referencia = params.get("referencia");
  const idTransaccion = params.get("id");

  const [pago, setPago] = useState(null);
  const [error, setError] = useState(referencia ? "" : "Falta la referencia del pago en la dirección.");
  const [cargando, setCargando] = useState(Boolean(referencia));

  useDocumentTitle("Resultado del pago", "Estado de tu pago en Dulce Esencia Pastelería.", "/pago/resultado", true);

  useEffect(() => {
    if (!referencia) return undefined;
    let cancelado = false;
    let temporizador;

    const consultar = async (intento) => {
      try {
        let actual = await obtenerPagoPorReferencia(referencia);
        if (actual.estado === "PENDING") {
          // El webhook puede tardar (o no llegar en local): se pide confirmar con Wompi.
          actual = await sincronizarPago(actual.id, idTransaccion).catch(() => actual);
        }
        if (cancelado) return;
        setPago(actual);
        setCargando(false);
        if (actual.estado === "PENDING" && intento < MAX_INTENTOS) {
          temporizador = setTimeout(() => consultar(intento + 1), INTERVALO_MS);
        }
      } catch (err) {
        if (cancelado) return;
        setError(err.message);
        setCargando(false);
      }
    };

    consultar(1);
    return () => {
      cancelado = true;
      clearTimeout(temporizador);
    };
  }, [referencia, idTransaccion]);

  const aprobado = pago?.estado === "APPROVED";
  const fallido = pago && FALLIDOS.includes(pago.estado);
  const enEspera = pago?.estado === "PENDING";

  return (
    <main className="mx-auto min-h-[60vh] max-w-xl px-4 py-12 text-center sm:px-6">
      {cargando && <div className="h-40 animate-pulse rounded-2xl bg-section" aria-label="Consultando tu pago" />}

      {error && (
        <p role="alert" className="rounded-lg bg-peligro px-4 py-3 text-sm text-peligro-fuerte">
          {error}
        </p>
      )}

      {aprobado && (
        <div className="rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 p-6 text-emerald-900 dark:text-emerald-200 border border-emerald-200/60 dark:border-emerald-800/40 shadow-sm">
          <Icon path={ICON_PATHS.check} className="mx-auto h-12 w-12 text-emerald-600 dark:text-emerald-400" />
          <h1 className="mt-3 text-2xl font-bold">¡Pago aprobado con éxito!</h1>
          <p className="mt-1 text-sm text-emerald-800 dark:text-emerald-300">
            Transacción procesada correctamente por la pasarela Wompi. Ya empezamos a preparar tu pedido.
          </p>

          <div className="mt-6 rounded-xl bg-white/80 dark:bg-slate-900/60 p-4 text-left text-xs space-y-2 border border-emerald-200/50 dark:border-emerald-900/50">
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Referencia:</span>
              <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">{pago.referencia}</span>
            </div>
            {(pago.idTransaccionProveedor || idTransaccion) && (
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">ID Wompi:</span>
                <span className="font-mono text-slate-700 dark:text-slate-300">{pago.idTransaccionProveedor || idTransaccion}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Pasarela:</span>
              <span className="font-semibold text-emerald-700 dark:text-emerald-400">Wompi Colombia (Bancolombia)</span>
            </div>
            {pago.metodoPago && (
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Método:</span>
                <span className="font-medium text-slate-700 dark:text-slate-300">{pago.metodoPago}</span>
              </div>
            )}
            {pago.monto && (
              <div className="flex justify-between border-t border-emerald-200/40 dark:border-slate-800 pt-2 font-bold text-sm text-slate-900 dark:text-white">
                <span>Total pagado:</span>
                <span className="text-emerald-600 dark:text-emerald-400">{formatearPrecio(pago.monto)}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {enEspera && (
        <div className="rounded-2xl bg-aviso px-6 py-8 text-aviso-fuerte">
          <h1 className="text-2xl font-bold">Estamos confirmando tu pago</h1>
          <p className="mt-1 text-sm">Puede tardar unos segundos. No cierres esta página.</p>
        </div>
      )}

      {fallido && (
        <div className="rounded-2xl bg-peligro px-6 py-8 text-peligro-fuerte">
          <h1 className="text-2xl font-bold">No pudimos procesar el pago</h1>
          <p className="mt-1 text-sm">Estado: {pago.estado}. Tu pedido sigue pendiente; puedes intentarlo de nuevo.</p>
        </div>
      )}

      <div className="mt-6 flex flex-wrap items-center justify-center gap-4 text-sm font-medium">
        {pago?.pedidoId && (
          <Link to={`/pedidos/${pago.pedidoId}`} className="text-primary underline underline-offset-2">
            {fallido ? "Volver al pedido y reintentar" : "Ver mi pedido"}
          </Link>
        )}
        <Link to="/panel/mis-pedidos" className="text-primary underline underline-offset-2">
          Mis pedidos
        </Link>
      </div>
    </main>
  );
}

export default PagoResultado;
