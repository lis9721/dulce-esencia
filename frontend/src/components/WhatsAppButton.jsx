/**
 * WhatsAppButton
 *
 * Botón flotante y reutilizable que abre una conversación de WhatsApp
 * con el número de contacto de Dulce Esencia. Se monta una sola vez en
 * App.jsx (fuera de <Routes>, junto al Header/Footer) para que quede
 * visible en TODAS las páginas del sitio, siempre en la misma
 * posición fija de la pantalla.
 *
 * Requisito del tercer avance (punto 15): reutilizable, fijo, con el
 * enlace correcto de WhatsApp, accesible, y visualmente coherente con
 * el resto del diseño (colores del proyecto, no el verde genérico de
 * WhatsApp a secas).
 */

// Mismo número que se muestra en la página de Contacto ("+57 300 000
// 0000"), pero en formato internacional SIN espacios ni símbolos, que
// es lo que exige la URL de wa.me. Cambia SOLO esta constante para
// apuntar el botón a un número real.
const TELEFONO_WHATSAPP = "573127231307";

const MENSAJE_PREDETERMINADO = "Hola, quiero más información sobre los productos de Dulce Esencia Pastelería.";

function WhatsAppButton() {
  const enlace = `https://wa.me/${TELEFONO_WHATSAPP}?text=${encodeURIComponent(MENSAJE_PREDETERMINADO)}`;

  return (
    <a
      href={enlace}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Escríbenos por WhatsApp"
      title="Escríbenos por WhatsApp"
      className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-cream shadow-lg transition-transform duration-200 hover:scale-110 hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2"
    >
      {/* Glifo oficial de WhatsApp (relleno, no outline): se deja como
          SVG propio en vez de usar el <Icon> genérico del proyecto,
          porque ese componente está pensado para íconos de trazo
          (stroke) y este logo necesita ser un ícono sólido (fill) para
          seguir siendo reconocible. */}
      <svg viewBox="0 0 32 32" className="h-7 w-7" fill="currentColor" aria-hidden="true">
        <path d="M16.02 3C9.4 3 4 8.37 4 15c0 2.2.6 4.27 1.63 6.05L4 29l8.17-2.14A11.94 11.94 0 0 0 16.02 27C22.63 27 28 21.63 28 15S22.63 3 16.02 3Zm0 21.8c-1.9 0-3.68-.5-5.23-1.44l-.37-.22-4.85 1.27 1.3-4.73-.24-.39A9.7 9.7 0 0 1 5.2 15c0-5.96 4.86-10.8 10.82-10.8 5.96 0 10.8 4.84 10.8 10.8s-4.84 10.8-10.8 10.8Zm5.93-8.1c-.32-.16-1.9-.94-2.2-1.05-.3-.11-.51-.16-.73.16-.21.32-.84 1.05-1.03 1.26-.19.21-.38.24-.7.08-.32-.16-1.35-.5-2.57-1.6-.95-.85-1.59-1.89-1.78-2.21-.19-.32-.02-.49.14-.65.14-.14.32-.38.48-.56.16-.19.21-.32.32-.53.11-.21.05-.4-.03-.56-.08-.16-.73-1.76-1-2.41-.26-.63-.53-.55-.73-.56h-.62c-.21 0-.56.08-.85.4-.29.32-1.12 1.09-1.12 2.66s1.15 3.09 1.31 3.31c.16.21 2.26 3.45 5.48 4.84.77.33 1.37.53 1.84.68.77.24 1.47.21 2.02.13.62-.09 1.9-.78 2.17-1.53.27-.75.27-1.4.19-1.53-.08-.13-.29-.21-.61-.37Z" />
      </svg>
    </a>
  );
}

export default WhatsAppButton;
