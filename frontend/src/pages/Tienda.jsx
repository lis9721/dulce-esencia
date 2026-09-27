import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Reveal from "../components/Reveal";
import Icon from "../components/ui/Icon";
import ICON_PATHS from "../components/ui/iconPaths";
import Paginacion from "../components/ui/Paginacion";
import BotonAgregarCarrito from "../components/BotonAgregarCarrito";
import FAMILIAS_PRODUCTO from "../constants/familiasProducto";
import { formatearPrecio, resolverUrlImagen } from "../utils/formato";
import { listarProductos } from "../utils/api";
import useDocumentTitle from "../hooks/useDocumentTitle";

const PRODUCTOS_POR_PAGINA = 12;

/**
 * Tarjeta individual del catálogo. Separada del componente principal
 * solo para poder llevar su propio estado de "la imagen no cargó" —
 * el campo `imagen` de un producto es un nombre de archivo escrito a
 * mano desde el panel (`GestionProductos.jsx`), así que si el admin
 * comete una errata o el archivo no existe entre los assets
 * empaquetados, mostramos un ícono de repuesto en vez de dejar el
 * ícono roto típico del navegador.
 */
function TarjetaProducto({ producto }) {
  const [imagenRota, setImagenRota] = useState(false);

  const inactivo = producto.activo === 0 || producto.activo === false;
  const sinStock = Number(producto.stock) <= 0;
  // Umbral de "pocas unidades": arbitrario, solo para dar una señal de
  // urgencia razonable sin exagerar con stocks altos.
  const pocasUnidades = !inactivo && !sinStock && Number(producto.stock) <= 5;

  let etiqueta = null;
  if (inactivo) {
    // Solo admin/empleado pueden llegar a ver un producto inactivo aquí
    // (el backend ya filtra el resto vía verificarTokenOpcional), así
    // que esta etiqueta es una señal útil para ellos, no para clientes.
    // bg-primary/text-cream cambian JUNTOS con el tema (par
    // complementario), así que siguen contrastando bien en ambos.
    etiqueta = { texto: "No disponible", clase: "bg-primary/70 text-cream" };
  } else if (sinStock) {
    etiqueta = { texto: "Agotado", clase: "bg-primary/70 text-cream" };
  } else if (pocasUnidades) {
    // bg-accent es un acento de marca fijo (no cambia con el tema), así
    // que su texto necesita quedar fijo también (text-ink), no
    // acompañar el swap de text-cream.
    etiqueta = { texto: `¡Quedan ${producto.stock}!`, clase: "bg-accent text-paper" };
  }

  return (
    <div className="group flex flex-col overflow-hidden rounded-lg border border-beige/60 bg-section transition-colors duration-200 hover:border-accent">
      <div className="relative aspect-[4/5] w-full overflow-hidden">
        {etiqueta && (
          <span
            className={`absolute left-2 top-2 z-10 rounded-full px-2.5 py-1 text-[11px] font-semibold ${etiqueta.clase}`}
          >
            {etiqueta.texto}
          </span>
        )}
        {imagenRota ? (
          <div className="flex h-full w-full items-center justify-center bg-beige/30 text-primary/30">
            <Icon path={ICON_PATHS.sparkle} className="h-10 w-10" />
          </div>
        ) : (
          <img
            src={resolverUrlImagen(producto.imagen)}
            alt={producto.titulo}
            loading="lazy"
            onError={() => setImagenRota(true)}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
          />
        )}
      </div>
      <div className="flex flex-1 flex-col p-4">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="font-display text-base font-semibold text-primary">{producto.titulo}</h2>
          {producto.pesoG != null && (
            <span className="shrink-0 text-xs text-primary/70">{producto.pesoG} g</span>
          )}
        </div>
        <p className="mt-1 line-clamp-2 flex-1 text-sm text-primary/70">{producto.descripcion}</p>
        <div className="mt-3 flex flex-col gap-2">
          <span className="text-base font-semibold text-primary">
            {formatearPrecio(producto.precio)}
          </span>
          <BotonAgregarCarrito producto={producto} className="w-full" />
        </div>
      </div>
    </div>
  );
}

/**
 * Tienda
 * Catálogo real de la pastelería, conectado a GET /api/productos (el mismo
 * endpoint que ya usa GestionProductos.jsx en el panel de admin). A
 * diferencia del carrusel del home (que es solo contenido editorial/
 * decorativo, con datos fijos en `data/carouselData.js`), esta página
 * SIEMPRE refleja el inventario real: lo que el admin crea, edita o
 * desactiva desde /panel/productos se ve aquí de inmediato.
 *
 * Es la única página pensada para comprar. No tiene ningún control de
 * edición/eliminación aunque quien la visite sea admin o empleado —
 * esa función se queda exclusivamente en el panel, para no duplicar el
 * CRUD en dos lugares distintos.
 *
 * Ruta pública (sin ProtectedRoute): el propio backend, con
 * verificarTokenOpcional, ya filtra los productos inactivos para
 * quien no sea admin/empleado, así que el frontend no necesita
 * lógica adicional de roles aquí.
 */
