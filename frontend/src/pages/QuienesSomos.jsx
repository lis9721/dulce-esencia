import Reveal from "../components/Reveal";
import useDocumentTitle from "../hooks/useDocumentTitle";

function QuienesSomos() {
  useDocumentTitle(
    "Quiénes somos",
    "Conoce la historia de Dulce Esencia, una pastelería artesanal de Medellín dedicada a hornear tortas, cupcakes, galletas y panes con ingredientes nobles.",
    "/quienes-somos"
  );

  return (
    <main className="flex-1">
      <Reveal>
        <section className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6">
          <h1 className="text-3xl font-bold sm:text-4xl">Nuestra esencia</h1>
          <div className="mx-auto mt-3 h-px w-16 bg-champagne" />
          <p className="mt-6 text-primary/70">
            Dulce Esencia es una pastelería artesanal de Medellín dedicada a
            hornear tortas, cupcakes, galletas y panes de alta calidad, con
            ingredientes nobles como la mantequilla, el chocolate, la vainilla
            y las frutas frescas.
          </p>
          <p className="mt-4 text-primary/70">
            Nuestro equipo combina la tradición repostera con una
            experiencia de compra moderna, ofreciendo asesoría personalizada
            para que encuentres —o diseñes— el postre perfecto para cada
            celebración.
          </p>
        </section>
      </Reveal>
    </main>
  );
}

export default QuienesSomos;
