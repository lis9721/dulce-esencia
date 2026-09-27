import { Link } from "react-router-dom";
import Carousel from "../components/Carousel";
import Collections from "../components/Collections";
import Hero from "../components/Hero";
import AnatomiaTorta from "../components/AnatomiaTorta";
import Reveal from "../components/Reveal";
import Icon from "../components/ui/Icon";
import ICON_PATHS from "../components/ui/iconPaths";
import carouselData from "../data/carouselData";
import useDocumentTitle from "../hooks/useDocumentTitle";

const BENEFICIOS = [
  {
    icono: ICON_PATHS.sparkle,
    titulo: "Recetas artesanales",
    descripcion: "Elaboradas por nuestros pasteleros con mantequilla, chocolate y frutas de verdad.",
  },
  {
    icono: ICON_PATHS.truck,
    titulo: "Domicilio a tu puerta",
    descripcion: "Recíbelos frescos en tu casa u oficina, cuidadosamente empacados.",
  },
  {
    icono: ICON_PATHS.shieldCheck,
    titulo: "Compra segura",
    descripcion: "Pagos protegidos y garantía de satisfacción en cada pedido.",
  },
];

function Index() {
  useDocumentTitle(
    "Pastelería artesanal",
    "Descubre Dulce Esencia: tortas, cupcakes, galletas, postres y panes artesanales horneados cada día. Pide en línea con domicilio.",
    "/"
  );

  return (
    <main className="flex-1">
      <Hero />

      {/* Nuestra vitrina: categorías de productos */}
      <Reveal>
        <Collections />
      </Reveal>

      {/* Cómo se arma una torta: diferenciador propio del negocio, ver
          components/AnatomiaTorta.jsx */}
      <Reveal>
        <AnatomiaTorta />
      </Reveal>

      {/* Carrusel de productos destacados */}
      <Reveal>
        <section id="coleccion-destacada" className="textura-acero bg-section px-4 py-16 sm:px-6">
          <div className="mx-auto mb-10 max-w-2xl text-center">
            <h2 className="text-2xl font-bold sm:text-3xl">Favoritos de la casa</h2>
            <p className="mt-2 text-primary/70">
              Un vistazo a algunos de nuestros productos más queridos.
            </p>
          </div>
          <Carousel items={carouselData} />
          <div className="mt-8 text-center">
            <Link
              to="/tienda"
              className="inline-block rounded-lg bg-primary px-6 py-3 text-sm font-semibold tracking-wide text-cream transition-all duration-200 hover:scale-105 hover:bg-primary-dark hover:shadow-lg"
            >
              VER CATÁLOGO COMPLETO
            </Link>
          </div>
        </section>
      </Reveal>

      {/* Beneficios */}
      <Reveal>
        <section className="px-4 py-16 sm:px-6">
          <div className="mx-auto grid max-w-5xl gap-8 sm:grid-cols-3">
            {BENEFICIOS.map((beneficio) => (
              <div
                key={beneficio.titulo}
                className="group flex flex-col items-center text-center"
              >
                <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-blush/50 text-ink transition-transform duration-300 group-hover:scale-110 group-hover:rotate-6">
                  <Icon path={beneficio.icono} className="h-7 w-7" />
                </span>
                <h3 className="text-base font-semibold">{beneficio.titulo}</h3>
                <p className="mt-1 text-sm text-primary/70">{beneficio.descripcion}</p>
              </div>
            ))}
          </div>
        </section>
      </Reveal>

      {/* CTA final */}
      <Reveal>
        <section className="bg-primary px-4 py-16 text-center text-cream sm:px-6">
          <h2 className="text-2xl font-bold sm:text-3xl">Endulza tu próxima celebración</h2>
          <p className="mx-auto mt-2 max-w-md text-cream/70">
            Conoce la historia de Dulce Esencia y déjate guiar por nuestras recomendaciones.
          </p>
          <Link
            to="/quienes-somos"
            className="mt-6 inline-block rounded-lg bg-cream px-6 py-3 text-sm font-semibold tracking-wide text-primary transition-all duration-200 hover:scale-105 hover:bg-champagne/40 hover:shadow-lg"
          >
            CONOCER MÁS
          </Link>
        </section>
      </Reveal>
    </main>
  );
}

export default Index;
