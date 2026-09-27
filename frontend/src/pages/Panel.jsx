import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { ROLES_PANEL } from "../constants/rolesPanel";
import useDocumentTitle from "../hooks/useDocumentTitle";

/**
 * Nombre a mostrar en el saludo del panel. Usa `usuario.nombre` (viene
 * tanto en la respuesta de /login como en /usuarios/perfil), con el
 * correo como respaldo solo si ese campo faltara — mismo criterio que
 * ya usa `iniciales()` en components/UserMenu.jsx para el avatar del
 * navbar, para no tener dos formas distintas de mostrar la identidad
 * del usuario en la misma app.
 */
function nombreParaSaludar(usuario) {
  return usuario?.nombre?.trim() || usuario?.correo?.split("@")[0] || "";
}

/**
 * Iniciales para el avatar de la tarjeta de usuario de la sidebar
 * (ej. "Laura Gómez" -> "LG"). Mismo criterio que UserMenu.jsx.
 */
function inicialesUsuario(usuario) {
  const inicialNombre = usuario?.nombre?.trim()?.[0];
  const inicialApellido = usuario?.apellido?.trim()?.[0];
  if (inicialNombre && inicialApellido) return `${inicialNombre}${inicialApellido}`.toUpperCase();
  if (inicialNombre) return inicialNombre.toUpperCase();
  return (usuario?.correo || "").slice(0, 2).toUpperCase();
}

/**
 * Pestañas visibles según el rol del usuario autenticado. Se calculan a
 * partir de ROLES_PANEL (la misma fuente de verdad que usa App.jsx para
 * proteger /panel/productos y /panel/usuarios) en vez de mantener una
 * segunda lista de roles por pestaña: así es imposible que la UI muestre
 * una pestaña a la que la ruta después le niegue el acceso, o viceversa.
 *
 * "Mi perfil" y "Mis pedidos" van siempre primero, para cualquier rol;
 * el resto de pestañas (gestión) se agrega solo si el rol tiene permiso.
 * gruposSidebar() se apoya en ese mismo orden para separar ambos bloques.
 */
function pestañasParaRol(rol) {
  const pestañas = [{ to: "/panel", end: true, label: "Mi perfil" }];
  pestañas.push({ to: "/panel/mis-pedidos", label: "Mis pedidos" });
  // Facturas y PQR: cualquier rol autenticado, igual que "Mis pedidos"
  // (el backend filtra "solo lo mío" para un cliente).
  pestañas.push({ to: "/panel/facturas", label: rol === "cliente" ? "Mis facturas" : "Facturas" });
  pestañas.push({ to: "/panel/pqr", label: "PQR" });
  if (ROLES_PANEL.dashboard.includes(rol)) {
    pestañas.push({ to: "/panel/dashboard", label: "Dashboard" });
  }
  if (ROLES_PANEL.ventas.includes(rol)) {
    pestañas.push({ to: "/panel/ventas", label: "Ventas" });
  }
  if (ROLES_PANEL.productos.includes(rol)) {
    pestañas.push({ to: "/panel/productos", label: "Productos" });
  }
  if (ROLES_PANEL.servicios.includes(rol)) {
    pestañas.push({ to: "/panel/servicios", label: "Servicios" });
  }
  if (ROLES_PANEL.proveedores.includes(rol)) {
    pestañas.push({ to: "/panel/proveedores", label: "Proveedores" });
  }
  if (ROLES_PANEL.usuarios.includes(rol)) {
    pestañas.push({ to: "/panel/usuarios", label: "Usuarios" });
  }
  if (ROLES_PANEL.pedidos.includes(rol)) {
    pestañas.push({ to: "/panel/pedidos", label: "Pedidos" });
  }
  if (ROLES_PANEL.cupones.includes(rol)) {
    pestañas.push({ to: "/panel/cupones", label: "Cupones" });
  }
  return pestañas;
}

/**
 * Agrupa las pestañas de la sidebar de escritorio en dos bloques con
 * rótulo — "Gestión" (todo lo operativo: productos, servicios, usuarios,
 * pedidos, cupones) y "Mi cuenta" (perfil, mis pedidos) — en vez de una
 * lista plana, para que se lea mejor a medida que crecen las opciones
 * (caso admin/empleado).
 *
 * El cliente no tiene pestañas de "Gestión" (ROLES_PANEL nunca incluye
 * "cliente"), así que para ese rol se devuelve un único grupo sin
 * rótulo: una sidebar con solo 2 opciones no necesita agruparse en
 * bloques, se vería sobredimensionada para lo poco que muestra.
 */
function gruposSidebar(rol) {
  const pestañas = pestañasParaRol(rol);
  // Los primeros 4 ítems de pestañasParaRol() son siempre "Mi cuenta"
  // (perfil, mis pedidos, facturas, PQR) para cualquier rol; el resto
  // (dashboard, ventas, productos, ...) es "Gestión" y solo existe
  // para admin/empleado.
  const cuenta = pestañas.slice(0, 4);
  const gestion = pestañas.slice(4);

  if (gestion.length === 0) {
    return [{ titulo: null, pestañas: cuenta }];
  }
  return [
    { titulo: "Gestión", pestañas: gestion },
    { titulo: "Mi cuenta", pestañas: cuenta },
  ];
}

const ETIQUETA_ROL = {
  cliente: "Cliente",
  empleado: "Empleado",
  admin: "Administrador",
};

