import { useEffect, useRef, useState } from "react";

/**
 * Envuelve cualquier sección para que aparezca con un fade + slide-up
 * al entrar en el viewport, y se desvanezca de nuevo al salir de él —
 * en cualquier dirección de scroll (bajando o subiendo) —, en vez de
 * mostrarse todo de golpe y quedarse así para siempre. Solo usa
 * IntersectionObserver (sin librerías nuevas).
 */
function Reveal({ children, className = "" }) {
  const refElemento = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const nodo = refElemento.current;
    if (!nodo) return undefined;

    const observador = new IntersectionObserver(
      ([entrada]) => setVisible(entrada.isIntersecting),
      // rootMargin negativo: dispara el fade un poco antes de que la
      // sección toque el borde exacto de la pantalla (arriba o abajo),
      // para que la transición se sienta más suave.
      { threshold: 0.15, rootMargin: "-10% 0px -10% 0px" }
    );

    observador.observe(nodo);
    return () => observador.disconnect();
  }, []);

  return (
    <div ref={refElemento} className={`reveal ${visible ? "reveal-visible" : ""} ${className}`}>
      {children}
    </div>
  );
}

export default Reveal;
