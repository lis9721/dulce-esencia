import { useState } from "react";
import Icon from "./Icon";
import ICON_PATHS from "./iconPaths";

/**
 * Campo de texto reutilizable con etiqueta y mensaje de error.
 * El error solo se muestra si el campo ya fue "tocado" (touched),
 * evitando mostrar validaciones antes de que el usuario interactúe.
 *
 * Cuando se recibe `maxLength`, además se muestra un contador de
 * caracteres ("12/60") junto a la etiqueta, para que el usuario sepa
 * de antemano cuánto puede escribir sin tener que adivinarlo o
 * enterarse recién al topar el límite.
 *
 * Cuando `type="password"`, se agrega un botón de "ojo" para
 * mostrar/ocultar la contraseña en texto plano. El estado es interno
 * (no se expone al padre): al tocar el ojo solo cambia el atributo
 * `type` real del input entre "password" y "text".
 */
function Input({
  label,
  name,
  type = "text",
  value,
  onChange,
  onBlur,
  error,
  touched,
  placeholder,
  maxLength,
  min,
  max,
  required = false,
  autoComplete,
}) {
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const esPassword = type === "password";
  const tipoReal = esPassword && mostrarPassword ? "text" : type;
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

      <div className="relative">
        <input
          id={name}
          name={name}
          type={tipoReal}
          value={value}
          onChange={onChange}
          onBlur={onBlur}
          placeholder={placeholder}
          maxLength={maxLength}
          min={min}
          max={max}
          autoComplete={autoComplete}
          aria-invalid={tieneError}
          aria-describedby={
            tieneError ? `${name}-error` : tieneContador ? `${name}-contador` : undefined
          }
          className={`w-full rounded-lg border bg-cream px-3 py-2 text-sm text-primary outline-none transition focus:ring-2 ${
            esPassword ? "pr-10" : ""
          } ${
            tieneError
              ? "border-peligro-fuerte focus:border-peligro-fuerte focus:ring-peligro"
              : "border-beige focus:border-primary focus:ring-primary/20"
          }`}
        />
        {esPassword && (
          <button
            type="button"
            onClick={() => setMostrarPassword((actual) => !actual)}
            aria-label={mostrarPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
            aria-pressed={mostrarPassword}
            tabIndex={-1}
            className="absolute inset-y-0 right-0 flex items-center px-3 text-primary/50 hover:text-primary"
          >
            <Icon path={mostrarPassword ? ICON_PATHS.eyeOff : ICON_PATHS.eye} className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Anuncio accesible del conteo para lectores de pantalla, ya que
          el contador visual arriba tiene aria-hidden. */}
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

export default Input;