// Color del badge de rol en la tarjeta de usuario de la sidebar: ayuda a
// identificar de un vistazo con qué tipo de cuenta se está trabajando,
// sin agregar colores nuevos a la paleta ya definida en index.css.
const BADGE_ROL = {
  admin: "bg-accent/20 text-accent",
  empleado: "bg-sage/30 text-primary",
  cliente: "bg-blush/30 text-primary",
};

/**
 * Subtítulo bajo el saludo. Para "cliente" se usa el lenguaje de una
 * tienda ("Mi cuenta") en vez de "Panel de Cliente", que suena más a
 * jerga interna de back-office — admin/empleado sí son back-office real,
 * así que mantienen "Panel de …".
 */
function subtituloPanel(rol) {
  if (rol === "cliente") return "Mi cuenta · Dulce Esencia Pastelería";
  return `Panel de ${ETIQUETA_ROL[rol] || "usuario"} · Dulce Esencia Pastelería`;
}

function claseItemSidebar({ isActive }) {
  return `rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-200 ${
    isActive ? "bg-primary text-cream" : "text-primary/70 hover:bg-section hover:text-primary"
  }`;
}

function Panel() {
  useDocumentTitle("Mi panel", "Panel privado de gestión de Dulce Esencia Pastelería.", "/panel", true);

  const { usuario, logout } = useAuth();
  const navigate = useNavigate();

  // Defensa extra: si por lo que sea Panel se renderizara sin un usuario
  // cargado (por ejemplo, un cambio futuro que reordene los guards),
  // no explota con "Cannot read properties of null" — el ErrorBoundary
  // ya cubre errores inesperados, pero esto evita uno totalmente evitable.
  if (!usuario) return null;

  const pestañas = pestañasParaRol(usuario.rol);
  const grupos = gruposSidebar(usuario.rol);

  const cerrarSesion = async () => {
    await logout();
    navigate("/");
  };

  return (
    <main className="flex-1 bg-section px-4 py-10 sm:px-6">
      <div className="mx-auto max-w-6xl md:grid md:grid-cols-[15rem_1fr] md:items-start md:gap-8">
        {/* Sidebar — solo escritorio. "sticky top-20" asume el header
            fijo (Header.jsx) de ~5rem de alto; ajustar ese valor si
            cambia la altura real del header. */}
        <aside className="sticky top-20 hidden h-fit flex-col gap-4 rounded-xl border border-beige/70 bg-cream p-4 md:flex">
          <div className="flex items-center gap-3 border-b border-beige/60 pb-4">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-cream">
              {inicialesUsuario(usuario)}
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-primary">
                {nombreParaSaludar(usuario)}
              </p>
              <span
                className={`mt-0.5 inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                  BADGE_ROL[usuario.rol] || "bg-beige/40 text-primary"
                }`}
              >
                {ETIQUETA_ROL[usuario.rol] || "Usuario"}
              </span>
            </div>
          </div>

          {grupos.map((grupo, indice) => (
            <nav
              key={grupo.titulo || indice}
              className="flex flex-col gap-1"
              aria-label={grupo.titulo || "Secciones del panel"}
            >
              {grupo.titulo && (
                <p className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-primary/40">
                  {grupo.titulo}
                </p>
              )}
              {grupo.pestañas.map((pestaña) => (
                <NavLink key={pestaña.to} to={pestaña.to} end={pestaña.end} className={claseItemSidebar}>
                  {pestaña.label}
                </NavLink>
              ))}
            </nav>
          ))}

          <div className="mt-1 flex flex-col gap-1 border-t border-beige/60 pt-3">
            {/* Acceso rápido propio del cliente: entra al panel a revisar
                su cuenta, pero seguramente quiere volver a comprar. */}
            {usuario.rol === "cliente" && (
              <NavLink
                to="/tienda"
                className="rounded-lg px-3 py-2 text-sm font-medium text-primary/70 hover:bg-blush/20 hover:text-primary"
              >
                Volver a la tienda
              </NavLink>
            )}
            <button
              type="button"
              onClick={cerrarSesion}
              className="rounded-lg px-3 py-2 text-left text-sm font-medium text-peligro-fuerte hover:bg-peligro dark:text-peligro-fuerte dark:hover:bg-peligro"
            >
              Cerrar sesión
            </button>
          </div>
        </aside>

        {/* Contenido */}
        <div className="min-w-0">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-primary">Hola, {nombreParaSaludar(usuario)}</h1>
            <p className="text-sm text-primary/70">{subtituloPanel(usuario.rol)}</p>
          </div>

          {/* Fila de pestañas horizontal — solo móvil/tablet, donde una
              sidebar no cabe bien. En escritorio la reemplaza la
              sidebar de la izquierda con las mismas pestañas. */}
          <nav className="mb-6 flex flex-wrap gap-2 md:hidden" aria-label="Secciones del panel">
            {pestañas.map((pestaña) => (
              <NavLink
                key={pestaña.to}
                to={pestaña.to}
                end={pestaña.end}
                className={({ isActive }) =>
                  `rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 hover:scale-105 ${
                    isActive
                      ? "bg-primary text-cream shadow-sm"
                      : "bg-cream text-primary/70 hover:text-primary hover:shadow-sm"
                  }`
                }
              >
                {pestaña.label}
              </NavLink>
            ))}
          </nav>

          <Outlet />
        </div>
      </div>
    </main>
  );
}

export default Panel;
