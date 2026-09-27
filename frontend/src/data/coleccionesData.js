/**
 * Categorías mostradas en la sección "Nuestra vitrina" del landing.
 * `acento` es un token de color ya definido en el tema (index.css) que
 * se usa como fondo del círculo del icono, para diferenciar cada tarjeta
 * sin depender de fotos nuevas.
 */
const coleccionesData = [
  {
    id: "tortas",
    nombre: "Tortas",
    descripcion: "Bizcochos húmedos y rellenos cremosos para cumpleaños, bodas y toda ocasión.",
    // text-ink (no text-primary): blush es un acento de marca fijo que
    // sigue siendo claro en modo oscuro, así que la tinta también debe
    // quedarse oscura siempre.
    acento: "bg-blush/60 text-ink",
  },
  {
    id: "cupcakes",
    nombre: "Cupcakes",
    descripcion: "Porciones individuales con buttercream y toppings de temporada.",
    // bg-beige SÍ se invierte en modo oscuro (es un token "neutro"),
    // así que text-primary se sigue autoadaptando correctamente acá.
    acento: "bg-beige/70 text-primary",
  },
  {
    id: "galletas",
    nombre: "Galletas",
    descripcion: "Crujientes, suaves y rellenas: de chips de chocolate a macarons.",
    acento: "bg-champagne/40 text-ink",
  },
  {
    id: "postres",
    nombre: "Postres",
    descripcion: "Cheesecakes y postres fríos listos para compartir en la mesa.",
    // bg-primary/10 + text-primary usan el MISMO token para ambos, así
    // que quedan consistentes entre sí sin importar qué valor tome.
    acento: "bg-primary/10 text-primary",
  },
  {
    id: "hojaldres",
    nombre: "Hojaldres",
    descripcion: "Croissants y masas laminadas con capas crocantes de mantequilla.",
    acento: "bg-sage/30 text-ink",
  },
  {
    id: "panaderia",
    nombre: "Panadería",
    descripcion: "Pan de bono y panes artesanales recién horneados.",
    acento: "bg-blush-dark/40 text-ink",
  },
];

export default coleccionesData;
