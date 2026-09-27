import { useEffect } from "react";
import Icon from "./Icon";
import ICON_PATHS from "./iconPaths";

/**
 * Modal reutilizable. Se cierra al hacer clic fuera del panel,
 * al presionar Escape, o al hacer clic en el botón de cerrar,
 * sin exigir que el usuario complete el formulario que contiene.
 */
function Modal({ isOpen, onClose, title, children }) {
  useEffect(() => {
    if (!isOpen) return;

    const manejarTeclado = (evento) => {
      if (evento.key === "Escape") onClose();
    };

    document.addEventListener("keydown", manejarTeclado);
    const overflowOriginal = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", manejarTeclado);
      document.body.style.overflow = overflowOriginal;
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-primary/60 p-4 backdrop-blur-sm"
      onClick={onClose}
      role="presentation"
    >
      {/* Panel del modal: patrón ARIA "dialog" estándar (div + role="dialog"
          + aria-modal). El onClick solo detiene la propagación del click
          hacia el fondo (para no cerrar el modal al hacer clic dentro),
          no es una interacción que deba anunciarse por teclado; el cierre
          por teclado ya lo cubre el propio Modal con la tecla Escape
          (ver el useEffect de arriba). Se evaluó usar el elemento nativo
          <dialog>, pero requeriría reimplementar el open/close (showModal/
          close) y el manejo de Escape que este componente ya hace a mano,
          así que se mantiene el patrón con role="dialog". */}
      {/* oxlint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions -- ver comentario arriba: solo detiene la propagación del click, no es una interacción con teclado pendiente */}
      <div
        className="animate-fade-in-up max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-cream shadow-2xl"
        onClick={(evento) => evento.stopPropagation()}
        // oxlint-disable-next-line jsx-a11y/prefer-tag-over-role -- ver comentario arriba: se evaluó <dialog> nativo y no aplica aquí
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <div className="flex items-center justify-between border-b border-beige/50 px-6 py-4">
          <h2 id="modal-title" className="text-lg font-semibold text-primary">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="rounded-full p-1.5 text-primary/40 transition hover:bg-section hover:text-primary"
          >
            <Icon path={ICON_PATHS.close} />
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}

export default Modal;
