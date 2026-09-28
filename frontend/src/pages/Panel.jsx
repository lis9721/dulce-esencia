import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import logo from "../assets/images/logo1.webp";
import { useAuth } from "../hooks/useAuth";
import useDarkMode from "../hooks/useDarkMode";
import { ROLES_PANEL } from "../constants/rolesPanel";
import useDocumentTitle from "../hooks/useDocumentTitle";
import Icon from "../components/ui/Icon";
import ICON_PATHS from "../components/ui/iconPaths";

/**
 * Nombre a mostrar en el saludo del panel.
 */
function nombreParaSaludar(usuario) {
  return usuario?.nombre?.trim() || usuario?.correo?.split("@")[0] || "";
}

/**
 * Iniciales para el avatar de la tarjeta de usuario de la sidebar.
 */
function inicialesUsuario(usuario) {
  const inicialNombre = usuario?.nombre?.trim()?.[0];
  const inicialApellido = usuario?.apellido?.trim()?.[0];
  if (inicialNombre && inicialApellido) return `${inicialNombre}${inicialApellido}`.toUpperCase();
  if (inicialNombre) return inicialNombre.toUpperCase();
  return (usuario?.correo || "").slice(0, 2).toUpperCase();
}

/**
 * Saludo según la hora del día.
 */
function saludoSegunHora() {
  const hora = new Date().getHours();
  if (hora < 12) return "Buenos días";
  if (hora < 18) return "Buenas tardes";
  return "Buenas noches";
}

/**
 * Pestañas visibles según el rol del usuario con su respectivo icono.
 */
function pestañasParaRol(rol) {
  const pestañas = [
    { to: "/panel", end: true, label: "Mi perfil", icono: ICON_PATHS.user, desc: "Administra tus datos personales y la seguridad de tu cuenta." },
    { to: "/panel/mis-pedidos", label: "Mis pedidos", icono: ICON_PATHS.bag, desc: "Consulta el estado y el historial de tus compras." },
    { to: "/panel/facturas", label: rol === "cliente" ? "Mis facturas" : "Facturas", icono: ICON_PATHS.receipt, desc: "Revisa y descarga tus facturas y recibos." },
    { to: "/panel/pqr", label: "PQR", icono: ICON_PATHS.chat, desc: "Peticiones, quejas y reclamos con su seguimiento." },
  ];

  if (ROLES_PANEL.dashboard.includes(rol)) {
    pestañas.push({ to: "/panel/dashboard", label: "Dashboard", icono: ICON_PATHS.chart, desc: "Indicadores y métricas del negocio de un vistazo." });
  }
  if (ROLES_PANEL.ventas.includes(rol)) {
    pestañas.push({ to: "/panel/ventas", label: "Ventas", icono: ICON_PATHS.cart, desc: "Registra ventas en mostrador y revisa el reporte de caja." });
  }
  if (ROLES_PANEL.productos.includes(rol)) {
    pestañas.push({ to: "/panel/productos", label: "Productos", icono: ICON_PATHS.package, desc: "Gestiona el catálogo y el inventario de productos." });
  }
  if (ROLES_PANEL.servicios.includes(rol)) {
    pestañas.push({ to: "/panel/servicios", label: "Servicios", icono: ICON_PATHS.sparkle, desc: "Administra los talleres, eventos y servicios ofrecidos." });
  }
  if (ROLES_PANEL.proveedores.includes(rol)) {
    pestañas.push({ to: "/panel/proveedores", label: "Proveedores", icono: ICON_PATHS.truck, desc: "Proveedores de insumos y materias primas." });
  }
  if (ROLES_PANEL.usuarios.includes(rol)) {
    pestañas.push({ to: "/panel/usuarios", label: "Usuarios", icono: ICON_PATHS.users, desc: "Cuentas de usuario, roles y permisos de acceso." });
  }
  if (ROLES_PANEL.pedidos.includes(rol)) {
    pestañas.push({ to: "/panel/pedidos", label: "Pedidos", icono: ICON_PATHS.bag, desc: "Gestiona los pedidos y su estado de entrega." });
  }
  if (ROLES_PANEL.cupones.includes(rol)) {
    pestañas.push({ to: "/panel/cupones", label: "Cupones", icono: ICON_PATHS.tag, desc: "Crea y controla cupones y códigos de descuento." });
  }

  return pestañas;
}

/**
 * Agrupa las pestañas de la sidebar en bloques.
 */
function gruposSidebar(rol) {
  const pestañas = pestañasParaRol(rol);
  const cuenta = pestañas.slice(0, 4);
  const gestion = pestañas.slice(4);

  const grupos = [];
  if (gestion.length > 0) grupos.push({ titulo: "Gestión", pestañas: gestion });
  grupos.push({ titulo: "Mi cuenta", pestañas: cuenta });
  return grupos;
}

