import { Link } from "react-router-dom";
import Icon from "./ui/Icon";
import ICON_PATHS from "./ui/iconPaths";
import coleccionesData from "../data/coleccionesData";

/**
 * Sección "Nuestra vitrina": muestra las categorías de Dulce Esencia como
 * tarjetas. Cada tarjeta lleva a /tienda ya filtrada por esa categoría
 * (`coleccion.id` usa el mismo vocabulario que `productos.familia` en la
 * BD — ver constants/familiasProducto.js).
 *
 * Grilla asimétrica tipo "vitrina": la primera categoría (tortas) ocupa
 * el doble de ancho como destacada, en vez de que las 6 tarjetas
 * compitan por la misma atención en una grilla uniforme.
 */
function Collections() {
  return (
    <section className="px-4 py-16 sm:px-6" aria-labelledby="colecciones-titulo">
      <div className="mx-auto mb-10 max-w-2xl text-center">
        <h2 id="colecciones-titulo" className="text-2xl font-bold sm:text-3xl">
          Nuestra vitrina
        </h2>
        <p className="mt-2 text-primary/70">
          Explora nuestra pastelería por categoría y encuentra el antojo que
          más se parece a ti.
        </p>
      </div>

      <div className="mx-auto grid max-w-5xl auto-rows-[minmax(120px,auto)] gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {coleccionesData.map((coleccion, indice) => {
          // La primera categoría es la destacada: ocupa doble ancho y
          // doble alto en pantallas grandes.
          const esDestacada = indice === 0;
          return (
            <Link
              key={coleccion.id}
              to={`/tienda?familia=${coleccion.id}`}
              className={`group flex flex-col justify-between gap-6 border border-beige/60 bg-cream p-6 text-left transition-colors duration-200 hover:border-accent ${
                esDestacada ? "lg:col-span-2 lg:row-span-2" : ""
              }`}
            >
              <span
                className={`flex shrink-0 items-center justify-center rounded-full transition-transform duration-300 group-hover:scale-110 ${coleccion.acento} ${
                  esDestacada ? "h-16 w-16" : "h-11 w-11"
                }`}
              >
                <Icon path={ICON_PATHS.sparkle} className={esDestacada ? "h-8 w-8" : "h-5 w-5"} />
              </span>
              <span>
                <span
                  className={`block font-display font-medium text-primary ${
                    esDestacada ? "text-2xl" : "text-base"
                  }`}
                >
                  {coleccion.nombre}
                </span>
                <span className="mt-1 block text-sm text-primary/70">
                  {coleccion.descripcion}
                </span>
              </span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

export default Collections;
