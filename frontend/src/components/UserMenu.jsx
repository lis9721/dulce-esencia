import { useEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";
import Icon from "./ui/Icon";
import ICON_PATHS from "./ui/iconPaths";

/**
 * Iniciales del usuario para el avatar del menú de cuenta
 * (ej. "Laura Gómez" -> "LG").
 * Usa nombre + apellido, que vienen tanto en la respuesta de /login como
 * en /usuarios/perfil (con la que AuthProvider recupera la sesión al
 * recargar la página). El correo queda como respaldo por si alguno
 * faltara.
 */
function iniciales(usuario) {
  const inicialNombre = usuario?.nombre?.trim()?.[0];
  const inicialApellido = usuario?.apellido?.trim()?.[0];

  if (inicialNombre && inicialApellido) {
    return `${inicialNombre}${inicialApellido}`.toUpperCase();
  }
  if (inicialNombre) {
    return inicialNombre.toUpperCase();
  }

  const base = usuario?.correo || "";
  return base.slice(0, 2).toUpperCase();
}

/**
 * UserMenu
 *
 * Menú de cuenta desplegable de la navegación de escritorio: agrupa
 * "Mi panel" y "Cerrar sesión" dentro de un único control con la
 * identidad del usuario (avatar + nombre), en vez de mostrarlos como dos
 * elementos sueltos uno junto al otro en la barra (como antes). Se cierra
 * al hacer clic afuera, con Escape, o al elegir una opción.
 *
 * Solo se usa en la navegación de escritorio de Header.jsx: el menú
 * móvil ya es, de por sí, una lista vertical desplegada, así que ahí
 * basta con agrupar visualmente esas mismas dos opciones bajo un rótulo
 * "Mi cuenta" (ver Header.jsx), sin necesitar este mismo patrón de
 * dropdown.
 */
function UserMenu({ usuario, onCerrarSesion }) {
  const [abierto, setAbierto] = useState(false);
  const contenedorRef = useRef(null);

  useEffect(() => {
    if (!abierto) return undefined;

    function alClicAfuera(evento) {
      if (contenedorRef.current && !contenedorRef.current.contains(evento.target)) {
        setAbierto(false);
      }
    }
    function alPresionarTecla(evento) {
      if (evento.key === "Escape") setAbierto(false);
    }

    document.addEventListener("mousedown", alClicAfuera);
    document.addEventListener("keydown", alPresionarTecla);
    return () => {
      document.removeEventListener("mousedown", alClicAfuera);
      document.removeEventListener("keydown", alPresionarTecla);
    };
  }, [abierto]);

  const cerrarYSalir = async () => {
    setAbierto(false);
    // onCerrarSesion (cerrarSesion en Header.jsx) ya se encarga de
    // llamar a logout() y navegar a "/" — este componente solo cierra
    // su propio dropdown antes de delegarle esa acción.
    await onCerrarSesion();
  };

  return (
    <div className="relative" ref={contenedorRef}>
      <button
        type="button"
        onClick={() => setAbierto((valor) => !valor)}
        aria-haspopup="menu"
        aria-expanded={abierto}
        className="flex items-center gap-2 rounded-lg border border-beige px-3 py-1.5 text-sm font-medium text-primary transition-all duration-200 hover:-translate-y-0.5 hover:bg-section hover:shadow-sm"
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-cream">
          {iniciales(usuario)}
        </span>
        {usuario?.nombre?.split(" ")[0] || "Mi cuenta"}
        <Icon
          path={ICON_PATHS.chevronDown}
          className={`h-4 w-4 opacity-60 transition-transform duration-200 ${abierto ? "rotate-180" : ""}`}
        />
      </button>

      {abierto && (
        <div
          role="menu"
          className="animate-fade-in-up absolute right-0 top-full mt-2 w-56 overflow-hidden rounded-xl border border-beige/70 bg-cream py-2 shadow-lg"
        >
          <div className="border-b border-beige/60 px-4 pb-2">
            <p className="truncate text-sm font-semibold text-primary">{usuario?.nombre}</p>
            <p className="truncate text-xs text-primary/70">{usuario?.correo}</p>
          </div>

          <NavLink
            to="/panel"
            role="menuitem"
            onClick={() => setAbierto(false)}
            className="mt-1 block px-4 py-2 text-sm text-primary/80 hover:bg-section"
          >
            Mi panel
          </NavLink>

          {/* Acción destructiva/irreversible dentro de la sesión: se
              resalta en rojo para separarla visualmente de la simple
              navegación ("Mi panel"), no por decoración. */}
          <button
            type="button"
            role="menuitem"
            onClick={cerrarYSalir}
            className="block w-full px-4 py-2 text-left text-sm font-medium text-peligro-fuerte hover:bg-peligro dark:text-peligro-fuerte dark:hover:bg-peligro"
          >
            Cerrar sesión
          </button>
        </div>
      )}
    </div>
  );
}

export default UserMenu;
