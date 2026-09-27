/**
 * Área de texto reutilizable con etiqueta, mensaje de error y contador
 * de caracteres. Hermano de Input.jsx: mismo look & feel y misma
 * lógica de contador, pero para textos largos (ej. el mensaje del
 * formulario de contacto).
 */
function Textarea({
  label,
  name,
  value,
  onChange,
  onBlur,
  error,
  touched,
  placeholder,
  maxLength,
  required = false,
  rows = 4,
}) {
  const tieneError = Boolean(touched && error);
  const tieneContador = typeof maxLength === "number" && maxLength > 0;
  const longitudActual = (value ?? "").toString().length;
  const cercaDelLimite = tieneContador && longitudActual >= maxLength * 0.9;

  return (
    <div className="flex flex-col gap-1">
      {(label || tieneContador) && (
        <div className="flex items-baseline justify-between gap-2">
          {label && (
            <label htmlFor={name} className="text-sm font-medium text-primary/80">
              {label} {required && <span className="text-primary">*</span>}
            </label>
          )}
          {tieneContador && (
            <span
              className={`shrink-0 text-xs tabular-nums ${
                cercaDelLimite ? "text-aviso-fuerte" : "text-primary/40"
              }`}
              aria-hidden="true"
            >
              {longitudActual}/{maxLength}
            </span>
          )}
        </div>
      )}

      <textarea
        id={name}
        name={name}
        rows={rows}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        placeholder={placeholder}
        maxLength={maxLength}
        aria-invalid={tieneError}
        aria-describedby={
          tieneError ? `${name}-error` : tieneContador ? `${name}-contador` : undefined
        }
        className={`w-full rounded-lg border bg-cream px-3 py-2 text-sm text-primary outline-none transition focus:ring-2 ${
          tieneError
            ? "border-peligro-fuerte focus:border-peligro-fuerte focus:ring-peligro"
            : "border-beige focus:border-primary focus:ring-primary/20"
        }`}
      />

      {tieneContador && (
        <span id={`${name}-contador`} className="sr-only">
          {longitudActual} de {maxLength} caracteres usados
        </span>
      )}

      {tieneError && (
        <p id={`${name}-error`} className="text-xs text-peligro-fuerte">
          {error}
        </p>
      )}
    </div>
  );
}

export default Textarea;
