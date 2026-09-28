import { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import StatCard from "../../components/ui/StatCard";
import ICON_PATHS from "../../components/ui/iconPaths";
import BarChart from "../../components/charts/BarChart";
import LineChart from "../../components/charts/LineChart";
import { obtenerEstadisticasAdmin, obtenerEstadisticasVentas } from "../../utils/api";
import { formatearPrecio } from "../../utils/formato";

const HOY = new Date().toISOString().slice(0, 10);
const HACE_30_DIAS = new Date(Date.now() - 29 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

/**
 * Dashboard
 * Requerimientos 10-13 del quinto avance: dashboard administrativo
 * (cards), dashboard de ventas (gráficos de barras/lineal), todo
 * diferenciado por rol y con filtros — y TODO viene de FastAPI
 * (GET /api/estadisticas/*), nada escrito a mano en el frontend
 * (requerimiento 15).
 */
function Dashboard() {
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "admin";

  const [cardsAdmin, setCardsAdmin] = useState(null);
  const [cargandoCards, setCargandoCards] = useState(esAdmin);

  const [filtros, setFiltros] = useState({
    fechaInicio: HACE_30_DIAS,
    fechaFin: HOY,
    agrupacion: "dia",
    estado: "",
    productoId: "",
    servicioId: "",
    clienteId: "",
  });
  const [serie, setSerie] = useState(null);
  const [cargandoSerie, setCargandoSerie] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!esAdmin) return;
    obtenerEstadisticasAdmin()
      .then(setCardsAdmin)
      .catch((err) => setError(err.message))
      .finally(() => setCargandoCards(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [esAdmin]);

  const cargarSerie = (filtrosActuales = filtros) => {
    setCargandoSerie(true);
    obtenerEstadisticasVentas(filtrosActuales)
      .then(setSerie)
      .catch((err) => setError(err.message))
      .finally(() => setCargandoSerie(false));
  };

  useEffect(() => {
    cargarSerie();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const actualizarFiltro = (campo, valor) => {
    setFiltros((prev) => ({ ...prev, [campo]: valor }));
  };

  const aplicarFiltros = (evento) => {
    evento.preventDefault();
    cargarSerie(filtros);
  };

  const datosGrafico = (serie?.serie || []).map((punto) => ({ label: punto.periodo, value: punto.total }));
  const datosGraficoCantidad = (serie?.serie || []).map((punto) => ({ label: punto.periodo, value: punto.cantidadVentas }));

  return (
    <div className="flex flex-col gap-6">
      {error && (
        <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte dark:bg-peligro dark:text-peligro-fuerte">
          {error}
        </p>
      )}

      {esAdmin && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-primary">Resumen general</h2>
          {cargandoCards ? (
            <p className="text-sm text-primary/70">Cargando indicadores...</p>
          ) : (
            cardsAdmin && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                <StatCard icono={ICON_PATHS.users} etiqueta="Usuarios" valor={cardsAdmin.totalUsuarios} />
                <StatCard icono={ICON_PATHS.package} etiqueta="Productos activos" valor={cardsAdmin.totalProductos} acento="sage" />
                <StatCard icono={ICON_PATHS.sparkle} etiqueta="Servicios activos" valor={cardsAdmin.totalServicios} acento="sage" />
                <StatCard icono={ICON_PATHS.cart} etiqueta="Ventas completadas" valor={cardsAdmin.totalVentas} acento="accent" />
                <StatCard icono={ICON_PATHS.receipt} etiqueta="Total facturado" valor={formatearPrecio(cardsAdmin.totalFacturado)} acento="accent" />
                <StatCard icono={ICON_PATHS.chat} etiqueta="PQR pendientes" valor={cardsAdmin.pqrPendientes} acento="blush" />
                <StatCard icono={ICON_PATHS.chat} etiqueta="PQR recibidas" valor={cardsAdmin.pqrRecibidas} acento="blush" />
              </div>
            )
          )}
        </section>
      )}

      <section className="rounded-2xl border border-beige/60 bg-cream p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-primary">Ventas</h2>
            <p className="text-sm text-primary/70">Comportamiento de las ventas en el período seleccionado.</p>
          </div>
        </div>

        <form onSubmit={aplicarFiltros} className="mb-5 flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-primary/70" htmlFor="fechaInicio">Desde</label>
            <input
              id="fechaInicio"
              type="date"
              value={filtros.fechaInicio}
              onChange={(e) => actualizarFiltro("fechaInicio", e.target.value)}
              className="rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-primary/70" htmlFor="fechaFin">Hasta</label>
            <input
              id="fechaFin"
              type="date"
              value={filtros.fechaFin}
              onChange={(e) => actualizarFiltro("fechaFin", e.target.value)}
              className="rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-primary/70" htmlFor="agrupacion">Agrupar por</label>
            <select
              id="agrupacion"
              value={filtros.agrupacion}
              onChange={(e) => actualizarFiltro("agrupacion", e.target.value)}
              className="rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
            >
              <option value="dia">Día</option>
              <option value="semana">Semana</option>
              <option value="mes">Mes</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-primary/70" htmlFor="estado">Estado</label>
            <select
              id="estado"
              value={filtros.estado}
              onChange={(e) => actualizarFiltro("estado", e.target.value)}
              className="rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
            >
              <option value="">Completadas</option>
              <option value="anulada">Anuladas</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-primary/70" htmlFor="productoId">Producto ID</label>
            <input
              id="productoId"
              type="number"
              min="1"
              placeholder="Todos"
              value={filtros.productoId}
              onChange={(e) => actualizarFiltro("productoId", e.target.value)}
              className="w-24 rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-primary/70" htmlFor="servicioId">Servicio ID</label>
            <input
              id="servicioId"
              type="number"
              min="1"
              placeholder="Todos"
              value={filtros.servicioId}
              onChange={(e) => actualizarFiltro("servicioId", e.target.value)}
              className="w-24 rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-primary/70" htmlFor="clienteId">Cliente ID</label>
            <input
              id="clienteId"
              type="number"
              min="1"
              placeholder="Todos"
              value={filtros.clienteId}
              onChange={(e) => actualizarFiltro("clienteId", e.target.value)}
              className="w-24 rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-cream transition hover:bg-primary-dark"
          >
            Filtrar
          </button>
        </form>

        {cargandoSerie ? (
          <p className="text-sm text-primary/70">Cargando gráficos...</p>
        ) : (
          <>
            <div className="mb-4 flex flex-wrap gap-3">
              <StatCard etiqueta="Ventas en el período" valor={serie?.cantidadVentasPeriodo ?? 0} />
              <StatCard etiqueta="Total del período" valor={formatearPrecio(serie?.totalPeriodo ?? 0)} acento="accent" />
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <div>
                <p className="mb-2 text-sm font-medium text-primary/70">Total vendido por período</p>
                <BarChart data={datosGrafico} formatoValor={(v) => formatearPrecio(v)} />
              </div>
              <div>
                <p className="mb-2 text-sm font-medium text-primary/70">Cantidad de ventas por período</p>
                <LineChart data={datosGraficoCantidad} />
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}

export default Dashboard;
