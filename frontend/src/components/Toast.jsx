import { useEffect } from "react";
import Icon from "./ui/Icon";
import ICON_PATHS from "./ui/iconPaths";

const DURACION_MS = 2500;

/**
 * Toast
 * Aviso flotante y no bloqueante (ej. "Agregado al carrito") en vez de
 * un window.alert() o de confiar en que el usuario note que un número
 * cambió en algún ícono. Se autodescarta solo, y también se puede
 * cerrar a mano.
 *
 * Uso típico (ver BotonAgregarCarrito.jsx):
 *   const [toast, setToast] = useState("");
 *   <Toast message={toast} onDismiss={() => setToast("")} />
 */
function Toast({ message, tono = "exito", onDismiss }) {
  useEffect(() => {
    if (!message) return undefined;
    const temporizador = setTimeout(onDismiss, DURACION_MS);
    return () => clearTimeout(temporizador);
  }, [message, onDismiss]);

  if (!message) return null;

  const colorFondo = tono === "error" ? "bg-peligro-solido" : "bg-primary";
  // El texto acompaña al fondo: bg-primary cambia con el tema, así que
  // su texto (text-cream) debe poder cambiar junto con él. bg-peligro-solido
  // en cambio NO cambia con el tema, así que su texto necesita quedar
  // fijo (text-paper) para no perder contraste en modo oscuro.
  const colorTexto = tono === "error" ? "text-paper" : "text-cream";

  return (
    <output
      aria-live="polite"
      className={`animate-fade-in-up fixed inset-x-4 bottom-4 z-[60] mx-auto flex max-w-sm items-center justify-between gap-3 rounded-lg px-4 py-3 text-sm font-medium ${colorTexto} shadow-lg sm:inset-x-auto sm:right-4 ${colorFondo}`}
    >
      <span>{message}</span>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Cerrar aviso"
        className="rounded-full p-1 transition hover:bg-white/20"
      >
        <Icon path={ICON_PATHS.close} className="h-4 w-4" />
      </button>
    </output>
  );
}

export default Toast;
