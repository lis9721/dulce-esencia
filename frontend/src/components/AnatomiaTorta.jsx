import { useState } from "react";

/**
 * Sección "Cómo se arma una torta" — diferenciador propio del negocio
 * (no un carrusel de "features" reciclado de un SaaS): las tres capas de
 * una torta (bizcocho, relleno, cobertura) con sus ingredientes, tomando
 * la "Torta de Fresas y Crema" como ejemplo (la misma que protagoniza el
 * hero del home).
 *
 * Al cambiar de capa, el contenido no cambia de golpe: se difumina
 * suavemente (clase `animate-difusion` en index.css), la única animación
 * de interacción de esta sección aparte del hover normal de los botones.
 */
const CAPAS = [
  {
    id: "bizcocho",
    nombre: "Bizcocho",
    detalle: "La base esponjosa que sostiene todo",
    ingredientes: ["Harina de trigo", "Huevos frescos", "Mantequilla", "Vainilla natural"],
  },
  {
    id: "relleno",
    nombre: "Relleno",
    detalle: "La capa cremosa del centro",
    ingredientes: ["Crema chantilly", "Fresas frescas", "Mermelada casera"],
  },
  {
    id: "cobertura",
    nombre: "Cobertura",
    detalle: "El acabado que la hace lucir",
    ingredientes: ["Buttercream de vainilla", "Fresas enteras", "Hojas de menta"],
  },
];

function AnatomiaTorta() {
  const [capaActiva, setCapaActiva] = useState(CAPAS[0].id);
  const capa = CAPAS.find((c) => c.id === capaActiva);

  return (
    <section className="px-4 py-16 sm:px-6" aria-labelledby="capas-titulo">
      <div className="mx-auto mb-10 max-w-2xl text-center">
        <h2 id="capas-titulo" className="text-2xl font-bold sm:text-3xl">
          Cómo se arma una torta
        </h2>
        <p className="mt-2 text-primary/70">
          Cada torta se construye en tres capas. Así se compone nuestra Torta
          de Fresas y Crema.
        </p>
      </div>

      <div className="mx-auto max-w-2xl">
        <div className="flex border-b border-beige/60">
          {CAPAS.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setCapaActiva(c.id)}
              aria-current={c.id === capaActiva}
              className={`flex-1 border-b-2 px-3 py-3 text-sm font-medium transition-colors duration-200 ${
                c.id === capaActiva
                  ? "border-accent text-primary"
                  : "border-transparent text-primary/70 hover:text-primary/80"
              }`}
            >
              {c.nombre}
            </button>
          ))}
        </div>

        <div key={capa.id} className="animate-difusion mt-6 text-center">
          <p className="text-sm text-primary/70">{capa.detalle}</p>
          <div className="mt-4 flex flex-wrap justify-center gap-3">
            {capa.ingredientes.map((ingrediente) => (
              <span
                key={ingrediente}
                className="rounded-full border border-beige/60 bg-section px-4 py-1.5 text-sm text-primary"
              >
                {ingrediente}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export default AnatomiaTorta;
