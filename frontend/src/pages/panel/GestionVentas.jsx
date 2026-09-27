import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Paginacion from "../../components/ui/Paginacion";
import Button from "../../components/ui/Button";
import {
  listarVentas,
  registrarVenta,
  cambiarEstadoVenta,
  generarFactura,
  listarUsuarios,
  listarProductosAdmin,
  listarServiciosAdmin,
  descargarReporteDiarioPdf,
  descargarReporteDiarioExcel,
} from "../../utils/api";
import { formatearPrecio, formatearFecha, obtenerEstadoVenta } from "../../utils/formato";

const VENTAS_POR_PAGINA = 10;
const HOY = new Date().toISOString().slice(0, 10);

/** Un ítem en construcción del formulario "Nueva venta". */
function itemVacio() {
  return { tipo: "producto", id: "", cantidad: 1 };
}

function GestionVentas() {
  // --- Historial ---
  const [ventas, setVentas] = useState([]);
  const [paginacion, setPaginacion] = useState({ pagina: 1, limite: VENTAS_POR_PAGINA, total: 0, totalPaginas: 0 });
  const [filtros, setFiltros] = useState({ fechaInicio: "", fechaFin: "", estado: "" });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [accionandoId, setAccionandoId] = useState(null);

  // --- Catálogos para el formulario ---
  const [clientes, setClientes] = useState([]);
  const [productos, setProductos] = useState([]);
  const [servicios, setServicios] = useState([]);

  // --- Formulario "Nueva venta" ---
  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [clienteId, setClienteId] = useState("");
  const [items, setItems] = useState([itemVacio()]);
  const [descuento, setDescuento] = useState("0");
  const [impuestos, setImpuestos] = useState("0");
  const [notas, setNotas] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [errorFormulario, setErrorFormulario] = useState("");

  // --- Reporte diario ---
  const [fechaReporte, setFechaReporte] = useState(HOY);
  const [descargando, setDescargando] = useState("");

  const cargarVentas = (pagina = 1, filtrosActuales = filtros) => {
    setCargando(true);
    listarVentas({ pagina, limite: VENTAS_POR_PAGINA, ...filtrosActuales })
      .then((respuesta) => {
        setVentas(respuesta.datos);
        setPaginacion(respuesta.paginacion);
      })
      .catch((err) => setError(err.message))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    cargarVentas(1, {});
    listarUsuarios({ pagina: 1, limite: 50 }).then((r) => setClientes(r.datos)).catch(() => {});
    listarProductosAdmin({ pagina: 1, limite: 50 }).then((r) => setProductos(r.datos.filter((p) => p.activo))).catch(() => {});
    listarServiciosAdmin({ pagina: 1, limite: 50 }).then((r) => setServicios(r.datos.filter((s) => s.activo))).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const aplicarFiltros = (evento) => {
    evento.preventDefault();
    cargarVentas(1, filtros);
  };

  const actualizarItem = (indice, campo, valor) => {
    setItems((prev) =>
      prev.map((item, i) => {
        if (i !== indice) return item;

        if (campo === "tipo") {
          return { ...item, tipo: valor, id: "" };
        }

        if (campo === "id") {
          return { ...item, id: valor };
        }

        return { ...item, [campo]: valor };
      })
    );
  };

  const agregarItem = () => setItems((prev) => [...prev, itemVacio()]);
  const quitarItem = (indice) => setItems((prev) => prev.filter((_, i) => i !== indice));

  const precioDe = (item) => {
    const catalogo = item.tipo === "producto" ? productos : servicios;
    const encontrado = catalogo.find((c) => String(c.id) === String(item.id));
    return encontrado ? Number(encontrado.precio) : 0;
  };

  const subtotalEstimado = items.reduce((acum, item) => acum + precioDe(item) * (Number(item.cantidad) || 0), 0);

  const enviarVenta = async (evento) => {
    evento.preventDefault();
    setErrorFormulario("");

    const itemsValidos = items.filter((item) => item.id && Number(item.cantidad) > 0);
    if (!clienteId || itemsValidos.length === 0) {
      setErrorFormulario("Selecciona un cliente y al menos un producto o servicio con cantidad válida.");
      return;
    }

    setGuardando(true);
    try {
      await registrarVenta({
        clienteId: Number(clienteId),
        items: itemsValidos.map((item) => ({
          productoId: item.tipo === "producto" ? Number(item.id) : undefined,
          servicioId: item.tipo === "servicio" ? Number(item.id) : undefined,
          cantidad: Number(item.cantidad),
        })),
        descuento: Number(descuento) || 0,
        impuestos: Number(impuestos) || 0,
        notas: notas || undefined,
      });
      setClienteId("");
      setItems([itemVacio()]);
      setDescuento("0");
      setImpuestos("0");
      setNotas("");
      setMostrarFormulario(false);
      cargarVentas(1, filtros);
    } catch (err) {
      setErrorFormulario(err.message);
    } finally {
      setGuardando(false);
    }
  };

  const anularVenta = async (venta) => {
    setAccionandoId(venta.id);
    try {
      await cambiarEstadoVenta(venta.id, "anulada");
      setVentas((prev) => prev.map((v) => (v.id === venta.id ? { ...v, estado: "anulada" } : v)));
    } catch (err) {
      setError(err.message);
    } finally {
      setAccionandoId(null);
    }
  };

  const facturar = async (venta) => {
    setAccionandoId(venta.id);
    try {
      await generarFactura(venta.id);
      cargarVentas(paginacion.pagina, filtros);
    } catch (err) {
      setError(err.message);
    } finally {
      setAccionandoId(null);
    }
  };

  const descargarReporte = async (formato) => {
    setDescargando(formato);
    try {
      if (formato === "pdf") await descargarReporteDiarioPdf(fechaReporte);
      else await descargarReporteDiarioExcel(fechaReporte);
    } catch (err) {
      setError(err.message);
    } finally {
      setDescargando("");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Reporte diario de ventas — requerimientos 4-6 */}
      <section className="rounded-2xl border border-beige/60 bg-cream p-6">
        <h2 className="text-lg font-semibold text-primary">Reporte diario de ventas</h2>
        <p className="mb-3 text-sm text-primary/70">Exporta las ventas de un día específico en PDF o Excel.</p>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label htmlFor="fechaReporte" className="text-xs font-medium text-primary/70">Fecha</label>
            <input
              id="fechaReporte"
              type="date"
              value={fechaReporte}
              onChange={(e) => setFechaReporte(e.target.value)}
              className="rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
            />
          </div>
          <Button variant="secondary" disabled={descargando === "pdf"} onClick={() => descargarReporte("pdf")}>
            {descargando === "pdf" ? "Generando..." : "Descargar PDF"}
          </Button>
          <Button variant="secondary" disabled={descargando === "excel"} onClick={() => descargarReporte("excel")}>
            {descargando === "excel" ? "Generando..." : "Descargar Excel"}
          </Button>
        </div>
      </section>

      {/* Nueva venta — requerimientos 1-2 */}
      <section className="rounded-2xl border border-beige/60 bg-cream p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-primary">Nueva venta</h2>
          <Button variant="secondary" onClick={() => setMostrarFormulario((v) => !v)}>
            {mostrarFormulario ? "Cancelar" : "Registrar venta"}
          </Button>
        </div>

        {mostrarFormulario && (
          <form onSubmit={enviarVenta} className="flex flex-col gap-4">
            {errorFormulario && (
              <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte dark:bg-peligro dark:text-peligro-fuerte">
                {errorFormulario}
              </p>
            )}

            <div className="flex flex-col gap-1">
              <label htmlFor="cliente" className="text-sm font-medium text-primary/80">Cliente *</label>
              <select
                id="cliente"
                value={clienteId}
                onChange={(e) => setClienteId(e.target.value)}
                className="rounded-lg border border-beige bg-cream px-3 py-2 text-sm text-primary outline-none focus:border-primary"
              >
                <option value="">Selecciona un cliente</option>
                {clientes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre} {c.apellido} — {c.correo}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-2 overflow-visible">
              <p className="text-sm font-medium text-primary/80">Productos / servicios *</p>
              {items.map((item, indice) => (
                <div key={indice} className="relative z-10 flex flex-wrap items-center gap-2 overflow-visible">
                  <select
                    value={item.tipo}
                    onChange={(e) => actualizarItem(indice, "tipo", e.target.value)}
                    className="rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
                  >
                    <option value="producto">Producto</option>
                    <option value="servicio">Servicio</option>
                  </select>
                  <select
                    value={item.id}
                    onChange={(e) => actualizarItem(indice, "id", e.target.value)}
                    className="min-w-[220px] flex-1 rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
                  >
                    <option value="">Selecciona...</option>
                    {(item.tipo === "producto" ? productos : servicios).map((opcion) => (
                      <option key={opcion.id} value={opcion.id}>
                        {opcion.titulo || opcion.nombre} — {formatearPrecio(opcion.precio)}
                        {item.tipo === "producto" ? ` (stock: ${opcion.stock})` : ""}
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    min="1"
                    value={item.cantidad}
                    onChange={(e) => actualizarItem(indice, "cantidad", e.target.value)}
                    className="w-20 rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
                  />
                  {items.length > 1 && (
                    <button
                      type="button"
                      onClick={() => quitarItem(indice)}
                      className="text-sm font-medium text-peligro-fuerte hover:underline"
                    >
                      Quitar
                    </button>
                  )}
                </div>
              ))}
              <button type="button" onClick={agregarItem} className="self-start text-sm font-medium text-primary underline underline-offset-2">
                + Agregar otro ítem
              </button>
            </div>

            <div className="flex flex-wrap gap-4">
              <div className="flex flex-col gap-1">
                <label htmlFor="descuento" className="text-sm font-medium text-primary/80">Descuento</label>
                <input
                  id="descuento"
                  type="number"
                  min="0"
                  step="0.01"
                  value={descuento}
                  onChange={(e) => setDescuento(e.target.value)}
                  className="w-32 rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label htmlFor="impuestos" className="text-sm font-medium text-primary/80">Impuestos</label>
                <input
                  id="impuestos"
                  type="number"
                  min="0"
                  step="0.01"
                  value={impuestos}
                  onChange={(e) => setImpuestos(e.target.value)}
                  className="w-32 rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
                />
              </div>
              <div className="flex flex-1 flex-col gap-1">
                <label htmlFor="notas" className="text-sm font-medium text-primary/80">Notas</label>
                <input
                  id="notas"
                  type="text"
                  maxLength={255}
                  value={notas}
                  onChange={(e) => setNotas(e.target.value)}
                  className="rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
                />
              </div>
            </div>

            <p className="text-sm text-primary/70">
              Subtotal estimado: <span className="font-semibold text-primary">{formatearPrecio(subtotalEstimado)}</span>{" "}
              <span className="text-xs text-primary/40">(el precio y stock reales se confirman en el servidor)</span>
            </p>

            <Button type="submit" disabled={guardando}>
              {guardando ? "Guardando..." : "Registrar venta"}
            </Button>
          </form>
        )}
      </section>

      {/* Historial de ventas — requerimiento 3 */}
      <section className="rounded-2xl border border-beige/60 bg-cream p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-primary">Historial de ventas</h2>
        </div>

        <form onSubmit={aplicarFiltros} className="mb-4 flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-primary/70" htmlFor="fFechaInicio">Desde</label>
            <input
              id="fFechaInicio"
              type="date"
              value={filtros.fechaInicio}
              onChange={(e) => setFiltros((p) => ({ ...p, fechaInicio: e.target.value }))}
              className="rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-primary/70" htmlFor="fFechaFin">Hasta</label>
            <input
              id="fFechaFin"
              type="date"
              value={filtros.fechaFin}
              onChange={(e) => setFiltros((p) => ({ ...p, fechaFin: e.target.value }))}
              className="rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-primary/70" htmlFor="fEstado">Estado</label>
            <select
              id="fEstado"
              value={filtros.estado}
              onChange={(e) => setFiltros((p) => ({ ...p, estado: e.target.value }))}
              className="rounded-md border border-beige bg-cream px-2 py-1.5 text-sm text-primary outline-none focus:border-primary"
            >
              <option value="">Todos</option>
              <option value="completada">Completada</option>
              <option value="anulada">Anulada</option>
            </select>
          </div>
          <Button type="submit" variant="secondary">Filtrar</Button>
        </form>

        {cargando && <p className="text-sm text-primary/70">Cargando ventas...</p>}
        {error && <p className="mb-3 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte dark:bg-peligro dark:text-peligro-fuerte">{error}</p>}

        {!cargando && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-beige/60 text-primary/70">
                  <th className="py-2 pr-3">Venta</th>
                  <th className="py-2 pr-3">Fecha</th>
                  <th className="py-2 pr-3 text-right">Total</th>
                  <th className="py-2 pr-3">Estado</th>
                  <th className="py-2 pr-3" aria-label="Acciones" />
                </tr>
              </thead>
              <tbody>
                {ventas.map((venta) => (
                  <tr key={venta.id} className="border-b border-beige/30">
                    <td className="py-2 pr-3 font-medium text-primary">#{venta.id}</td>
                    <td className="py-2 pr-3 text-primary/70">{formatearFecha(venta.creadoEn)}</td>
                    <td className="py-2 pr-3 text-right font-medium text-primary">{formatearPrecio(venta.total)}</td>
                    <td className="py-2 pr-3">
                      <span
                        className="rounded-full px-2.5 py-1 text-xs font-semibold"
                        style={{
                          color: obtenerEstadoVenta(venta.estado).color,
                          backgroundColor: obtenerEstadoVenta(venta.estado).fondo,
                        }}
                      >
                        {obtenerEstadoVenta(venta.estado).texto}
                      </span>
                    </td>
                    <td className="py-2 pr-3">
                      <div className="flex flex-wrap justify-end gap-3">
                        <button
                          type="button"
                          disabled={accionandoId === venta.id}
                          onClick={() => facturar(venta)}
                          className="text-sm font-medium text-primary underline underline-offset-2 disabled:opacity-50"
                        >
                          Facturar
                        </button>
                        {venta.estado === "completada" && (
                          <button
                            type="button"
                            disabled={accionandoId === venta.id}
                            onClick={() => anularVenta(venta)}
                            className="text-sm font-medium text-peligro-fuerte underline underline-offset-2 disabled:opacity-50"
                          >
                            Anular
                          </button>
                        )}
                        <Link to="/panel/facturas" className="text-sm font-medium text-primary/70 underline underline-offset-2">
                          Ver facturas
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
                {ventas.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-4 text-center text-primary/70">
                      No hay ventas que coincidan con este filtro.
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
          onCambiarPagina={(pagina) => cargarVentas(pagina, filtros)}
          deshabilitado={cargando}
        />
      </section>
    </div>
  );
}

export default GestionVentas;
