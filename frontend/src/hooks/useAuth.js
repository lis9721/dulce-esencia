import { useContext } from "react";
import AuthContext from "../context/AuthContext";

/**
 * Hook de acceso rápido: const { usuario, isAuthenticated, logout } = useAuth();
 *
 * Vive en su propio archivo (y no junto a `AuthProvider` en
 * AuthContext.jsx) porque un módulo que exporta un componente Y un hook
 * a la vez rompe el Fast Refresh de Vite (ver regla
 * react/only-export-components): al editar cualquiera de los dos, Vite
 * no puede refrescar en caliente y recarga toda la página.
 */
export function useAuth() {
  const contexto = useContext(AuthContext);
  if (!contexto) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>.");
  }
  return contexto;
}

export default useAuth;
