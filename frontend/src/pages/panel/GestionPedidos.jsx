import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Paginacion from "../../components/ui/Paginacion";
import { listarPedidos, cambiarEstadoPedido } from "../../utils/api";
import { formatearPrecio, formatearFecha, obtenerEstadoPedido } from "../../utils/formato";

const PEDIDOS_POR_PAGINA = 10;
const ESTADOS = ["pendiente", "pagado", "enviado", "entregado", "cancelado"];
const ESTADOS_TERMINALES = ["entregado", "cancelado"];

function GestionPedidos() {
  const [pedidos, setPedidos] = useState([]);
  const [paginacion, setPaginacion] = useState({ pagina: 1, limite: PEDIDOS_POR_PAGINA, total: 0, totalPaginas: 0 });
  const [filtroEstado, setFiltroEstado] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [guardandoId, setGuardandoId] = useState(null);
  const [errorEstado, setErrorEstado] = useState("");

  const cargar = (pagina = 1, estado = filtroEstado) => {
    setCargando(true);
    listarPedidos({ pagina, limite: PEDIDOS_POR_PAGINA, estado })
      .then((respuesta) => {
        setPedidos(respuesta.datos);
        setPaginacion(respuesta.paginacion);
      })
      .catch((err) => setError(err.message))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    cargar(1, "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCambiarFiltro = (estadoNuevo) => {
    setFiltroEstado(estadoNuevo);
    cargar(1, estadoNuevo);
  };

  const handleCambiarPagina = (paginaNueva) => {
    cargar(paginaNueva, filtroEstado);
  };

  const handleCambiarEstado = async (pedido, estadoNuevo) => {
    setGuardandoId(pedido.id);
    setErrorEstado("");
    try {
      await cambiarEstadoPedido(pedido.id, estadoNuevo);
      setPedidos((prev) => prev.map((p) => (p.id === pedido.id ? { ...p, estado: estadoNuevo } : p)));
    } catch (err) {
      // Ej. un pedido que YA estaba entregado/cancelado (409): se avisa
      // acá arriba de la tabla en vez de dejar el select en un estado
      // que el backend en realidad rechazó.
      setErrorEstado(err.message);
    } finally {
      setGuardandoId(null);
    }
  };

  return (
    <section className="rounded-2xl border border-beige/60 bg-cream p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-primary">Pedidos</h2>
          <p className="text-sm text-primary/70">Todos los pedidos de la tienda. Cambia el estado a medida que avanzan.</p>
        </div>
        <select
          value={filtroEstado}
          onChange={(evento) => handleCambiarFiltro(evento.target.value)}
          className="rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
          aria-label="Filtrar por estado"
        >
          <option value="">Todos los estados</option>
          {ESTADOS.map((estado) => (
            <option key={estado} value={estado}>
              {obtenerEstadoPedido(estado).texto}
            </option>
          ))}
        </select>
      </div>

      {cargando && <p className="text-sm text-primary/70">Cargando pedidos...</p>}
      {error && <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{error}</p>}
      {errorEstado && (
        <p className="mb-4 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorEstado}</p>
      )}

      {!cargando && !error && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-beige/60 text-primary/70">
                <th className="py-2 pr-3">Pedido</th>
                <th className="py-2 pr-3">Cliente</th>
                <th className="py-2 pr-3">Fecha</th>
                <th className="py-2 pr-3 text-right">Total</th>
                <th className="py-2 pr-3">Estado</th>
                <th className="py-2 pr-3" aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {pedidos.map((pedido) => {
                const esTerminal = ESTADOS_TERMINALES.includes(pedido.estado);
                return (
                  <tr key={pedido.id} className="border-b border-beige/30">
                    <td className="py-2 pr-3 font-medium text-primary">#{pedido.id}</td>
                    <td className="py-2 pr-3 text-primary/70">{pedido.correoUsuario}</td>
                    <td className="py-2 pr-3 text-primary/70">{formatearFecha(pedido.creadoEn)}</td>
                    <td className="py-2 pr-3 text-right font-medium text-primary">
                      {formatearPrecio(pedido.total)}
                    </td>
                    <td className="py-2 pr-3">
                      {esTerminal ? (
                        <span
                          className="rounded-full px-2.5 py-1 text-xs font-semibold"
                          style={{
                            color: obtenerEstadoPedido(pedido.estado).color,
                            backgroundColor: obtenerEstadoPedido(pedido.estado).fondo,
                          }}
                        >
                          {obtenerEstadoPedido(pedido.estado).texto}
                        </span>
                      ) : (
                        <select
                          value={pedido.estado}
                          disabled={guardandoId === pedido.id}
                          onChange={(evento) => handleCambiarEstado(pedido, evento.target.value)}
                          className="rounded-md border border-beige bg-cream px-2 py-1 text-sm text-primary outline-none focus:border-primary"
                        >
                          {ESTADOS.map((estado) => (
                            <option key={estado} value={estado}>
                              {obtenerEstadoPedido(estado).texto}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td className="py-2 pr-3 text-right">
                      <Link
                        to={`/pedidos/${pedido.id}`}
                        className="text-sm font-medium text-primary underline underline-offset-2"
                      >
                        Ver detalle
                      </Link>
                    </td>
                  </tr>
                );
              })}
              {pedidos.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-primary/70">
                    No hay pedidos que coincidan con este filtro.
                  </td>
                </tr>
              )}
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

export default GestionPedidos;
