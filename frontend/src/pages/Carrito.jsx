import { useState } from "react";
import { Link } from "react-router-dom";
import Icon from "../components/ui/Icon";
import ICON_PATHS from "../components/ui/iconPaths";
import ConfirmModal from "../components/ui/ConfirmModal";
import Button from "../components/ui/Button";
import { formatearPrecio, resolverUrlImagen } from "../utils/formato";
import { useCart } from "../hooks/useCart";
import { useAuth } from "../hooks/useAuth";
import useDocumentTitle from "../hooks/useDocumentTitle";

/**
 * Campo de cupón del carrito (Flujo 6 del plan de tienda): valida el
 * código contra el subtotal actual vía `aplicarCupon` (CartContext,
 * que llama a POST /api/cupones/validar) y muestra el descuento antes
 * de llegar al checkout — así no hay sorpresas al confirmar el pedido.
 * Solo aplica: no gasta un uso del cupón, eso ocurre recién al
 * confirmar la compra.
 */
function CampoCupon({ cuponAplicado, aplicarCupon, quitarCupon }) {
  const [codigo, setCodigo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");

  const handleAplicar = async (evento) => {
    evento.preventDefault();
    if (!codigo.trim()) return;
    setEnviando(true);
    setError("");
    try {
      await aplicarCupon(codigo);
      setCodigo("");
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  };

  if (cuponAplicado) {
    return (
      <div className="mt-4 flex items-center justify-between gap-3 rounded-lg bg-exito px-4 py-3">
        <p className="text-sm text-exito-fuerte">
          Cupón <span className="font-semibold">{cuponAplicado.codigo}</span> aplicado: -
          {formatearPrecio(cuponAplicado.descuento)}
        </p>
        <button
          type="button"
          onClick={quitarCupon}
          className="text-xs font-medium text-exito-fuerte underline underline-offset-2 hover:text-exito-fuerte"
        >
          Quitar
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleAplicar} className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-start">
      <div className="flex-1">
        <label htmlFor="cupon" className="sr-only">
          Código de cupón
        </label>
        <input
          id="cupon"
          name="cupon"
          value={codigo}
          onChange={(evento) => setCodigo(evento.target.value)}
          placeholder="¿Tienes un código de descuento?"
          className="w-full rounded-lg border border-beige bg-cream px-3 py-2 text-sm uppercase text-primary outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
        {error && <p className="mt-1 text-xs font-medium text-peligro-fuerte">{error}</p>}
      </div>
      <Button type="submit" variant="secondary" disabled={enviando || !codigo.trim()}>
        {enviando ? "Validando..." : "Aplicar"}
      </Button>
    </form>
  );
}

/**
 * Selector de cantidad +/-, bloqueado en 1 como mínimo y en el stock
 * disponible como máximo (Flujo 2 del plan de tienda: "si sube la
 * cantidad más allá del stock disponible, el campo lo bloquea y
 * avisa... no se descubre el problema hasta el checkout").
 */
function SelectorCantidad({ cantidad, stock, disabled, onCambiar }) {
  const enElMaximo = cantidad >= stock;

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={() => onCambiar(cantidad - 1)}
        disabled={disabled || cantidad <= 1}
        aria-label="Disminuir cantidad"
        className="flex h-8 w-8 items-center justify-center rounded-full border border-beige text-primary transition hover:bg-section disabled:cursor-not-allowed disabled:opacity-40"
      >
        <Icon path={ICON_PATHS.minus} className="h-4 w-4" />
      </button>
      <span className="w-6 text-center text-sm font-semibold text-primary" aria-live="polite">
        {cantidad}
      </span>
      <button
        type="button"
        onClick={() => onCambiar(cantidad + 1)}
        disabled={disabled || enElMaximo}
        aria-label="Aumentar cantidad"
        className="flex h-8 w-8 items-center justify-center rounded-full border border-beige text-primary transition hover:bg-section disabled:cursor-not-allowed disabled:opacity-40"
      >
        <Icon path={ICON_PATHS.plus} className="h-4 w-4" />
      </button>
    </div>
  );
}

function FilaCarrito({ item, onActualizar, onQuitar }) {
  const [enviando, setEnviando] = useState(false);
  const [errorFila, setErrorFila] = useState("");
  const inactivo = item.activo === 0 || item.activo === false;
  const sinStockSuficiente = !inactivo && item.cantidad > item.stock;

  const cambiarCantidad = async (nuevaCantidad) => {
    if (nuevaCantidad < 1 || nuevaCantidad > item.stock) return;
    setEnviando(true);
    setErrorFila("");
    try {
      await onActualizar(item.productoId, nuevaCantidad);
    } catch (error) {
      // Puede pasar que el stock cambió (otro cliente compró) entre
      // que se cargó la página y este clic: se avisa acá mismo, en la
      // fila, en vez de dejar una promesa sin atender.
      setErrorFila(error.message);
    } finally {
      setEnviando(false);
    }
  };

  const quitar = async () => {
    setEnviando(true);
    setErrorFila("");
    try {
      await onQuitar(item.productoId);
    } catch (error) {
      setErrorFila(error.message);
      setEnviando(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 border-b border-beige/50 py-4 sm:flex-row sm:items-center">
      <div className="flex flex-1 items-center gap-4">
        {item.imagen && (
          <img
            src={resolverUrlImagen(item.imagen)}
            alt={item.titulo}
            className="h-16 w-16 flex-shrink-0 rounded-lg object-cover"
          />
        )}
        <div>
          <p className="font-medium text-primary">{item.titulo}</p>
          <p className="text-sm text-primary/70">{formatearPrecio(item.precio)} c/u</p>
          {inactivo && (
            <p className="mt-1 text-xs font-medium text-peligro-fuerte">
              Este producto ya no está disponible. Quítalo del carrito para continuar.
            </p>
          )}
          {sinStockSuficiente && (
            <p className="mt-1 text-xs font-medium text-peligro-fuerte">
              Solo quedan {item.stock} unidades disponibles.
            </p>
          )}
          {errorFila && <p className="mt-1 text-xs font-medium text-peligro-fuerte">{errorFila}</p>}
        </div>
      </div>

      <div className="flex items-center justify-between gap-4 sm:justify-end">
        <SelectorCantidad
          cantidad={item.cantidad}
          stock={item.stock}
          disabled={enviando || inactivo}
          onCambiar={cambiarCantidad}
        />
        <p className="w-24 text-right text-sm font-semibold text-primary">
          {formatearPrecio(item.subtotal)}
        </p>
        <button
          type="button"
          onClick={quitar}
          disabled={enviando}
          aria-label={`Quitar ${item.titulo} del carrito`}
          className="rounded-full p-2 text-primary/70 transition hover:bg-peligro hover:text-peligro-fuerte disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Icon path={ICON_PATHS.trash} className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}

function Carrito() {
  useDocumentTitle("Tu carrito", "Revisa y edita los productos de tu carrito en Dulce Esencia Pastelería.", "/carrito", true);

  const {
    items,
    total,
    cargando,
    error,
    esInvitado,
    actualizar,
    quitar,
    vaciar,
    cuponAplicado,
    totalConDescuento,
    aplicarCupon,
    quitarCupon,
  } = useCart();
  const { isAuthenticated } = useAuth();
  const [confirmandoVaciado, setConfirmandoVaciado] = useState(false);

  const hayProductosBloqueados = items.some(
    (item) => item.activo === 0 || item.activo === false || item.cantidad > item.stock
  );

  return (
    <main className="mx-auto min-h-[60vh] max-w-3xl px-4 py-10 sm:px-6">
      <h1 className="text-2xl font-bold text-primary sm:text-3xl">Tu carrito</h1>

      {esInvitado && (
        <p className="mt-2 text-sm text-primary/70">
          Estás viendo tu carrito como invitado.{" "}
          <Link to="/login" className="font-medium text-primary underline underline-offset-2">
            Inicia sesión
          </Link>{" "}
          para guardarlo en tu cuenta y poder pagar.
        </p>
      )}

      {error && (
        <p className="mt-4 rounded-lg bg-peligro px-4 py-3 text-sm text-peligro-fuerte">{error}</p>
      )}

      {cargando && items.length === 0 ? (
        <div className="mt-8 space-y-3" aria-hidden="true">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-20 animate-pulse rounded-lg bg-section" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="mt-10 flex flex-col items-center gap-4 rounded-xl bg-section px-6 py-14 text-center">
          <Icon path={ICON_PATHS.cart} className="h-10 w-10 text-primary/30" />
          <p className="text-primary/70">Todavía no has agregado ningún producto.</p>
          <Link
            to="/"
            className="inline-block rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-cream transition hover:bg-primary-dark"
          >
            Ver productos
          </Link>
        </div>
      ) : (
        <>
          <div className="mt-6">
            {items.map((item) => (
              <FilaCarrito key={item.productoId} item={item} onActualizar={actualizar} onQuitar={quitar} />
            ))}
          </div>

          {/* Sin sesión no se puede aplicar cupón todavía: el backend
              exige `verificarToken` en POST /api/cupones/validar
              (Fase 3 solo lo ofrece a carritos ya asociados a un
              usuario). El invitado ve el campo recién al iniciar
              sesión, igual que ya pasa con "Ir a pagar". */}
          {!esInvitado && (
            <CampoCupon cuponAplicado={cuponAplicado} aplicarCupon={aplicarCupon} quitarCupon={quitarCupon} />
          )}

          <div className="mt-6 flex items-center justify-between border-t border-beige/60 pt-4">
            <button
              type="button"
              onClick={() => setConfirmandoVaciado(true)}
              className="text-sm font-medium text-primary/70 underline-offset-2 hover:text-peligro-fuerte hover:underline"
            >
              Vaciar carrito
            </button>
            <div className="text-right">
              {cuponAplicado && (
                <p className="text-sm text-primary/70 line-through">{formatearPrecio(total)}</p>
              )}
              <p className="text-lg font-bold text-primary">Total: {formatearPrecio(totalConDescuento)}</p>
            </div>
          </div>

          {hayProductosBloqueados && (
            <p className="mt-3 text-sm text-peligro-fuerte">
              Ajusta las cantidades marcadas arriba antes de continuar.
            </p>
          )}

          {/* /checkout ya existe (Fase 2): ProtectedRoute se encarga de
              mandar a /login y volver acá si no hay sesión iniciada,
              así que este botón no necesita esa lógica. */}
          <div className="mt-6 flex justify-end">
            <Link
              to="/checkout"
              aria-disabled={hayProductosBloqueados}
              onClick={(evento) => hayProductosBloqueados && evento.preventDefault()}
              className={`inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-cream transition-all duration-200 hover:scale-[1.03] hover:bg-primary-dark hover:shadow-md active:scale-[0.97] ${
                hayProductosBloqueados ? "pointer-events-none cursor-not-allowed opacity-60" : ""
              }`}
            >
              Ir a pagar
            </Link>
          </div>
          {!isAuthenticated && (
            <p className="mt-2 text-right text-xs text-primary/70">
              Necesitarás iniciar sesión para completar la compra.
            </p>
          )}
        </>
      )}

      <ConfirmModal
        isOpen={confirmandoVaciado}
        onClose={() => setConfirmandoVaciado(false)}
        title="Vaciar carrito"
        message="¿Quitar todos los productos de tu carrito? Esta acción no se puede deshacer."
        confirmLabel="Vaciar"
        onConfirm={vaciar}
      />
    </main>
  );
}

export default Carrito;
