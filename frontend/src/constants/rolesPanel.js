/**
 * Roles que pueden entrar a cada sub-sección del panel. Es la fuente
 * de verdad que usa App.jsx para proteger /panel/productos y
 * /panel/usuarios con <ProtectedRoute rolesPermitidos={...}>, y que
 * usa Panel.jsx para decidir qué pestañas mostrar. Así el control de
 * acceso real (a nivel de router) y la UI nunca quedan desincronizados.
 *
 * Vive en su propio archivo (en vez de exportarse junto a un
 * componente) porque mezclar un export de componente con un export de
 * constante en el mismo módulo rompe el Fast Refresh de Vite
 * (ver regla react/only-export-components).
 */
export const ROLES_PANEL = {
  productos: ["admin", "empleado"],
  servicios: ["admin", "empleado"],
  usuarios: ["admin", "empleado"],
  pedidos: ["admin", "empleado"],
  // A diferencia de productos/usuarios/pedidos, cupones NO admite
  // "empleado": el backend protege las 4 rutas de gestión
  // (GET/POST/PUT/DELETE /api/cupones) con verificarRol("admin") a
  // secas (ver routes/cupones.routes.js) — aquí solo se refleja esa
  // misma regla, no se inventa una nueva.
  cupones: ["admin"],
  // Quinto Avance: gestión comercial, reportes y dashboards — mismo
  // criterio que productos/servicios/usuarios/pedidos (admin y
  // empleado, no cliente). Facturas y PQR NO tienen entrada acá
  // porque las ve cualquier rol autenticado (el backend filtra "solo
  // lo mío" para un cliente) — mismo criterio que "mis-pedidos".
  ventas: ["admin", "empleado"],
  dashboard: ["admin", "empleado"],
  // Proveedores: mismo criterio que productos — admin y empleado
  // gestionan, pero DELETE queda restringido a admin dentro del propio
  // GestionProveedores.jsx (igual que ya hace GestionProductos.jsx).
  proveedores: ["admin", "empleado"],
};