function Tienda() {
  useDocumentTitle(
    "Tienda",
    "Explora el catálogo completo de Dulce Esencia Pastelería y añade tus antojos al carrito.",
    "/tienda"
  );

  const [searchParams, setSearchParams] = useSearchParams();
  // Si llega desde una tarjeta de "Colecciones" en el home
  // (Collections.jsx, ej. /tienda?familia=tortas) o de un link
  // compartido/recargado, preseleccionamos ese estado. Cada valor se
  // valida antes de usarlo, por si alguien edita la URL a mano con
  // algo que no existe.
  const familiaDesdeUrl = FAMILIAS_PRODUCTO.some((f) => f.value === searchParams.get("familia"))
    ? searchParams.get("familia")
    : "";
  const ordenDesdeUrl = ["precio_asc", "precio_desc"].includes(searchParams.get("orden"))
    ? searchParams.get("orden")
    : "";
  const paginaDesdeUrlNumero = Number(searchParams.get("pagina"));
  const paginaDesdeUrl =
    Number.isInteger(paginaDesdeUrlNumero) && paginaDesdeUrlNumero > 0 ? paginaDesdeUrlNumero : 1;

  const [productos, setProductos] = useState([]);
  const [paginacion, setPaginacion] = useState({
    pagina: paginaDesdeUrl,
    limite: PRODUCTOS_POR_PAGINA,
    total: 0,
    totalPaginas: 0,
  });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [familia, setFamilia] = useState(familiaDesdeUrl);
  const [orden, setOrden] = useState(ordenDesdeUrl);

  // `filtros` se pasa explícito en cada llamada (en vez de leerlo de
  // `familia`/`orden` por closure) para evitar el clásico bug de state
  // "viejo": si se leyera el state directamente, el handler que acaba
  // de hacer setFamilia(nuevaFamilia) todavía vería el valor anterior
  // en la misma renderización, porque los setState no son síncronos.
  const obtenerProductos = (pagina, filtros) => {
    setError("");
    listarProductos({
      pagina,
      limite: PRODUCTOS_POR_PAGINA,
      familia: filtros.familia,
      orden: filtros.orden,
    })
      .then((respuesta) => {
        setProductos(respuesta.datos);
        setPaginacion(respuesta.paginacion);
      })
      .catch((err) => setError(err.message || "No se pudo cargar el catálogo. Intenta de nuevo."))
      .finally(() => setCargando(false));
  };

  // Refleja {familia, orden, pagina} en la URL — reemplaza la entrada
  // actual del historial en vez de apilar una por cada clic (así el
  // botón "atrás" del navegador no se llena de un paso por cada
  // cambio de filtro). Con esto, recargar la página o compartir el
  // link mantiene exactamente el mismo estado del catálogo. `pagina=1`
  // se omite de la URL a propósito, para no ensuciarla con el caso
  // por defecto.
  const sincronizarUrl = ({ familia: familiaNueva, orden: ordenNuevo, pagina }) => {
    const params = {};
    if (familiaNueva) params.familia = familiaNueva;
    if (ordenNuevo) params.orden = ordenNuevo;
    if (pagina > 1) params.pagina = String(pagina);
    setSearchParams(params, { replace: true });
  };

  useEffect(() => {
    obtenerProductos(paginaDesdeUrl, { familia: familiaDesdeUrl, orden: ordenDesdeUrl });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCambiarPagina = (paginaNueva) => {
    setCargando(true);
    setBusqueda("");
    obtenerProductos(paginaNueva, { familia, orden });
    sincronizarUrl({ familia, orden, pagina: paginaNueva });
    // Sube al inicio de la grilla al cambiar de página, para que la
    // persona no tenga que scrollear hacia arriba manualmente.
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // Cambiar el filtro de familia u orden siempre vuelve a la página 1:
  // seguir en, por ejemplo, la página 3 de "todas las familias" no
  // tiene sentido al filtrar por "Cítricas", que puede tener muchas
  // menos páginas.
  const handleCambiarFamilia = (evento) => {
    const nuevaFamilia = evento.target.value;
    setFamilia(nuevaFamilia);
    setBusqueda("");
    setCargando(true);
    obtenerProductos(1, { familia: nuevaFamilia, orden });
    sincronizarUrl({ familia: nuevaFamilia, orden, pagina: 1 });
  };

  const handleCambiarOrden = (evento) => {
    const nuevoOrden = evento.target.value;
    setOrden(nuevoOrden);
    setBusqueda("");
    setCargando(true);
    obtenerProductos(1, { familia, orden: nuevoOrden });
    sincronizarUrl({ familia, orden: nuevoOrden, pagina: 1 });
  };

  // Búsqueda solo del lado del cliente, sobre los productos YA
  // cargados de la página actual: GET /api/productos no acepta un
  // parámetro de búsqueda (?buscar=), así que filtrar contra todo el
  // catálogo requeriría agregar eso al backend. Por eso el hint bajo
  // el input aclara "en esta página" — evita prometer una búsqueda
  // global que en realidad no cubre las demás páginas del catálogo.
  const terminoNormalizado = busqueda.trim().toLowerCase();
  const productosFiltrados = terminoNormalizado
    ? productos.filter((producto) => producto.titulo.toLowerCase().includes(terminoNormalizado))
    : productos;

  return (
    <main className="flex-1">
      <Reveal>
        <section className="px-4 py-16 sm:px-6">
          <div className="mx-auto mb-10 max-w-2xl text-center">
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.3em] text-champagne">
              Catálogo completo
            </p>
            <h1 className="text-3xl font-bold sm:text-4xl">Tienda</h1>
            <p className="mt-3 text-primary/70">
              Todos nuestros productos disponibles, listos para añadir al carrito.
            </p>
          </div>

          <div className="mx-auto max-w-6xl">
            {!cargando && !error && (
              <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
                <p className="text-sm text-primary/70">
                  {paginacion.total} {paginacion.total === 1 ? "producto" : "productos"}
                </p>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <select
                    value={familia}
                    onChange={handleCambiarFamilia}
                    aria-label="Filtrar por categoría"
                    className="rounded-lg border border-beige bg-cream px-3 py-2 text-sm text-primary focus:border-primary focus:outline-none"
                  >
                    <option value="">Todas las categorías</option>
                    {FAMILIAS_PRODUCTO.map((opcion) => (
                      <option key={opcion.value} value={opcion.value}>
                        {opcion.label}
                      </option>
                    ))}
                  </select>
                  <select
                    value={orden}
                    onChange={handleCambiarOrden}
                    aria-label="Ordenar por precio"
                    className="rounded-lg border border-beige bg-cream px-3 py-2 text-sm text-primary focus:border-primary focus:outline-none"
                  >
                    <option value="">Orden destacado</option>
                    <option value="precio_asc">Precio: menor a mayor</option>
                    <option value="precio_desc">Precio: mayor a menor</option>
                  </select>
                  <div className="relative w-full sm:w-56">
                    <Icon
                      path={ICON_PATHS.search}
                      className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-primary/40"
                    />
                    <input
                      type="search"
                      value={busqueda}
                      onChange={(evento) => setBusqueda(evento.target.value)}
                      placeholder="Buscar en esta página..."
                      aria-label="Buscar producto por nombre en esta página"
                      className="w-full rounded-lg border border-beige bg-cream py-2 pl-9 pr-3 text-sm text-primary placeholder:text-primary/40 focus:border-primary focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            )}

            {cargando && (
              <div
                className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
                aria-hidden="true"
              >
                {Array.from({ length: PRODUCTOS_POR_PAGINA }).map((_, indice) => (
                  <div key={indice} className="overflow-hidden rounded-2xl bg-section">
                    <div className="aspect-[4/5] w-full animate-pulse bg-beige/40" />
                    <div className="space-y-2 p-4">
                      <div className="h-4 w-3/4 animate-pulse rounded bg-beige/40" />
                      <div className="h-3 w-full animate-pulse rounded bg-beige/40" />
                      <div className="h-3 w-2/3 animate-pulse rounded bg-beige/40" />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!cargando && error && (
              <p className="mx-auto max-w-md rounded-lg bg-peligro px-4 py-3 text-center text-sm text-peligro-fuerte">
                {error}
              </p>
            )}

            {!cargando && !error && productos.length === 0 && (
              <p className="py-12 text-center text-sm text-primary/70">
                {familia
                  ? `No hay productos en la categoría "${FAMILIAS_PRODUCTO.find((f) => f.value === familia)?.label ?? familia}" por ahora.`
                  : "Todavía no hay productos disponibles."}
              </p>
            )}

            {!cargando && !error && productos.length > 0 && productosFiltrados.length === 0 && (
              <p className="py-12 text-center text-sm text-primary/70">
                Ningún producto de esta página coincide con "{busqueda.trim()}". Prueba con otra
                página o borra la búsqueda.
              </p>
            )}

            {!cargando && !error && productosFiltrados.length > 0 && (
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {productosFiltrados.map((producto, indice) => (
                  <div
                    key={producto.id}
                    className="animate-fade-in-up"
                    // Escalonado (stagger): cada tarjeta entra un poco
                    // después que la anterior. Se topa en 7 para que,
                    // con hasta 12 productos por página, la última no
                    // tarde casi un segundo en aparecer — de ahí en
                    // adelante todas entran junto con la octava.
                    style={{ animationDelay: `${Math.min(indice, 7) * 60}ms` }}
                  >
                    <TarjetaProducto producto={producto} />
                  </div>
                ))}
              </div>
            )}

            {!cargando && !error && (
              <Paginacion
                pagina={paginacion.pagina}
                totalPaginas={paginacion.totalPaginas}
                total={paginacion.total}
                onCambiarPagina={handleCambiarPagina}
                deshabilitado={cargando}
              />
            )}
          </div>
        </section>
      </Reveal>
    </main>
  );
}

export default Tienda;
