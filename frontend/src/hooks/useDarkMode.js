import { useCallback, useEffect, useState } from "react";

const CLAVE_STORAGE = "essentia-theme";

/**
 * Lee el estado YA resuelto por el script inline de index.html (que
 * corre antes de este componente montar, para evitar el flash de tema
 * equivocado). Acá solo lo reflejamos en el state de React, no lo
 * recalculamos — la clase en <html> es la fuente de verdad inicial.
 */
function leerEstadoInicial() {
  if (typeof document === "undefined") return false;
  return document.documentElement.classList.contains("dark");
}

/**
 * Modo oscuro con persistencia en localStorage y clase .dark en
 * <html> (ver el `@custom-variant dark` de index.css: los `dark:` de
 * Tailwind dependen de esta clase, no de prefers-color-scheme, para
 * que el toggle manual del Header mande por encima del tema del SO).
 */
export default function useDarkMode() {
  const [oscuro, setOscuro] = useState(leerEstadoInicial);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", oscuro);
    try {
      localStorage.setItem(CLAVE_STORAGE, oscuro ? "dark" : "light");
    } catch {
      // localStorage puede fallar (modo privado, cuota llena, etc.):
      // el tema igual se aplica para esta sesión, solo no persiste.
    }
  }, [oscuro]);

  const alternar = useCallback(() => setOscuro((valorActual) => !valorActual), []);

  return [oscuro, alternar];
}
