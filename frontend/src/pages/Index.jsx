import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Reveal from "../components/Reveal";
import Icon from "../components/ui/Icon";
import ICON_PATHS from "../components/ui/iconPaths";
import carouselData from "../data/carouselData";
import useDocumentTitle from "../hooks/useDocumentTitle";
import useCart from "../hooks/useCart";
import { formatearPrecio, resolverUrlImagen } from "../utils/formato";
import { listarProductos } from "../utils/api";


const CATEGORIAS_RAPIDAS = [
  { id: "tortas", nombre: "Tortas", icono: "🎂", badge: "12 variedades", color: "bg-blush/40 text-primary border-blush" },
  { id: "cupcakes", nombre: "Cupcakes", icono: "🧁", badge: "8 sabores", color: "bg-champagne/40 text-primary border-champagne" },
  { id: "galletas", nombre: "Galletas & Macarons", icono: "🍪", badge: "Cajas x12", color: "bg-sage/40 text-primary border-sage" },
  { id: "postres", nombre: "Postres & Cheesecakes", icono: "🍰", badge: "Frutos rojos", color: "bg-lavender/40 text-primary border-lavender" },
  { id: "hojaldres", nombre: "Hojaldres", icono: "🥐", badge: "Recién horneado", color: "bg-blush-dark/30 text-primary border-blush-dark/40" },
  { id: "panaderia", nombre: "Panadería", icono: "🥖", badge: "Pan de bono", color: "bg-champagne/50 text-primary border-champagne" },
];

const CAPAS_TORTA = [
  {
    id: "bizcocho",
    nombre: "1. Bizcocho Húmedo",
    descripcion: "Horneado a fuego lento con mantequilla de verdad, huevos frescos y vainilla pura.",
    ingredientes: ["Mantequilla pura", "Cacao o vainilla", "Harina seleccionada"],
  },
  {
    id: "relleno",
    nombre: "2. Relleno Cremoso",
    descripcion: "Chantilly sedosa, ganache belga o compotas caseras de fresa y frutos del bosque.",
    ingredientes: ["Frutas frescas", "Crema chantilly", "Ganache artesanal"],
  },
  {
    id: "cobertura",
    nombre: "3. Cobertura & Arte",
    descripcion: "Decoración impecable con buttercream suave, flores comestibles y fruta fresca.",
    ingredientes: ["Buttercream de autor", "Fresas frescas", "Toppings crujientes"],
  },
];

const BENEFICIOS = [
  {
    icono: ICON_PATHS.sparkle,
    titulo: "100% Artesanal",
    descripcion: "Mantequilla real, cacao puro y fruta fresca. Sin conservantes artificiales.",
  },
  {
    icono: ICON_PATHS.truck,
    titulo: "Envíos Cuidados",
    descripcion: "Empaque especial térmico y protegido para que llegue perfecto a tu mesa.",
  },
  {
    icono: ICON_PATHS.shieldCheck,
    titulo: "Pagos Seguros",
    descripcion: "Paga con tarjeta, transferencia o pasarela protegida en segundos.",
  },
  {
    icono: ICON_PATHS.cart,
    titulo: "Garantía de Sabor",
    descripcion: "Elaborado fresco el mismo día de tu entrega para máxima frescura.",
  },
];

const RESENAS = [
  {
    nombre: "María Paula V.",
    rol: "Cliente verificado",
    comentario: "La Torta de Fresas y Crema fue el centro de atención del cumpleaños de mi mamá. Bizcocho húmedo, dulzor en el punto exacto y presentación hermosa.",
    calificacion: 5,
    producto: "Torta de Fresas y Crema",
  },
  {
    nombre: "Juan Diego C.",
    rol: "Cliente verificado",
    comentario: "Pedí los macarons y cupcakes para una reunión corporativa. La puntualidad de entrega y la calidad de la masa hojaldrada fueron excepcionales.",
    calificacion: 5,
    producto: "Macarons & Cupcakes",
  },
  {
    nombre: "Sofía Herrera",
    rol: "Cliente frecuente",
    comentario: "El cheesecake de frutos rojos es el mejor de Medellín sin duda alguna. Se nota el amor y la técnica en cada capa. 100% recomendados.",
    calificacion: 5,
    producto: "Cheesecake de Frutos Rojos",
  },
];

