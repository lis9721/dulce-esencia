import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import logo from "../assets/images/logo1.webp";
import Icon from "./ui/Icon";
import ICON_PATHS from "./ui/iconPaths";
import UserMenu from "./UserMenu";
import { useAuth } from "../hooks/useAuth";
import { useCart } from "../hooks/useCart";
import useDarkMode from "../hooks/useDarkMode";
import ENLACES from "../constants/enlacesNav";

function claseEnlace({ isActive }) {
  return `border-b-2 pb-1 text-sm font-medium transition-colors ${
    isActive
      ? "border-blush text-primary"
      : "border-transparent text-primary/70 hover:border-blush hover:text-primary"
  }`;
}

function Header() {
  const [menuAbierto, setMenuAbierto] = useState(false);
  const { isAuthenticated, usuario, logout } = useAuth();
  const { cantidadTotal } = useCart();
  const [oscuro, alternarTema] = useDarkMode();
  const navigate = useNavigate();

  // Con el header ahora fijo (sticky) arriba, esta sombra un poco más
  // marcada aparece solo cuando ya hay contenido desplazado detrás, para
  // distinguir el header "en reposo" (arriba del todo) del header ya
  // pegado durante el scroll. Puro detalle visual: no afecta el layout.
  const [conScroll, setConScroll] = useState(false);
  useEffect(() => {
    const alScrollear = () => setConScroll(window.scrollY > 8);
    alScrollear();
    window.addEventListener("scroll", alScrollear, { passive: true });
    return () => window.removeEventListener("scroll", alScrollear);
  }, []);

  const cerrarSesion = async () => {
    // logout() ahora es async: llama al backend para borrar la cookie
    // httpOnly de sesión antes de limpiar el estado local.
    await logout();
    setMenuAbierto(false);
    navigate("/");
  };

  return (
    <header
      className={`sticky top-0 z-40 border-b bg-cream transition-colors duration-200 ${
        conScroll ? "border-champagne" : "border-transparent"
      }`}
    >
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6">
        <NavLink
          to="/"
          className="flex items-center transition-transform duration-200 hover:scale-105"
          onClick={() => setMenuAbierto(false)}
        >
          <img src={logo} alt="Dulce Esencia Pastelería" width={50} height={56} className="h-14 w-auto" />
        </NavLink>

        {/* Navegación de escritorio */}
        <nav className="hidden items-center gap-6 md:flex">
          {ENLACES.map((enlace) => (
            <NavLink key={enlace.to} to={enlace.to} end={enlace.end} className={claseEnlace}>
              {enlace.label}
            </NavLink>
          ))}

          {/* Ícono de carrito con badge: visible con o sin sesión, ya
              que un invitado también puede armar y revisar su carrito
              (localStorage) sin loguearse — ver CartContext.jsx. */}
          <NavLink
            to="/carrito"
            aria-label={`Ver carrito${cantidadTotal > 0 ? ` (${cantidadTotal} productos)` : ""}`}
            className="relative rounded-full p-2 text-primary transition-transform duration-200 hover:scale-110 hover:bg-section"
          >
            <Icon path={ICON_PATHS.cart} className="h-6 w-6" />
            {cantidadTotal > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1 text-[11px] font-bold text-paper">
                {cantidadTotal > 99 ? "99+" : cantidadTotal}
              </span>
            )}
          </NavLink>

          <button
            type="button"
            onClick={alternarTema}
            aria-label={oscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
            className="rounded-full p-2 text-primary transition-transform duration-200 hover:scale-110 hover:bg-section"
          >
            <Icon path={oscuro ? ICON_PATHS.sun : ICON_PATHS.moon} className="h-5 w-5" />
          </button>

          {isAuthenticated ? (
            <UserMenu usuario={usuario} onCerrarSesion={cerrarSesion} />
          ) : (
            <NavLink
              to="/login"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-cream transition-all duration-200 hover:scale-105 hover:bg-primary-dark hover:shadow-md"
            >
              Iniciar sesión
            </NavLink>
          )}
        </nav>

        {/* Ícono de carrito + botón de menú móvil: el carrito queda
            siempre visible en la barra compacta de móvil (no dentro
            del menú desplegable), igual que en cualquier tienda. */}
        <div className="flex items-center gap-1 md:hidden">
          <NavLink
            to="/carrito"
            onClick={() => setMenuAbierto(false)}
            aria-label={`Ver carrito${cantidadTotal > 0 ? ` (${cantidadTotal} productos)` : ""}`}
            className="relative rounded-full p-2 text-primary transition-transform duration-200 active:scale-90"
          >
            <Icon path={ICON_PATHS.cart} className="h-6 w-6" />
            {cantidadTotal > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1 text-[11px] font-bold text-paper">
                {cantidadTotal > 99 ? "99+" : cantidadTotal}
              </span>
            )}
          </NavLink>

          <button
            type="button"
            onClick={alternarTema}
            aria-label={oscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
            className="rounded-full p-2 text-primary transition-transform duration-200 active:scale-90"
          >
            <Icon path={oscuro ? ICON_PATHS.sun : ICON_PATHS.moon} className="h-5 w-5" />
          </button>

          <button
            type="button"
            onClick={() => setMenuAbierto((prev) => !prev)}
            aria-label="Abrir menú"
            aria-expanded={menuAbierto}
            className="rounded-md p-2 text-primary transition-transform duration-200 active:scale-90"
          >
            <Icon path={menuAbierto ? ICON_PATHS.close : ICON_PATHS.menu} className="h-6 w-6" />
          </button>
        </div>
      </div>

      {/* Navegación móvil */}
      {menuAbierto && (
        <nav className="animate-fade-in-up flex flex-col gap-1 border-t border-beige/60 bg-cream px-4 pb-4 md:hidden">
          {ENLACES.map((enlace) => (
            <NavLink
              key={enlace.to}
              to={enlace.to}
              end={enlace.end}
              onClick={() => setMenuAbierto(false)}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm font-medium ${
                  isActive ? "bg-blush/40 text-ink" : "text-primary/70 hover:bg-beige/20"
                }`
              }
            >
              {enlace.label}
            </NavLink>
          ))}

          {isAuthenticated ? (
            <div className="mt-2 rounded-lg border border-beige/60 p-2">
              <p className="px-1 pb-1 text-xs font-semibold uppercase tracking-wide text-primary/40">
                Mi cuenta
              </p>
              <NavLink
                to="/panel"
                onClick={() => setMenuAbierto(false)}
                className="block rounded-md px-2 py-2 text-sm font-medium text-primary/70 hover:bg-beige/20"
              >
                Mi panel ({usuario?.rol})
              </NavLink>
              <button
                type="button"
                onClick={cerrarSesion}
                className="mt-1 block w-full rounded-md px-2 py-2 text-left text-sm font-semibold text-peligro-fuerte hover:bg-peligro dark:text-peligro-fuerte dark:hover:bg-peligro"
              >
                Cerrar sesión
              </button>
            </div>
          ) : (
            <NavLink
              to="/login"
              onClick={() => setMenuAbierto(false)}
              className="mt-2 rounded-lg bg-primary px-3 py-2 text-center text-sm font-semibold text-cream hover:bg-primary-dark"
            >
              Iniciar sesión
            </NavLink>
          )}
        </nav>
      )}
    </header>
  );
}

export default Header;
