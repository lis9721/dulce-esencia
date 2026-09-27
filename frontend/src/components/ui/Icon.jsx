/**
 * Envoltorio base para los iconos SVG de la interfaz.
 * Antes cada componente (Header, Modal, Carousel, RecoverPassword)
 * repetía el mismo <svg xmlns... viewBox... stroke...>; ahora solo
 * se pasa el "path" del icono que se necesita (ver iconPaths.js).
 */
function Icon({ path, className = "h-5 w-5" }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
      className={className}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d={path} />
    </svg>
  );
}

export default Icon;
