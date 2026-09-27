import { useCallback, useEffect, useRef, useState } from "react";
import Icon from "./ui/Icon";
import ICON_PATHS from "./ui/iconPaths";

const AUTOPLAY_MS = 4500;

/**
 * Carrusel tipo "coverflow" pensado para una landing page: en escritorio
 * se ven la tarjeta activa en el centro y un adelanto de la anterior/
 * siguiente a los lados; en móvil se ve una sola tarjeta a la vez.
 * Soporta autoplay (con pausa al interactuar), flechas, indicadores,
 * teclado y arrastre táctil/mouse (swipe).
 */
function Carousel({ items }) {
  const [indiceActual, setIndiceActual] = useState(0);
  const [pausado, setPausado] = useState(false);
  const arrastreRef = useRef({ activo: false, inicioX: 0, deltaX: 0 });
  const [arrastreX, setArrastreX] = useState(0);
  const contenedorRef = useRef(null);

  const total = items?.length ?? 0;

  const irA = useCallback(
    (indice) => {
      if (total === 0) return;
      setIndiceActual(((indice % total) + total) % total);
    },
    [total]
  );

  const siguiente = useCallback(() => irA(indiceActual + 1), [indiceActual, irA]);
  const anterior = useCallback(() => irA(indiceActual - 1), [indiceActual, irA]);

  // Autoplay: se pausa mientras el usuario pasa el mouse, arrastra o
  // acaba de interactuar con los controles.
  useEffect(() => {
    if (pausado || total <= 1) return undefined;
    const intervalo = setInterval(() => {
      setIndiceActual((prev) => (prev === total - 1 ? 0 : prev + 1));
    }, AUTOPLAY_MS);
    return () => clearInterval(intervalo);
  }, [pausado, total]);

  // Navegación con teclado cuando el carrusel tiene el foco.
  const handleKeyDown = (evento) => {
    if (evento.key === "ArrowLeft") anterior();
    if (evento.key === "ArrowRight") siguiente();
  };

  // --- Swipe (mouse y táctil) ---
  const iniciarArrastre = (clienteX) => {
    arrastreRef.current = { activo: true, inicioX: clienteX, deltaX: 0 };
    setPausado(true);
  };

  const moverArrastre = (clienteX) => {
    if (!arrastreRef.current.activo) return;
    const delta = clienteX - arrastreRef.current.inicioX;
    arrastreRef.current.deltaX = delta;
    setArrastreX(delta);
  };

  const finalizarArrastre = () => {
    if (!arrastreRef.current.activo) return;
    const UMBRAL = 45;
    if (arrastreRef.current.deltaX > UMBRAL) {
      anterior();
    } else if (arrastreRef.current.deltaX < -UMBRAL) {
      siguiente();
    }
    arrastreRef.current = { activo: false, inicioX: 0, deltaX: 0 };
    setArrastreX(0);
    setPausado(false);
  };

  if (!items || items.length === 0) return null;

  return (
    <div className="mx-auto w-full max-w-5xl">
      {/* Contenedor del carrusel: patrón ARIA "carousel" (role="region" +
          navegación por teclado en el propio contenedor). jsx-a11y marca
          tabIndex/eventos de teclado y mouse en elementos "no interactivos"
          como sospechosos por defecto, pero aquí son intencionales: así
          cualquier persona que navegue con teclado puede enfocar el
          carrusel (Tab) y moverlo con las flechas, sin depender solo del
          mouse/touch. Se usa <section> (en vez de div+role="region") para
          que el rol sea implícito por la propia semántica del elemento. */}
      {/* oxlint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- ver comentario arriba: patrón ARIA "carousel" */}
      <section
        ref={contenedorRef}
        aria-roledescription="carrusel"
        aria-label="Productos destacados"
        // oxlint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- ver comentario arriba: patrón ARIA "carousel"
        tabIndex={0}
        onKeyDown={handleKeyDown}
        onMouseEnter={() => setPausado(true)}
        onMouseLeave={() => {
          setPausado(false);
          finalizarArrastre();
        }}
        onPointerDown={(e) => iniciarArrastre(e.clientX)}
        onPointerMove={(e) => moverArrastre(e.clientX)}
        onPointerUp={finalizarArrastre}
        className="relative h-[340px] select-none overflow-hidden px-2 outline-none sm:h-[380px] md:h-[420px]"
        style={{ touchAction: "pan-y" }}
      >
        {items.map((item, indice) => {
          let offset = indice - indiceActual;
          // Normaliza el offset para que el carrusel sea circular
          // (ej: del último al primero se mueve "hacia adelante").
          if (offset > total / 2) offset -= total;
          if (offset < -total / 2) offset += total;

          const esActivo = offset === 0;
          const visible = Math.abs(offset) <= 1;

          const desplazamiento = offset * 62 + arrastreX / 6;
          const escala = esActivo ? 1 : 0.82;
          const opacidad = Math.abs(offset) > 1 ? 0 : esActivo ? 1 : 0.55;

          return (
            <div
              key={item.id}
              aria-hidden={!esActivo}
              className="absolute left-1/2 top-1/2 w-[78%] max-w-sm transition-all duration-500 ease-out sm:w-[62%] md:w-[46%]"
              style={{
                transform: `translate(-50%, -50%) translateX(${desplazamiento}%) scale(${escala})`,
                opacity: opacidad,
                zIndex: esActivo ? 20 : 10 - Math.abs(offset),
                pointerEvents: visible ? "auto" : "none",
              }}
            >
              <button
                type="button"
                onClick={() => !esActivo && irA(indice)}
                className={`block w-full overflow-hidden rounded-2xl bg-section text-left shadow-xl shadow-primary/10 ${
                  esActivo ? "cursor-default" : "cursor-pointer"
                }`}
                tabIndex={esActivo ? -1 : 0}
                aria-label={esActivo ? undefined : `Ir a ${item.titulo}`}
              >
                <img
                  src={item.imagen}
                  alt={item.titulo}
                  draggable={false}
                  className="aspect-[4/5] w-full object-cover"
                />
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent px-4 pb-4 pt-10 text-left">
                  <h3 className="font-display text-base font-semibold text-white sm:text-lg">
                    {item.titulo}
                  </h3>
                  {esActivo && (
                    <p className="mt-1 text-xs text-white/85 sm:text-sm">{item.descripcion}</p>
                  )}
                </div>
              </button>
            </div>
          );
        })}

        {/* Controles anterior/siguiente */}
        <button
          type="button"
          onClick={anterior}
          aria-label="Producto anterior"
          className="absolute left-1 top-1/2 z-30 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/85 text-ink shadow transition-all duration-200 hover:scale-110 hover:bg-white hover:shadow-md sm:left-3"
        >
          <Icon path={ICON_PATHS.chevronLeft} />
        </button>
        <button
          type="button"
          onClick={siguiente}
          aria-label="Siguiente producto"
          className="absolute right-1 top-1/2 z-30 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/85 text-ink shadow transition-all duration-200 hover:scale-110 hover:bg-white hover:shadow-md sm:right-3"
        >
          <Icon path={ICON_PATHS.chevronRight} />
        </button>
      </section>

      {/* Indicadores */}
      <div className="mt-5 flex justify-center gap-2">
        {items.map((_, indice) => (
          <button
            key={indice}
            type="button"
            onClick={() => irA(indice)}
            aria-label={`Ir a la imagen ${indice + 1}`}
            aria-current={indice === indiceActual}
            className={`h-2.5 rounded-full transition-all duration-300 hover:scale-110 ${
              indice === indiceActual ? "w-6 bg-accent" : "w-2.5 bg-beige/60 hover:bg-beige"
            }`}
          />
        ))}
      </div>
    </div>
  );
}

export default Carousel;