const ETIQUETA_ROL = {
  cliente: "Cliente",
  empleado: "Empleado",
  admin: "Administrador",
};

const BADGE_ROL = {
  admin: "bg-accent/15 text-accent-dark dark:text-accent-soft",
  empleado: "bg-exito text-exito-fuerte",
  cliente: "bg-blush/50 text-ink",
};

function claseItemSidebar({ isActive }) {
  return `group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
    isActive
      ? "bg-accent/10 font-semibold text-accent-dark dark:text-accent-soft"
      : "font-medium text-primary/70 hover:bg-section hover:text-primary"
  }`;
}

const CLASE_ENLACE_SITIO =
  "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-primary/70 transition-colors hover:bg-section hover:text-primary";

/**
 * Contenido de la sidebar (logo, navegación por grupos, enlaces al
 * sitio y tarjeta del usuario). Se usa dos veces: fija en escritorio
 * y dentro del drawer en móvil, por eso vive como componente propio.
 */
function SidebarContenido({ grupos, usuario, onNavegar, onCerrarSesion }) {
  return (
    <div className="flex h-full flex-col">
      <Link
        to="/"
        onClick={onNavegar}
        className="flex h-16 shrink-0 items-center gap-3 border-b border-beige px-5"
        aria-label="Dulce Esencia Pastelería, ir al inicio"
      >
        <img src={logo} alt="" width={36} height={40} className="h-10 w-auto" />
        <span className="leading-tight">
          <span className="block font-display text-base font-bold text-primary">Dulce Esencia</span>
          <span className="block text-xs text-primary/55">Panel de control</span>
        </span>
      </Link>

      <div className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
        {grupos.map((grupo) => (
          <div key={grupo.titulo}>
            <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-primary/45">
              {grupo.titulo}
            </p>
            <nav className="flex flex-col gap-0.5" aria-label={grupo.titulo}>
              {grupo.pestañas.map((pestaña) => (
                <NavLink
                  key={pestaña.to}
                  to={pestaña.to}
                  end={pestaña.end}
                  onClick={onNavegar}
                  className={claseItemSidebar}
                >
                  {({ isActive }) => (
                    <>
                      {isActive && (
                        <span
                          aria-hidden="true"
                          className="absolute -left-3 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-accent"
                        />
                      )}
                      <Icon path={pestaña.icono} className="h-[18px] w-[18px] shrink-0" />
                      <span className="flex-1 truncate">{pestaña.label}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </nav>
          </div>
        ))}

        <div>
          <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-primary/45">
            Sitio
          </p>
          <nav className="flex flex-col gap-0.5" aria-label="Sitio">
            <Link to="/tienda" onClick={onNavegar} className={CLASE_ENLACE_SITIO}>
              <Icon path={ICON_PATHS.cart} className="h-[18px] w-[18px] shrink-0" />
              <span>Ir a la tienda</span>
            </Link>
            <Link to="/" onClick={onNavegar} className={CLASE_ENLACE_SITIO}>
              <Icon path={ICON_PATHS.home} className="h-[18px] w-[18px] shrink-0" />
              <span>Volver al inicio</span>
            </Link>
          </nav>
        </div>
      </div>

      {/* Tarjeta del usuario al pie, como en la referencia */}
      <div className="flex shrink-0 items-center gap-3 border-t border-beige p-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent to-accent-soft text-xs font-bold text-paper">
          {inicialesUsuario(usuario)}
        </span>
        <div className="min-w-0 flex-1 leading-tight">
          <p className="truncate text-sm font-semibold text-primary">{nombreParaSaludar(usuario)}</p>
          <p className="truncate text-xs text-primary/55">{ETIQUETA_ROL[usuario.rol] || "Usuario"}</p>
        </div>
        <button
          type="button"
          onClick={onCerrarSesion}
          aria-label="Cerrar sesión"
          title="Cerrar sesión"
          className="rounded-lg p-2 text-primary/60 transition-colors hover:bg-peligro hover:text-peligro-fuerte"
        >
          <Icon path={ICON_PATHS.logout} className="h-[18px] w-[18px]" />
        </button>
      </div>
    </div>
  );
}

function Panel() {
  useDocumentTitle("Panel de Control", "Panel privado de gestión de Dulce Esencia Pastelería.", "/panel", true);

  const { usuario, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [oscuro, alternarTema] = useDarkMode();
  const [menuAbierto, setMenuAbierto] = useState(false);

  // Escape cierra el drawer móvil.
  useEffect(() => {
    if (!menuAbierto) return undefined;
    const alTeclear = (evento) => {
      if (evento.key === "Escape") setMenuAbierto(false);
    };
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [menuAbierto]);

  if (!usuario) return null;

  const pestañas = pestañasParaRol(usuario.rol);
  const grupos = gruposSidebar(usuario.rol);

  const cerrarSesion = async () => {
    await logout();
    navigate("/");
  };

  const seccionActual =
    pestañas.find((p) => (p.end ? location.pathname === p.to : location.pathname.startsWith(p.to))) || pestañas[0];
  const esInicio = seccionActual?.to === "/panel";

  const fecha = new Date().toLocaleDateString("es-CO", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="min-h-screen bg-section lg:grid lg:grid-cols-[16.5rem_minmax(0,1fr)]">
      {/* SIDEBAR DE ESCRITORIO */}
      <aside className="sticky top-0 hidden h-screen border-r border-beige bg-cream lg:block">
        <SidebarContenido
          grupos={grupos}
          usuario={usuario}
          onNavegar={undefined}
          onCerrarSesion={cerrarSesion}
        />
      </aside>

      {/* DRAWER MÓVIL */}
      {menuAbierto && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menú del panel">
          <button
            type="button"
            aria-label="Cerrar menú"
            onClick={() => setMenuAbierto(false)}
            className="absolute inset-0 bg-primary-dark/50"
          />
          <aside className="relative h-full w-72 max-w-[85%] border-r border-beige bg-cream shadow-elevada">
            <SidebarContenido
              grupos={grupos}
              usuario={usuario}
              onNavegar={() => setMenuAbierto(false)}
              onCerrarSesion={cerrarSesion}
            />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-col">
        {/* BARRA SUPERIOR */}
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-beige bg-cream/90 px-4 backdrop-blur sm:px-8">
          <button
            type="button"
            onClick={() => setMenuAbierto(true)}
            aria-label="Abrir menú del panel"
            aria-expanded={menuAbierto}
            className="-ml-2 rounded-lg p-2 text-primary lg:hidden"
          >
            <Icon path={ICON_PATHS.menu} className="h-6 w-6" />
          </button>

          <nav aria-label="Ruta actual" className="flex min-w-0 items-center gap-2 text-sm">
            <Link to="/panel" className="text-primary/55 transition-colors hover:text-primary">
              Panel
            </Link>
            <Icon path={ICON_PATHS.chevronRight} className="h-3 w-3 shrink-0 text-primary/40" />
            <span className="truncate font-semibold text-primary" aria-current="page">
              {seccionActual?.label}
            </span>
          </nav>

          <div className="ml-auto flex items-center gap-1.5">
            <Link
              to="/tienda"
              className="hidden items-center gap-2 rounded-lg border border-beige bg-cream px-3 py-1.5 text-sm font-medium text-primary/80 transition-colors hover:bg-section hover:text-primary sm:inline-flex"
            >
              <Icon path={ICON_PATHS.cart} className="h-4 w-4" />
              <span>Ir a la tienda</span>
            </Link>
            <button
              type="button"
              onClick={alternarTema}
              aria-label={oscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
              className="rounded-lg p-2 text-primary/70 transition-colors hover:bg-section hover:text-primary"
            >
              <Icon path={oscuro ? ICON_PATHS.sun : ICON_PATHS.moon} className="h-5 w-5" />
            </button>
            <span
              title={usuario.correo}
              className="ml-1 flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-accent to-accent-soft text-xs font-bold text-paper"
            >
              {inicialesUsuario(usuario)}
            </span>
          </div>
        </header>

        {/* CONTENIDO */}
        <div className="panel-area flex-1 px-4 py-8 sm:px-8">
          <div className="mx-auto max-w-6xl">
            <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs font-medium tracking-wide text-primary/55 first-letter:uppercase">{fecha}</p>
                <h1 className="mt-1.5 font-display text-3xl font-bold tracking-tight text-primary sm:text-4xl">
                  {esInicio ? (
                    <>
                      {saludoSegunHora()},{" "}
                      <span className="text-accent dark:text-accent-soft">{nombreParaSaludar(usuario)}</span>
                    </>
                  ) : (
                    seccionActual?.label
                  )}
                </h1>
                <p className="mt-2 max-w-xl text-sm leading-relaxed text-primary/70">{seccionActual?.desc}</p>
              </div>
              <span
                className={`self-start rounded-full px-3 py-1 text-xs font-semibold sm:self-auto ${
                  BADGE_ROL[usuario.rol] || "bg-beige/40 text-primary"
                }`}
              >
                {ETIQUETA_ROL[usuario.rol] || "Usuario"}
              </span>
            </div>

            <div className="min-w-0">
              <Outlet />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Panel;
