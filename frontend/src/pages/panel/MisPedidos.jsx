import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Icon from "../../components/ui/Icon";
import ICON_PATHS from "../../components/ui/iconPaths";
import Paginacion from "../../components/ui/Paginacion";
import { listarPedidos, descargarFacturaPedido } from "../../utils/api";
import { formatearPrecio, formatearFecha, obtenerEstadoPedido } from "../../utils/formato";

const PEDIDOS_POR_PAGINA = 10;

function MisPedidos() {
  const [pedidos, setPedidos] = useState([]);
  const [paginacion, setPaginacion] = useState({ pagina: 1, limite: PEDIDOS_POR_PAGINA, total: 0, totalPaginas: 0 });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  // Id del pedido cuya factura se está generando en este momento (o null):
  // solo uno a la vez, para poder deshabilitar únicamente ESE botón de la
  // tabla y no toda la lista mientras se descarga.
  const [descargandoId, setDescargandoId] = useState(null);
  const [errorFactura, setErrorFactura] = useState("");

  const cargar = (pagina = paginacion.pagina) => {
    listarPedidos({ pagina, limite: PEDIDOS_POR_PAGINA })
      .then((respuesta) => {
        setPedidos(respuesta.datos);
        setPaginacion(respuesta.paginacion);
      })
      .catch((err) => setError(err.message))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    cargar(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCambiarPagina = (paginaNueva) => {
    setCargando(true);
    cargar(paginaNueva);
  };

  const handleDescargarFactura = async (id) => {
    setErrorFactura("");
    setDescargandoId(id);
    try {
      await descargarFacturaPedido(id);
    } catch (err) {
      setErrorFactura(err.message);
    } finally {
      setDescargandoId(null);
    }
  };

  return (
    <section className="rounded-2xl border border-beige/60 bg-cream p-6">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-primary">Mis pedidos</h2>
        <p className="text-sm text-primary/70">El historial de todo lo que has comprado en Dulce Esencia.</p>
      </div>

      {cargando && <p className="text-sm text-primary/70">Cargando tus pedidos...</p>}
      {error && <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{error}</p>}
      {errorFactura && (
        <p className="mb-3 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorFactura}</p>
      )}

      {!cargando && !error && pedidos.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-xl bg-section px-6 py-12 text-center">
          <Icon path={ICON_PATHS.cart} className="h-9 w-9 text-primary/30" />
          <p className="text-primary/70">Todavía no has hecho ningún pedido.</p>
          <Link
            to="/"
            className="inline-block rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-cream transition hover:bg-primary-dark"
          >
            Ver productos
          </Link>
        </div>
      )}

      {!cargando && !error && pedidos.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px] text-left text-sm">
            <thead>
              <tr className="border-b border-beige/60 text-primary/70">
                <th className="py-2 pr-3">Pedido</th>
                <th className="py-2 pr-3">Fecha</th>
                <th className="py-2 pr-3">Estado</th>
                <th className="py-2 pr-3 text-right">Total</th>
                <th className="py-2 pr-3" aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {pedidos.map((pedido) => {
                const estado = obtenerEstadoPedido(pedido.estado);
                return (
                  <tr key={pedido.id} className="border-b border-beige/30">
                    <td className="py-2 pr-3 font-medium text-primary">#{pedido.id}</td>
                    <td className="py-2 pr-3 text-primary/70">{formatearFecha(pedido.creadoEn)}</td>
                    <td className="py-2 pr-3">
                      <span
                        className="rounded-full px-2.5 py-1 text-xs font-semibold"
                        style={{ color: estado.color, backgroundColor: estado.fondo }}
                      >
                        {estado.texto}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-right font-medium text-primary">
                      {formatearPrecio(pedido.total)}
                    </td>
                    <td className="py-2 pr-3 text-right">
                      <div className="flex items-center justify-end gap-3">
                        <button
                          type="button"
                          onClick={() => handleDescargarFactura(pedido.id)}
                          disabled={descargandoId === pedido.id}
                          title="Descargar factura"
                          aria-label={`Descargar factura del pedido ${pedido.id}`}
                          className="text-primary/70 transition hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <Icon path={ICON_PATHS.download} className="h-4 w-4" />
                        </button>
                        <Link
                          to={`/pedidos/${pedido.id}`}
                          className="text-sm font-medium text-primary underline underline-offset-2"
                        >
                          Ver detalle
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {!error && (
        <Paginacion
          pagina={paginacion.pagina}
          totalPaginas={paginacion.totalPaginas}
          total={paginacion.total}
          onCambiarPagina={handleCambiarPagina}
          deshabilitado={cargando}
        />
      )}
    </section>
  );
}

export default MisPedidos;
