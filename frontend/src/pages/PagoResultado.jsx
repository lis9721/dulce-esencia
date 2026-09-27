import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Icon from "../components/ui/Icon";
import ICON_PATHS from "../components/ui/iconPaths";
import useDocumentTitle from "../hooks/useDocumentTitle";
import { obtenerPagoPorReferencia, sincronizarPago } from "../utils/api";

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
        <div className="rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 px-6 py-8 text-emerald-800 dark:text-emerald-300">
          <Icon path={ICON_PATHS.check} className="mx-auto h-10 w-10" />
          <h1 className="mt-3 text-2xl font-bold">¡Pago aprobado!</h1>
          <p className="mt-1 text-sm">Referencia {pago.referencia}. Ya empezamos a preparar tu pedido.</p>
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
