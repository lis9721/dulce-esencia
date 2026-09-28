import { useRef } from "react";
import { Link } from "react-router-dom";
import { resolverUrlImagen } from "../utils/formato";

const heroImagen = resolverUrlImagen("/uploads/productos/e183cb186c224d0b9baab1f5965352cd.jpg");

/**
 * Hero de la página de inicio.
 *
 * Split asimétrico 55/45: el texto ancla abajo-izquierda, la foto del
 * producto estrella sangra por el borde derecho y superior, y una línea
 * vertical de trazo irregular separa ambas mitades. Es el único momento de animación orquestado
 * de toda la página (ver comentario en index.css) — el resto del
 * sitio solo anima en respuesta a acciones del usuario.
 *
 * El reflejo de luz que sigue al cursor sobre la imagen (punto 1 de
 * la propuesta) se hace con un radial-gradient posicionado vía
 * variables CSS `--x`/`--y`, actualizadas en cada `pointermove` —
 * sin librerías, sin recalcular layout.
 */
function Hero() {
  const imagenRef = useRef(null);

  const seguirCursor = (evento) => {
    const nodo = imagenRef.current;
    if (!nodo) return;
    const rect = nodo.getBoundingClientRect();
    const x = ((evento.clientX - rect.left) / rect.width) * 100;
    const y = ((evento.clientY - rect.top) / rect.height) * 100;
    nodo.style.setProperty("--x", `${x}%`);
    nodo.style.setProperty("--y", `${y}%`);
  };

  return (
    <section className="relative overflow-hidden bg-cream">
      <div className="mx-auto grid max-w-6xl grid-cols-1 md:grid-cols-[55%_45%]">
        {/* Texto: ancla abajo-izquierda, no centrado. */}
        <div className="relative z-10 flex flex-col justify-end px-4 py-16 sm:px-6 sm:py-20 md:py-28">
          <h1 className="animate-hero-parallax max-w-md text-4xl leading-[1.05] font-display font-medium text-primary sm:text-5xl">
            Horneado con cariño cada mañana.
          </h1>
          <p
            className="animate-hero-parallax mt-5 max-w-sm text-primary/70"
            style={{ animationDelay: "0.1s" }}
          >
            Tortas, cupcakes, galletas y panes artesanales elaborados con
            mantequilla, chocolate y frutas de verdad.
          </p>
          <div
            className="animate-hero-parallax mt-8 flex flex-wrap items-center gap-5"
            style={{ animationDelay: "0.2s" }}
          >
            <Link
              to="/tienda"
              className="inline-block bg-primary px-6 py-3 text-sm font-semibold text-cream transition-colors duration-200 hover:bg-primary-dark"
              style={{
                clipPath: "polygon(0 0, 100% 0, 100% 100%, 10px 100%, 0 calc(100% - 10px))",
              }}
            >
              Explorar la vitrina
            </Link>
            <span className="text-sm text-primary/70">Desde $18.000</span>
          </div>
        </div>

        {/* Línea divisoria: un trazo irregular (no una onda genérica)
            que se dibuja al cargar. */}
        <svg
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 left-1/2 hidden h-full w-6 -translate-x-1/2 md:block"
          viewBox="0 0 24 400"
          preserveAspectRatio="none"
        >
          <path
            className="animate-grieta"
            d="M12 0 L9 60 L15 95 L10 150 L14 190 L11 260 L15 300 L10 350 L12 400"
            fill="none"
            stroke="var(--color-champagne)"
            strokeWidth="1"
          />
        </svg>

        {/* Imagen: sangra por el borde derecho y superior, con el
            reflejo de luz que sigue al cursor. */}
        <div
          ref={imagenRef}
          onPointerMove={seguirCursor}
          className="relative h-64 overflow-hidden sm:h-80 md:h-auto md:-mr-[max(0px,calc((100vw-72rem)/2))]"
          style={{ "--x": "50%", "--y": "50%" }}
        >
          <img
            src={heroImagen}
            alt="Torta de fresas y crema de Dulce Esencia"
            className="h-full w-full object-cover"
          />
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(circle 220px at var(--x) var(--y), rgba(255,255,255,0.16), transparent 70%)",
            }}
          />
        </div>
      </div>
    </section>
  );
}

export default Hero;