function Index() {
  useDocumentTitle(
    "Pastelería Artesanal",
    "Descubre Dulce Esencia: tortas, cupcakes, galletas, postres y panes recién horneados con ingredientes 100% naturales.",
    "/"
  );

  const { agregar } = useCart();
  const [agregados, setAgregados] = useState({});

  // Catálogo del home: parte de los datos fijos (carouselData) y, apenas
  // responde la API, toma de ahí la imagen real de cada producto (misma
  // fuente que /tienda). Si la API falla, quedan las fotos de respaldo.
  const [catalogo, setCatalogo] = useState(carouselData);
  useEffect(() => {
    let vigente = true;
    listarProductos({ pagina: 1, limite: 50 })
      .then((respuesta) => {
        if (!vigente) return;
        const reales = respuesta.datos || [];
        if (reales.length >= 3) {
          setCatalogo(
            reales.map((p) => {
              const carouselItem = carouselData.find((c) => c.titulo === p.titulo);
              // Forzar siempre el uso de la foto local (la foto "linda") si el producto es uno de los 10 originales.
              const usarFotoLocal = Boolean(carouselItem);
              return { ...p, imagen: usarFotoLocal ? carouselItem.imagen : resolverUrlImagen(p.imagen) };
            })
          );
        } else if (reales.length > 0) {
          // Si hay menos de 3, completamos con el carouselData para no romper el layout del Bento
          const combinados = reales.map((p) => {
            const carouselItem = carouselData.find((c) => c.titulo === p.titulo);
            const usarFotoLocal = Boolean(carouselItem);
            return { ...p, imagen: usarFotoLocal ? carouselItem.imagen : resolverUrlImagen(p.imagen) };
          });
          const faltantes = 3 - reales.length;
          setCatalogo([...combinados, ...carouselData.slice(0, faltantes)]);
        }
      })
      .catch(() => {});
    return () => {
      vigente = false;
    };
  }, []);
  const [filtroCategoria, setFiltroCategoria] = useState("todos");
  const [capaActiva, setCapaActiva] = useState("bizcocho");
  const [cuponCopiado, setCuponCopiado] = useState(false);

  const handleAgregar = async (producto) => {
    try {
      await agregar(producto, 1);
      setAgregados((prev) => ({ ...prev, [producto.id]: true }));
      setTimeout(() => {
        setAgregados((prev) => ({ ...prev, [producto.id]: false }));
      }, 1600);
    } catch {
      // Ignorar error de carrito
    }
  };

  const handleCopiarCupon = () => {
    navigator.clipboard.writeText("DULCE10");
    setCuponCopiado(true);
    setTimeout(() => setCuponCopiado(false), 2000);
  };

  // Filtrado de productos destacados
  const productosFiltrados = catalogo.filter((item) => {
    if (filtroCategoria === "todos") return true;
    if (filtroCategoria === "tortas") return item.titulo.toLowerCase().includes("torta");
    if (filtroCategoria === "cupcakes") return item.titulo.toLowerCase().includes("cupcake");
    if (filtroCategoria === "galletas") return item.titulo.toLowerCase().includes("galleta") || item.titulo.toLowerCase().includes("macaron");
    if (filtroCategoria === "postres") return item.titulo.toLowerCase().includes("cheesecake");
    if (filtroCategoria === "panaderia") return item.titulo.toLowerCase().includes("croissant") || item.titulo.toLowerCase().includes("pan");
    return true;
  });

  const capaSeleccionada = CAPAS_TORTA.find((c) => c.id === capaActiva) || CAPAS_TORTA[0];

  return (
    <main className="flex-1 space-y-12 pb-16">
      {/* ========================================================================= */}
      {/* 1. HERO BENTO MODERNO: ESPACIO 100% OPTIMIZADO */}
      {/* ========================================================================= */}
      <section className="relative overflow-hidden bg-gradient-to-b from-cream via-cream to-section/40 px-4 pt-6 pb-12 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="grid grid-cols-1 items-center gap-8 lg:grid-cols-12 lg:gap-10">
            {/* Columna Izquierda: Mensaje principal y llamados a la acción (7 cols) */}
            <div className="flex flex-col justify-center lg:col-span-7">
              <div className="mb-4 inline-flex items-center gap-2 self-start rounded-full border border-blush bg-blush/30 px-3.5 py-1 text-xs font-semibold text-primary">
                <span className="flex h-2 w-2 rounded-full bg-accent animate-pulse" />
                <span>Horneado artesanal cada mañana • Medellín</span>
              </div>

              <h1 className="font-display text-4xl leading-[1.12] font-bold text-primary sm:text-5xl lg:text-6xl">
                El arte de endulzar tus momentos con sabor <span className="text-accent underline decoration-blush decoration-wavy">auténtico</span>.
              </h1>

              <p className="mt-4 max-w-xl text-base text-primary/75 sm:text-lg">
                Tortas personalizadas, cupcakes esponjosos y repostería fina hechos desde cero con mantequilla de verdad, cacao puro y frutas frescas seleccionadas.
              </p>

              {/* Botones de acción principales */}
              <div className="mt-7 flex flex-wrap items-center gap-3.5">
                <Link
                  to="/tienda"
                  className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-sm font-semibold tracking-wide text-cream shadow-md transition-all hover:scale-[1.02] hover:bg-primary-dark hover:shadow-lg active:scale-95"
                >
                  <Icon path={ICON_PATHS.cart} className="h-4 w-4" />
                  <span>Ver Menú & Tienda</span>
                </Link>

                <Link
                  to="/servicios"
                  className="inline-flex items-center gap-2 rounded-xl border-2 border-beige bg-cream/70 px-5 py-3 text-sm font-semibold text-primary backdrop-blur-sm transition-all hover:border-primary hover:bg-cream active:scale-95"
                >
                  <span>Torta Personalizada</span>
                  <Icon path={ICON_PATHS.chevronRight} className="h-4 w-4" />
                </Link>
              </div>

              {/* Métricas de confianza compactas */}
              <div className="mt-8 grid grid-cols-3 gap-3 border-t border-beige/60 pt-5 sm:max-w-lg">
                <div className="flex flex-col">
                  <span className="font-display text-xl font-bold text-primary sm:text-2xl">4.9 ★</span>
                  <span className="text-xs text-primary/65">+1.200 clientes felices</span>
                </div>
                <div className="flex flex-col border-l border-beige/60 pl-3">
                  <span className="font-display text-xl font-bold text-primary sm:text-2xl">Hoy</span>
                  <span className="text-xs text-primary/65">Envíos el mismo día</span>
                </div>
                <div className="flex flex-col border-l border-beige/60 pl-3">
                  <span className="font-display text-xl font-bold text-primary sm:text-2xl">100%</span>
                  <span className="text-xs text-primary/65">Ingredientes naturales</span>
                </div>
              </div>
            </div>

            {/* Columna Derecha: Bento Showcase interactivo (5 cols) */}
            <div className="grid grid-cols-2 gap-3.5 lg:col-span-5">
              {/* Tarjeta principal destacada (Ocupa 2 columnas de ancho) */}
              <div className="group relative col-span-2 overflow-hidden rounded-2xl border border-beige/70 bg-cream shadow-sm transition-all duration-300 hover:shadow-md">
                <div className="relative h-56 w-full overflow-hidden sm:h-64">
                  <img
                    src={catalogo[0]?.imagen}
                    alt={catalogo[0]?.titulo}
                    className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/10" />

                  <span className="absolute top-3 left-3 rounded-full bg-blush px-3 py-1 text-xs font-bold text-ink shadow-sm">
                    🔥 Favorita de la Casa
                  </span>

                  <div className="absolute right-3 bottom-3 left-3 flex items-end justify-between gap-2 text-white">
                    <div>
                      <h2 className="text-base font-bold text-white drop-shadow sm:text-lg">
                        {catalogo[0]?.titulo}
                      </h2>
                      <p className="line-clamp-1 text-xs text-white/90">{catalogo[0]?.descripcion}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => catalogo[0] && handleAgregar(catalogo[0])}
                      className="shrink-0 rounded-lg bg-cream px-3 py-1.5 text-xs font-bold text-primary shadow transition-all hover:bg-white active:scale-90"
                    >
                      {catalogo[0] && agregados[catalogo[0].id] ? "¡Añadida! ✓" : catalogo[0] ? `${formatearPrecio(catalogo[0].precio)} +` : ""}
                    </button>
                  </div>
                </div>
              </div>

              {/* Tarjeta secundaria 1: Macarons */}
              <div className="group relative flex flex-col justify-between overflow-hidden rounded-xl border border-beige/60 bg-cream p-3 shadow-xs transition-all hover:border-accent/40 hover:shadow-sm">
                <div className="relative h-28 w-full overflow-hidden rounded-lg">
                  <img
                    src={catalogo[1]?.imagen}
                    alt={catalogo[1]?.titulo}
                    className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                  />
                </div>
                <div className="mt-2.5">
                  <h3 className="line-clamp-1 text-xs font-bold text-primary sm:text-sm">{catalogo[1]?.titulo}</h3>
                  <div className="mt-1 flex items-center justify-between">
                    <span className="text-xs font-bold text-accent">{catalogo[1] ? formatearPrecio(catalogo[1].precio) : ""}</span>
                    <button
                      type="button"
                      onClick={() => catalogo[1] && handleAgregar(catalogo[1])}
                      className="rounded bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary transition-colors hover:bg-primary hover:text-white"
                    >
                      {catalogo[1] && agregados[catalogo[1].id] ? "✓" : "+ Añadir"}
                    </button>
                  </div>
                </div>
              </div>

              {/* Tarjeta secundaria 2: Cupcakes */}
              <div className="group relative flex flex-col justify-between overflow-hidden rounded-xl border border-beige/60 bg-cream p-3 shadow-xs transition-all hover:border-accent/40 hover:shadow-sm">
                <div className="relative h-28 w-full overflow-hidden rounded-lg">
                  <img
                    src={catalogo[2]?.imagen}
                    alt={catalogo[2]?.titulo}
                    className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                  />
                </div>
                <div className="mt-2.5">
                  <h3 className="line-clamp-1 text-xs font-bold text-primary sm:text-sm">{catalogo[2]?.titulo}</h3>
                  <div className="mt-1 flex items-center justify-between">
                    <span className="text-xs font-bold text-accent">{catalogo[2] ? formatearPrecio(catalogo[2].precio) : ""}</span>
                    <button
                      type="button"
                      onClick={() => catalogo[2] && handleAgregar(catalogo[2])}
                      className="rounded bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary transition-colors hover:bg-primary hover:text-white"
                    >
                      {catalogo[2] && agregados[catalogo[2].id] ? "✓" : "+ Añadir"}
                    </button>
                  </div>
                </div>
              </div>
              </div>
            </div>
          </div>
      </section>

      {/* ========================================================================= */}
      {/* 2. BARRA DE CATEGORÍAS RÁPIDAS (ACCESO DIRECTO Y ESPACIO COMPACTO) */}
      {/* ========================================================================= */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between pb-3">
          <div>
            <h2 className="text-lg font-bold sm:text-xl">Nuestra Vitrina por Categoría</h2>
            <p className="text-xs text-primary/70 sm:text-sm">Encuentra exactamente lo que se te antoja hoy</p>
          </div>
          <Link
            to="/tienda"
            className="text-xs font-semibold text-accent hover:underline sm:text-sm"
          >
            Ver catálogo completo →
          </Link>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {CATEGORIAS_RAPIDAS.map((cat) => (
            <Link
              key={cat.id}
              to={`/tienda?familia=${cat.id}`}
              className="group flex flex-col justify-between rounded-xl border border-beige/60 bg-cream p-3.5 transition-all duration-200 hover:-translate-y-1 hover:border-accent hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <span className="text-2xl transition-transform duration-300 group-hover:scale-125">
                  {cat.icono}
                </span>
                <span className="rounded-full bg-primary/5 px-2 py-0.5 text-[10px] font-medium text-primary/70">
                  {cat.badge}
                </span>
              </div>
              <div className="mt-3">
                <span className="block font-semibold text-primary transition-colors group-hover:text-accent">
                  {cat.nombre}
                </span>
                <span className="text-[11px] text-primary/60 group-hover:text-primary/80">
                  Ver productos →
                </span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 3. PRODUCTOS MÁS VENDIDOS: GRID CON FILTRADO RÁPIDO */}
      {/* ========================================================================= */}
      <Reveal>
        <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col justify-between gap-4 border-b border-beige/60 pb-4 sm:flex-row sm:items-end">
            <div>
              <div className="inline-flex items-center gap-1.5 text-xs font-bold tracking-wider text-accent uppercase">
                <Icon path={ICON_PATHS.sparkle} className="h-3.5 w-3.5" />
                <span>Lo más pedido</span>
              </div>
              <h2 className="text-2xl font-bold sm:text-3xl">Favoritos de la Casa</h2>
              <p className="mt-1 text-sm text-primary/70">
                Los consentidos de nuestros clientes, listos para tu mesa o celebración.
              </p>
            </div>

            {/* Píldoras de filtro rápido */}
            <div className="flex flex-wrap gap-1.5 self-start sm:self-end">
              {[
                { id: "todos", label: "Todos" },
                { id: "tortas", label: "Tortas" },
                { id: "cupcakes", label: "Cupcakes" },
                { id: "galletas", label: "Galletas" },
                { id: "postres", label: "Postres" },
                { id: "panaderia", label: "Panes" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setFiltroCategoria(tab.id)}
                  className={`rounded-full px-3 py-1 text-xs font-semibold transition-all ${
                    filtroCategoria === tab.id
                      ? "bg-primary text-cream shadow-xs"
                      : "bg-cream text-primary/75 hover:bg-beige/50"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Grilla de productos con uso óptimo del espacio */}
          <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 lg:gap-6">
            {productosFiltrados.slice(0, 8).map((prod) => {
              const estaAgregado = Boolean(agregados[prod.id]);
              return (
                <div
                  key={prod.id}
                  className="group flex flex-col justify-between overflow-hidden rounded-2xl border border-beige/60 bg-cream shadow-xs transition-all duration-300 hover:border-accent/50 hover:shadow-md"
                >
                  <div className="relative aspect-square w-full overflow-hidden bg-section">
                    <img
                      src={prod.imagen}
                      alt={prod.titulo}
                      loading="lazy"
                      className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                    <span className="absolute top-2.5 left-2.5 rounded-md bg-cream/90 px-2 py-0.5 text-[11px] font-bold text-primary shadow-xs backdrop-blur-sm">
                      Stock: {prod.stock}
                    </span>
                  </div>

                  <div className="flex flex-1 flex-col justify-between p-3.5 sm:p-4">
                    <div>
                      <h3 className="font-display line-clamp-1 text-sm font-bold text-primary group-hover:text-accent sm:text-base">
                        {prod.titulo}
                      </h3>
                      <p className="mt-1 line-clamp-2 text-xs text-primary/70">
                        {prod.descripcion}
                      </p>
                    </div>

                    <div className="mt-4 flex items-center justify-between pt-2 border-t border-beige/40">
                      <div>
                        <span className="text-[10px] text-primary/60 uppercase">Precio</span>
                        <p className="text-sm font-bold text-primary sm:text-base">
                          {formatearPrecio(prod.precio)}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleAgregar(prod)}
                        className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-all active:scale-95 ${
                          estaAgregado
                            ? "bg-emerald-600 text-white"
                            : "bg-primary text-cream hover:bg-primary-dark"
                        }`}
                        title="Añadir al carrito"
                      >
                        {estaAgregado ? (
                          <>
                            <Icon path={ICON_PATHS.check} className="h-3.5 w-3.5" />
                            <span>Listo</span>
                          </>
                        ) : (
                          <>
                            <Icon path={ICON_PATHS.plus} className="h-3.5 w-3.5" />
                            <span>Añadir</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-8 text-center">
            <Link
              to="/tienda"
              className="inline-flex items-center gap-2 rounded-xl border border-primary px-6 py-2.5 text-sm font-bold text-primary transition-all hover:bg-primary hover:text-cream"
            >
              <span>Ver todos los productos ({catalogo.length})</span>
              <Icon path={ICON_PATHS.chevronRight} className="h-4 w-4" />
            </Link>
          </div>
        </section>
      </Reveal>

      {/* ========================================================================= */}
      {/* 4. BENTO GRID: EXPERIENCIAS, ANATOMÍA DE TORTA & PROMOCIONES */}
      {/* ========================================================================= */}
      <Reveal>
        <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
            {/* Tarjeta 1: Personalización de Tortas (5 cols) */}
            <div className="relative flex flex-col justify-between overflow-hidden rounded-2xl border border-beige/70 bg-gradient-to-br from-section to-cream p-6 lg:col-span-5 shadow-xs">
              <div className="relative z-10">
                <span className="inline-block rounded-full bg-blush/60 px-3 py-1 text-xs font-bold text-ink">
                  Eventos & Celebraciones
                </span>
                <h3 className="font-display mt-3 text-2xl font-bold sm:text-3xl">
                  Tortas a tu medida
                </h3>
                <p className="mt-2 text-sm text-primary/75">
                  ¿Tienes una boda, cumpleaños o evento corporativo? Personalizamos sabores, pisos, colores y temática con tus ideas.
                </p>

                <ul className="mt-4 space-y-2 text-xs text-primary/80 font-medium">
                  <li className="flex items-center gap-2">
                    <Icon path={ICON_PATHS.check} className="h-4 w-4 text-emerald-600" />
                    Diseños temáticos en fondant o crema
                  </li>
                  <li className="flex items-center gap-2">
                    <Icon path={ICON_PATHS.check} className="h-4 w-4 text-emerald-600" />
                    Degustación previa para bodas y quinceañeros
                  </li>
                  <li className="flex items-center gap-2">
                    <Icon path={ICON_PATHS.check} className="h-4 w-4 text-emerald-600" />
                    Entrega programada directamente en el evento
                  </li>
                </ul>
              </div>

              <div className="relative z-10 mt-6 pt-4 border-t border-beige/50">
                <Link
                  to="/servicios"
                  className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-xs font-bold text-cream transition-all hover:bg-primary-dark"
                >
                  <span>Cotizar mi evento</span>
                  <Icon path={ICON_PATHS.chevronRight} className="h-3.5 w-3.5" />
                </Link>
              </div>

              {/* Marca decorativa suave al fondo */}
              <div className="absolute right-0 bottom-0 -mr-6 -mb-6 h-36 w-36 rounded-full bg-blush/20 blur-xl pointer-events-none" />
            </div>

            {/* Tarjeta 2: Anatomía de la Torta Interactiva (4 cols) */}
            <div className="flex flex-col justify-between rounded-2xl border border-beige/70 bg-cream p-6 lg:col-span-4 shadow-xs">
              <div>
                <span className="text-xs font-bold tracking-wider text-accent uppercase">
                  Diferenciador Artesanal
                </span>
                <h3 className="font-display mt-1 text-xl font-bold sm:text-2xl">
                  Anatomía de una Torta
                </h3>
                <p className="mt-1 text-xs text-primary/70">
                  Así construimos cada creación para lograr frescura y humedad perfecta.
                </p>

                {/* Tabs de capas */}
                <div className="mt-4 flex rounded-lg bg-section p-1">
                  {CAPAS_TORTA.map((capa) => (
                    <button
                      key={capa.id}
                      type="button"
                      onClick={() => setCapaActiva(capa.id)}
                      className={`flex-1 rounded-md py-1.5 text-xs font-bold transition-all ${
                        capaActiva === capa.id
                          ? "bg-cream text-primary shadow-xs"
                          : "text-primary/60 hover:text-primary"
                      }`}
                    >
                      {capa.id === "bizcocho" ? "1. Bizcocho" : capa.id === "relleno" ? "2. Relleno" : "3. Cobertura"}
                    </button>
                  ))}
                </div>

                <div className="mt-4 rounded-xl border border-beige/60 bg-section/40 p-4 transition-all">
                  <h4 className="text-sm font-bold text-primary">{capaSeleccionada.nombre}</h4>
                  <p className="mt-1 text-xs text-primary/70">{capaSeleccionada.descripcion}</p>

                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {capaSeleccionada.ingredientes.map((ing) => (
                      <span
                        key={ing}
                        className="rounded-full bg-cream px-2.5 py-0.5 text-[11px] font-medium text-primary shadow-xs"
                      >
                        ✓ {ing}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-beige/40">
                <span className="text-[11px] text-primary/60 italic">
                  * Elaboradas con mantequilla pura de vaca y frutas frescas locales.
                </span>
              </div>
            </div>

            {/* Tarjeta 3: Cupón de Descuento & Promoción (3 cols) */}
            <div className="flex flex-col justify-between rounded-2xl border border-champagne bg-gradient-to-br from-champagne/30 via-cream to-blush/20 p-6 lg:col-span-3 shadow-xs">
              <div>
                <span className="inline-block rounded-full bg-champagne px-2.5 py-1 text-xs font-bold text-ink">
                  🎁 Cupón Especial
                </span>
                <h3 className="font-display mt-3 text-xl font-bold sm:text-2xl">
                  -10% en tu primera compra
                </h3>
                <p className="mt-2 text-xs text-primary/75">
                  Aplica este cupón en el checkout y empieza a disfrutar de Dulce Esencia hoy.
                </p>

                <div className="mt-4 rounded-xl border-2 border-dashed border-accent/40 bg-cream p-3 text-center">
                  <span className="font-mono text-lg font-bold tracking-widest text-accent">
                    DULCE10
                  </span>
                  <button
                    type="button"
                    onClick={handleCopiarCupon}
                    className="mt-2 block w-full rounded-lg bg-primary/10 py-1 text-xs font-bold text-primary hover:bg-primary hover:text-white transition-colors"
                  >
                    {cuponCopiado ? "¡Copiado al portapapeles! ✓" : "Copiar código"}
                  </button>
                </div>
              </div>

              <p className="mt-4 text-[11px] text-primary/60">
                Válido para usuarios nuevos en pedidos superiores a $30.000 COP.
              </p>
            </div>
          </div>
        </section>
      </Reveal>

      {/* ========================================================================= */}
      {/* 5. BENEFICIOS / PROPUESTA DE VALOR COMPACTA */}
      {/* ========================================================================= */}
      <Reveal>
        <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 gap-4 rounded-2xl border border-beige/60 bg-section/40 p-6 sm:p-8 lg:grid-cols-4">
            {BENEFICIOS.map((b) => (
              <div key={b.titulo} className="flex flex-col items-start gap-2.5">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Icon path={b.icono} className="h-5 w-5" />
                </span>
                <div>
                  <h4 className="text-sm font-bold text-primary sm:text-base">{b.titulo}</h4>
                  <p className="mt-1 text-xs text-primary/70">{b.descripcion}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      </Reveal>

      {/* ========================================================================= */}
      {/* 6. SOCIAL PROOF / OPINIONES DE CLIENTES REALES */}
      {/* ========================================================================= */}
      <Reveal>
        <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-6 text-center">
            <span className="text-xs font-bold tracking-wider text-accent uppercase">
              Opiniones Reales
            </span>
            <h2 className="text-2xl font-bold sm:text-3xl">La voz de nuestros clientes</h2>
            <p className="mt-1 text-sm text-primary/70">
              Más de 1.200 entregas felices en toda el área metropolitana.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {RESENAS.map((res) => (
              <div
                key={res.nombre}
                className="flex flex-col justify-between rounded-2xl border border-beige/60 bg-cream p-5 shadow-xs"
              >
                <div>
                  <div className="flex items-center gap-1 text-amber-500">
                    {"★".repeat(res.calificacion)}
                  </div>
                  <p className="mt-3 text-xs leading-relaxed text-primary/80 italic sm:text-sm">
                    "{res.comentario}"
                  </p>
                </div>

                <div className="mt-5 flex items-center justify-between border-t border-beige/50 pt-3">
                  <div>
                    <h4 className="text-xs font-bold text-primary">{res.nombre}</h4>
                    <span className="text-[10px] text-emerald-700 dark:text-emerald-400 font-semibold">
                      ✓ {res.rol}
                    </span>
                  </div>
                  <span className="rounded bg-section px-2 py-0.5 text-[10px] font-medium text-primary/70">
                    {res.producto}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </Reveal>

      {/* ========================================================================= */}
      {/* 7. BANNER FINAL CTA */}
      {/* ========================================================================= */}
      <Reveal>
        <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="relative overflow-hidden rounded-3xl bg-primary px-6 py-12 text-center text-cream shadow-xl sm:px-12 sm:py-16">
            <div className="relative z-10 mx-auto max-w-2xl">
              <span className="inline-block rounded-full bg-blush/20 px-3.5 py-1 text-xs font-bold text-blush tracking-wider uppercase">
                Endulza tu día
              </span>
              <h2 className="font-display mt-3 text-3xl font-bold sm:text-4xl">
                ¿Listo para probar el auténtico sabor artesanal?
              </h2>
              <p className="mt-3 text-sm text-cream/80 sm:text-base">
                Haz tu pedido en línea ahora y recíbelo fresco en tu casa u oficina, o programa tu torta para tu próxima fecha especial.
              </p>

              <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
                <Link
                  to="/tienda"
                  className="rounded-xl bg-cream px-7 py-3.5 text-sm font-bold text-primary shadow transition-all hover:scale-105 hover:bg-white active:scale-95"
                >
                  Explorar Catálogo Completo
                </Link>
                <Link
                  to="/contacto"
                  className="rounded-xl border border-cream/40 bg-cream/10 px-6 py-3.5 text-sm font-bold text-cream backdrop-blur-sm transition-all hover:bg-cream/20 active:scale-95"
                >
                  Hablar con un Asesor
                </Link>
              </div>
            </div>

            {/* Efectos de fondo sutiles */}
            <div className="absolute top-0 left-0 -ml-16 -mt-16 h-48 w-48 rounded-full bg-accent/20 blur-3xl pointer-events-none" />
            <div className="absolute right-0 bottom-0 -mr-16 -mb-16 h-48 w-48 rounded-full bg-blush/20 blur-3xl pointer-events-none" />
          </div>
        </section>
      </Reveal>
    </main>
  );
}

export default Index;
