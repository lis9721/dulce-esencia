import { useState } from "react";
import { NavLink } from "react-router-dom";
import logo from "../assets/images/logo1.webp";
import Icon from "./ui/Icon";
import ICON_PATHS from "./ui/iconPaths";
import { useAuth } from "../hooks/useAuth";
import ENLACES from "../constants/enlacesNav";

// Redes sociales de la marca. Las URLs son un placeholder: cámbialas por
// las cuentas reales de Dulce Esencia cuando existan (mismo criterio que el
// número de WhatsApp en components/WhatsAppButton.jsx).
const REDES = [
  { nombre: "Instagram", href: "https://instagram.com/dulceesencia", icono: ICON_PATHS.instagram },
  { nombre: "Facebook", href: "https://facebook.com/dulceesencia", icono: ICON_PATHS.facebook },
  { nombre: "TikTok", href: "https://tiktok.com/@dulceesencia", icono: ICON_PATHS.tiktok },
];

function TituloColumna({ children }) {
  return <h3 className="text-sm font-medium text-paper">{children}</h3>;
}

/**
 * Footer: fondo Ink FIJO (--color-ink, --color-paper), independiente
 * del tema claro/oscuro del resto del sitio, como una base oscura y
 * estable bajo el resto de la página. Antes usaba
 * `bg-primary text-cream`, que se invierte en modo oscuro (--color-
 * primary se vuelve claro) — con eso el footer terminaba con fondo
 * claro en modo oscuro, justo lo contrario de lo que se buscaba.
 */
function Footer() {
  const { isAuthenticated } = useAuth();
  const anioActual = new Date().getFullYear();
  const [correo, setCorreo] = useState("");
  const [enviado, setEnviado] = useState(false);

  const handleSuscripcion = (evento) => {
    evento.preventDefault();
    if (!correo.trim()) return;
    // Placeholder: aún no hay un endpoint de newsletter en el backend.
    // Cuando exista, este handler llama a la API en vez de solo marcar
    // "enviado" localmente.
    setEnviado(true);
    setCorreo("");
  };

  return (
    <footer className="mt-auto bg-ink text-paper">
      <div className="mx-auto grid max-w-5xl gap-10 px-4 py-12 sm:grid-cols-2 sm:px-6 md:grid-cols-4">
        {/* Marca + redes */}
        <div className="flex flex-col gap-3 sm:col-span-2 md:col-span-1">
          <div className="flex items-center gap-2">
            <img src={logo} alt="Dulce Esencia Pastelería" className="h-8 w-8 rounded-full object-cover" />
            <span className="font-display text-lg font-medium italic text-paper">Dulce Esencia</span>
          </div>
          <p className="max-w-xs text-sm text-paper/60">
            Pastelería artesanal: tortas, cupcakes, galletas y panes
            horneados cada día en Medellín.
          </p>
          <div className="mt-1 flex gap-2">
            {REDES.map((red) => (
              <a
                key={red.nombre}
                href={red.href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`Síguenos en ${red.nombre}`}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-paper/20 text-paper/70 transition-colors duration-200 hover:border-paper/40 hover:text-paper"
              >
                <Icon path={red.icono} className="h-4 w-4" />
              </a>
            ))}
          </div>
        </div>

        {/* Enlaces */}
        <div className="flex flex-col gap-3">
          <TituloColumna>Tienda</TituloColumna>
          <nav className="flex flex-col gap-2 text-sm">
            {ENLACES.map((enlace) => (
              <NavLink
                key={enlace.to}
                to={enlace.to}
                end={enlace.end}
                className="w-fit text-paper/60 transition-colors hover:text-paper"
              >
                {enlace.label}
              </NavLink>
            ))}
            <NavLink
              to={isAuthenticated ? "/panel" : "/login"}
              className="w-fit text-paper/60 transition-colors hover:text-paper"
            >
              {isAuthenticated ? "Mi panel" : "Iniciar sesión"}
            </NavLink>
          </nav>
        </div>

        {/* Atención al cliente */}
        <div className="flex flex-col gap-3">
          <TituloColumna>Ayuda</TituloColumna>
          <ul className="flex flex-col gap-2 text-sm text-paper/60">
            <li>contacto@dulceesencia.com</li>
            <li>+57 300 000 0000</li>
            <li>Pastelería Dulce Esencia, Medellín, Colombia</li>
            {/* Horario de referencia: confirmar con el dato real del negocio */}
            <li>Lun. – sáb. · 9:00 a. m. – 7:00 p. m.</li>
          </ul>
        </div>

        {/* Newsletter — reemplaza el bloque "Por qué elegirnos" (ya
            cubierto por la sección de Beneficios en Index.jsx) por algo
            accionable, con el botón de esquina cortada del hero. */}
        <div className="flex flex-col gap-3">
          <TituloColumna>Novedades por correo</TituloColumna>
          {enviado ? (
            <p className="text-sm text-paper/70">Gracias por suscribirte.</p>
          ) : (
            <form onSubmit={handleSuscripcion} className="flex border-b border-sage pb-2">
              <input
                type="email"
                required
                value={correo}
                onChange={(evento) => setCorreo(evento.target.value)}
                placeholder="nombre@correo.com"
                aria-label="Correo electrónico"
                className="min-w-0 flex-1 bg-transparent text-sm text-paper placeholder:text-paper/40 focus:outline-none"
              />
              <button
                type="submit"
                className="ml-2 bg-accent px-3 py-1.5 text-xs font-semibold text-paper transition-colors duration-200 hover:bg-accent-dark"
                style={{
                  clipPath: "polygon(0 0, 100% 0, 100% 100%, 6px 100%, 0 calc(100% - 6px))",
                }}
              >
                Unirme
              </button>
            </form>
          )}
        </div>
      </div>

      <div className="border-t border-paper/10 px-4 py-4 sm:px-6">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 text-xs text-paper/50">
          <p>
            © {anioActual} Dulce Esencia Pastelería. Medellín, Colombia.
          </p>
          <p>Proyecto React + Vite — Actividad práctica ADSO, Ficha 3406211</p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
