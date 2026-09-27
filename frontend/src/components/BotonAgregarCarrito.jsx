import { useState } from "react";
import Icon from "./ui/Icon";
import ICON_PATHS from "./ui/iconPaths";
import Toast from "./Toast";
import { useCart } from "../hooks/useCart";

/**
 * BotonAgregarCarrito
 * Botón reutilizable para cualquier tarjeta de producto (carrusel del
 * home, catálogo de la Fase 6, página de detalle, etc.). Encapsula:
 * - El estado de carga mientras se agrega (evita doble clic con dos
 *   requests en vuelo).
 * - Feedback visual con Toast en vez de que el único indicador de
 *   "pasó algo" sea el número del ícono del Header cambiando.
 * - El caso "sin stock" / "producto despublicado": el botón se
 *   deshabilita en vez de dejar que el usuario descubra el error
 *   recién en la respuesta del backend.
 *
 * @param {{id:number, titulo:string, imagen:string, precio:number, stock:number, activo?:number|boolean}} producto
 */
function BotonAgregarCarrito({ producto, className = "" }) {
  const { agregar } = useCart();
  const [enviando, setEnviando] = useState(false);
  const [toast, setToast] = useState("");
  const [tonoToast, setTonoToast] = useState("exito");
  // Contador (no booleano) para poder retriggerar la animación de la
  // gota si el usuario agrega el mismo producto dos veces seguidas:
  // cambiar la "key" del elemento fuerza a React a remontarlo y la
  // animación CSS vuelve a correr desde el principio.
  const [gotaId, setGotaId] = useState(0);

  const sinStock = Number(producto.stock) <= 0;
  const inactivo = producto.activo === 0 || producto.activo === false;
  const deshabilitado = sinStock || inactivo || enviando;

  const handleClick = async (evento) => {
    // Cuando el botón vive dentro de la tarjeta clicable del carrusel
    // (ver Carousel.jsx), no queremos que el clic también dispare la
    // navegación/selección de la tarjeta.
    evento.stopPropagation();
    if (deshabilitado) return;

    setEnviando(true);
    try {
      await agregar(producto, 1);
      setTonoToast("exito");
      setToast(`"${producto.titulo}" se agregó al carrito.`);
      // Micro-interacción "gota": en vez de un check genérico, una
      // gotita (de glaseado) cae del botón hacia el carrito y se
      // desvanece (ver @keyframes gota-cae en index.css).
      setGotaId((id) => id + 1);
    } catch (error) {
      setTonoToast("error");
      setToast(error.message || "No se pudo agregar el producto al carrito.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        disabled={deshabilitado}
        aria-label={
          inactivo
            ? `${producto.titulo} ya no está disponible`
            : sinStock
              ? `${producto.titulo} sin stock disponible`
              : `Añadir ${producto.titulo} al carrito`
        }
        className={`relative inline-flex items-center justify-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-paper transition-all duration-200 hover:scale-105 hover:bg-accent-dark hover:shadow-md active:scale-95 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:scale-100 disabled:hover:shadow-none sm:text-sm ${className}`}
      >
        <Icon path={ICON_PATHS.cart} className="h-4 w-4" />
        {inactivo ? "No disponible" : sinStock ? "Agotado" : enviando ? "Agregando..." : "Añadir al carrito"}
        {gotaId > 0 && (
          <svg
            key={gotaId}
            aria-hidden="true"
            viewBox="0 0 10 14"
            className="animate-gota pointer-events-none absolute left-1/2 top-full h-3.5 w-2.5 -translate-x-1/2 text-accent"
          >
            <path
              fill="currentColor"
              d="M5 0C5 0 0 7 0 10a5 5 0 0 0 10 0C10 7 5 0 5 0Z"
            />
          </svg>
        )}
      </button>

      <Toast message={toast} tono={tonoToast} onDismiss={() => setToast("")} />
    </>
  );
}

export default BotonAgregarCarrito;
