/**
 * Selector reutilizable (por ejemplo, para el tipo de documento).
 */
function Select({
  label,
  name,
  value,
  onChange,
  onBlur,
  error,
  touched,
  options,
  required = false,
  placeholder = "Selecciona una opción",
}) {
  const tieneError = Boolean(touched && error);

  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label htmlFor={name} className="text-sm font-medium text-primary/80">
          {label} {required && <span className="text-primary">*</span>}
        </label>
      )}

      <select
        id={name}
        name={name}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        aria-invalid={tieneError}
        aria-describedby={tieneError ? `${name}-error` : undefined}
        className={`rounded-lg border bg-cream px-3 py-2 text-sm text-primary outline-none transition focus:ring-2 ${
          tieneError
            ? "border-peligro-fuerte focus:border-peligro-fuerte focus:ring-peligro"
            : "border-beige focus:border-primary focus:ring-primary/20"
        }`}
      >
        <option value="">{placeholder}</option>
        {options.map((opcion) => (
          <option key={opcion.value} value={opcion.value}>
            {opcion.label}
          </option>
        ))}
      </select>

      {tieneError && (
        <p id={`${name}-error`} className="text-xs text-peligro-fuerte">
          {error}
        </p>
      )}
    </div>
  );
}

export default Select;
