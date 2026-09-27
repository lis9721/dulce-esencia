/**
 * Botón reutilizable con distintas variantes visuales.
 * Se usa en Login, RecoverPassword, RegisterModal y demás formularios.
 */
function Button({
  children,
  type = "button",
  variant = "primary",
  fullWidth = false,
  disabled = false,
  onClick,
  className = "",
}) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all duration-200 hover:scale-[1.03] hover:shadow-md active:scale-[0.97] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:scale-100 disabled:hover:shadow-none";

  const variants = {
    primary:
      "bg-primary text-cream hover:bg-primary-dark focus-visible:outline-primary",
    // Rosa empolvado con tinta fija (text-ink, no text-primary): el
    // fondo sigue siendo claro incluso en modo oscuro, así que la
    // tinta también debe quedarse oscura siempre — text-primary se
    // volvería clara en modo oscuro y perdería contraste acá.
    blush:
      "bg-blush text-ink hover:bg-blush-dark focus-visible:outline-primary",
    // Lila de marca: para llamados a la acción que quieren sentirse más
    // vivos (newsletter, CTAs destacados). text-paper (no text-ink): el
    // accent de esta paleta es un lila medio-oscuro — el texto oscuro
    // solo da ~2.9:1, por debajo del mínimo WCAG de 4.5:1; el texto
    // claro fijo sí cumple (~4.8:1).
    accent:
      "bg-accent text-paper hover:bg-accent-dark focus-visible:outline-accent",
    secondary:
      "border border-primary text-primary hover:bg-primary/5 focus-visible:outline-primary",
    ghost:
      "text-primary hover:bg-primary/5 focus-visible:outline-primary",
    // Para acciones destructivas (eliminar producto/usuario) dentro de
    // ConfirmModal: mismo lenguaje visual que el resto de botones, pero
    // en rojo para dejar claro que la acción no se puede deshacer.
    // text-paper (no text-cream): el rojo es un color fijo que no
    // cambia con el tema, así que el texto también debe quedarse claro
    // siempre.
    danger:
      "bg-peligro-solido text-paper hover:bg-peligro-solido-dark focus-visible:outline-peligro-solido",
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${variants[variant]} ${fullWidth ? "w-full" : ""} ${className}`}
    >
      {children}
    </button>
  );
}

export default Button;
