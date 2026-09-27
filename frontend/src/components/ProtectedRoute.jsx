import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

/**
 * ProtectedRoute
 * Envuelve una página que requiere sesión iniciada. Si además se
 * pasa `rolesPermitidos`, exige que el usuario tenga uno de esos roles.
 *
 * Uso:
 *   <Route path="/panel" element={
 *     <ProtectedRoute><Panel /></ProtectedRoute>
 *   } />
 *
 *   <Route path="/panel/usuarios" element={
 *     <ProtectedRoute rolesPermitidos={["admin"]}><GestionUsuarios /></ProtectedRoute>
 *   } />
 */
function ProtectedRoute({ children, rolesPermitidos }) {
  const { isAuthenticated, usuario, cargando } = useAuth();
  const ubicacion = useLocation();

  if (cargando) return null;

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ desde: ubicacion.pathname }} replace />;
  }

  if (rolesPermitidos && !rolesPermitidos.includes(usuario.rol)) {
    return <Navigate to="/panel" replace />;
  }

  return children;
}

export default ProtectedRoute;
