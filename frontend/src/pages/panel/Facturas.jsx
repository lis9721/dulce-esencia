import { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import Paginacion from "../../components/ui/Paginacion";
import { listarFacturas, descargarFacturaVenta } from "../../utils/api";
import { formatearPrecio, formatearFecha } from "../../utils/formato";

const FACTURAS_POR_PAGINA = 10;

/**
 * Facturas — requerimientos 8-9 del quinto avance.
 * Un cliente ve solo sus propias facturas; admin/empleado ven todas
 * y pueden filtrar por número o fecha (el backend ya resuelve el
 * alcance según el rol, ver GET /api/facturas).
 */
function Facturas() {
  const { usuario } = useAuth();
  const esGestion = usuario?.rol === "admin" || usuario?.rol === "empleado";

  const [facturas, setFacturas] = useState([]);
  const [paginacion, setPaginacion] = useState({ pagina: 1, limite: FACTURAS_POR_PAGINA, total: 0, totalPaginas: 0 });
  const [numero, setNumero] = useState("");
  const [fecha, setFecha] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [descargandoId, setDescargandoId] = useState(null);

  const cargar = (pagina = 1, filtros = { numero, fecha }) => {
    setCargando(true);
    listarFacturas({ pagina, limite: FACTURAS_POR_PAGINA, ...filtros })
      .then((respuesta) => {
        setFacturas(respuesta.datos);
        setPaginacion(respuesta.paginacion);
      })
      .catch((err) => setError(err.message))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    cargar(1, {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const aplicarFiltros = (evento) => {
    evento.preventDefault();
    cargar(1, { numero, fecha });
  };

  const descargar = async (factura) => {
    setDescargandoId(factura.id);
    try {
      await descargarFacturaVenta(factura.id, factura.numero);
    } catch (err) {
      setError(err.message);
    } finally {
      setDescargandoId(null);
    }
  };

  return (
    <section className="rounded-2xl border border-beige/60 bg-cream p-6">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-primary">{esGestion ? "Facturas" : "Mis facturas"}</h2>
        <p className="text-sm text-primary/70">
          {esGestion ? "Todas las facturas de venta emitidas." : "Las facturas generadas a partir de tus compras."}
        </p>
      </div>

      <form onSubmit={aplicarFiltros} className="mb-4 flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <label htmlFor="numero" className="text-xs font-medium text-primary/70">N.º de factura</label>
          <input
            id="numero"
            type="text"
            placeholder="FAC-000001"
            value={numero}
            onChange={(e) => setNumero(e.target.value)}
            className="rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="fecha" className="text-xs font-medium text-primary/70">Fecha</label>
          <input
            id="fecha"
            type="date"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
            className="rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
          />
        </div>
        <button
          type="submit"
          className="rounded-lg border border-primary px-4 py-2 text-sm font-medium text-primary hover:bg-primary/5"
        >
          Buscar
        </button>
      </form>

      {cargando && <p className="text-sm text-primary/70">Cargando facturas...</p>}
      {error && <p className="mb-3 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte dark:bg-peligro dark:text-peligro-fuerte">{error}</p>}

      {!cargando && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-beige/60 text-primary/70">
                <th className="py-2 pr-3">N.º factura</th>
                <th className="py-2 pr-3">Fecha</th>
                <th className="py-2 pr-3 text-right">Total</th>
                <th className="py-2 pr-3">Estado</th>
                <th className="py-2 pr-3" aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {facturas.map((factura) => (
                <tr key={factura.id} className="border-b border-beige/30">
                  <td className="py-2 pr-3 font-medium text-primary">{factura.numero}</td>
                  <td className="py-2 pr-3 text-primary/70">{formatearFecha(factura.creadoEn)}</td>
                  <td className="py-2 pr-3 text-right font-medium text-primary">{formatearPrecio(factura.total)}</td>
                  <td className="py-2 pr-3 capitalize text-primary/70">{factura.estado}</td>
                  <td className="py-2 pr-3 text-right">
                    <button
                      type="button"
                      disabled={descargandoId === factura.id}
                      onClick={() => descargar(factura)}
                      className="text-sm font-medium text-primary underline underline-offset-2 disabled:opacity-50"
                    >
                      {descargandoId === factura.id ? "Descargando..." : "Descargar PDF"}
                    </button>
                  </td>
                </tr>
              ))}
              {facturas.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-primary/70">
                    No hay facturas que coincidan con esta búsqueda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <Paginacion
        pagina={paginacion.pagina}
        totalPaginas={paginacion.totalPaginas}
        total={paginacion.total}
        onCambiarPagina={(pagina) => cargar(pagina, { numero, fecha })}
        deshabilitado={cargando}
      />
    </section>
  );
}

export default Facturas;
