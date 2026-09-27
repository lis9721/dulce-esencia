import { useContext } from "react";
import CartContext from "../context/CartContext";

/**
 * Hook de acceso rápido: const { items, total, cantidadTotal, agregar } = useCart();
 *
 * Vive en su propio archivo, igual que useAuth.js, por la misma razón:
 * un módulo que exporta un componente (CartProvider) Y un hook a la
 * vez rompe el Fast Refresh de Vite.
 */
export function useCart() {
  const contexto = useContext(CartContext);
  if (!contexto) {
    throw new Error("useCart debe usarse dentro de <CartProvider>.");
  }
  return contexto;
}

export default useCart;
