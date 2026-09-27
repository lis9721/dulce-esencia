import { useEffect, useMemo, useState } from "react";
import useForm from "../../hooks/useForm";
import Input from "../../components/ui/Input";
import Select from "../../components/ui/Select";
import Textarea from "../../components/ui/Textarea";
import Button from "../../components/ui/Button";
import Modal from "../../components/ui/Modal";
import ConfirmModal from "../../components/ui/ConfirmModal";
import Paginacion from "../../components/ui/Paginacion";
import Icon from "../../components/ui/Icon";
import ICON_PATHS from "../../components/ui/iconPaths";
import CATEGORIAS_PROVEEDOR from "../../constants/categoriasProveedor";
import {
  validarRazonSocial,
  validarNit,
  validarCategoriaProveedor,
  validarContactoNombre,
  validarCorreoProveedor,
  validarTelefonoProveedor,
  validarCiudadProveedor,
  validarDireccionProveedor,
  validarSitioWebProveedor,
  validarDiasCredito,
  validarCupoCredito,
  validarMotivoSuspension,
} from "../../utils/validators";
import { formatearPrecio } from "../../utils/formato";
import {
  listarProveedores,
  crearProveedor,
  actualizarProveedor,
  eliminarProveedor,
  suspenderProveedor,
  reactivarProveedor,
} from "../../utils/api";
import { useAuth } from "../../hooks/useAuth";

const ESTADOS_PROVEEDOR = [
  { value: "activo", label: "Activo" },
  { value: "suspendido", label: "Suspendido" },
];

const valoresIniciales = {
  razonSocial: "",
  nit: "",
  categoria: "",
  contactoNombre: "",
  correo: "",
  telefono: "",
  ciudad: "",
  direccion: "",
  sitioWeb: "",
  diasCredito: "0",
  cupoCredito: "0",
};

const validadores = {
  razonSocial: validarRazonSocial,
  nit: validarNit,
  categoria: validarCategoriaProveedor,
  contactoNombre: validarContactoNombre,
  correo: validarCorreoProveedor,
  telefono: validarTelefonoProveedor,
  ciudad: validarCiudadProveedor,
  direccion: validarDireccionProveedor,
  sitioWeb: validarSitioWebProveedor,
  diasCredito: validarDiasCredito,
  cupoCredito: validarCupoCredito,
};

const PROVEEDORES_POR_PAGINA = 10;

function proveedorAValoresFormulario(proveedor) {
  return {
    razonSocial: proveedor.razonSocial,
    nit: proveedor.nit,
    categoria: proveedor.categoria,
    contactoNombre: proveedor.contactoNombre,
    correo: proveedor.correo,
    telefono: proveedor.telefono,
    ciudad: proveedor.ciudad,
    direccion: proveedor.direccion || "",
    sitioWeb: proveedor.sitioWeb || "",
    diasCredito: String(proveedor.diasCredito ?? 0),
    cupoCredito: String(proveedor.cupoCredito ?? 0),
  };
}

/** "activo" -> pastel menta + tinta legible; "suspendido" -> pastel de aviso. */
function badgeEstado(estado) {
  if (estado === "activo") return "bg-exito text-exito-fuerte";
  return "bg-aviso text-aviso-fuerte";
}

function GestionProveedores() {
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "admin";

  const [proveedores, setProveedores] = useState([]);
  const [paginacion, setPaginacion] = useState({ pagina: 1, limite: PROVEEDORES_POR_PAGINA, total: 0, totalPaginas: 0 });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

  // Filtros del panel (criterio 22: al menos tres filtros opcionales).
  const [filtroCategoria, setFiltroCategoria] = useState("");
  const [filtroEstado, setFiltroEstado] = useState("");
  const [filtroBuscar, setFiltroBuscar] = useState("");

  const [modalAbierto, setModalAbierto] = useState(false);
  const [proveedorEditando, setProveedorEditando] = useState(null); // null = crear
  const [proveedorAEliminar, setProveedorAEliminar] = useState(null);
  const [proveedorASuspender, setProveedorASuspender] = useState(null);
  const [motivoSuspension, setMotivoSuspension] = useState("");
  const [errorSuspension, setErrorSuspension] = useState("");
  const [enviandoSuspension, setEnviandoSuspension] = useState(false);

  const {
    values,
    errors,
    touched,
    handleChange,
    handleBlur,
    validateAll,
    resetForm,
    setValues,
  } = useForm(valoresIniciales, validadores);

  const [enviando, setEnviando] = useState(false);
  const [errorFormulario, setErrorFormulario] = useState("");

  const obtenerProveedores = (pagina = paginacion.pagina) => {
    listarProveedores({
      pagina,
      limite: PROVEEDORES_POR_PAGINA,
      categoria: filtroCategoria || undefined,
      estado: filtroEstado || undefined,
      buscar: filtroBuscar || undefined,
    })
      .then((respuesta) => {
        setProveedores(respuesta.datos);
        setPaginacion(respuesta.paginacion);
        setError("");
      })
      .catch((err) => setError(err.message))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    setCargando(true);
    obtenerProveedores(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroCategoria, filtroEstado, filtroBuscar]);

  const recargar = () => {
    setCargando(true);
    obtenerProveedores(paginacion.pagina);
  };

  const handleCambiarPagina = (paginaNueva) => {
    setCargando(true);
    obtenerProveedores(paginaNueva);
  };

  const abrirCrear = () => {
    setProveedorEditando(null);
    resetForm();
    setErrorFormulario("");
    setModalAbierto(true);
  };

  const abrirEditar = (proveedor) => {
    setProveedorEditando(proveedor);
    setValues(proveedorAValoresFormulario(proveedor));
    setErrorFormulario("");
    setModalAbierto(true);
  };

  const cerrarModal = () => {
    if (enviando) return;
    setModalAbierto(false);
  };

  const handleGuardar = async (evento) => {
    evento.preventDefault();
    if (!validateAll()) return;

    const cuerpo = {
      razonSocial: values.razonSocial,
      nit: values.nit,
      categoria: values.categoria,
      contactoNombre: values.contactoNombre,
      correo: values.correo,
      telefono: values.telefono,
      ciudad: values.ciudad,
      direccion: values.direccion || null,
      sitioWeb: values.sitioWeb || null,
      diasCredito: Number(values.diasCredito),
      cupoCredito: values.cupoCredito,
    };

    setEnviando(true);
    setErrorFormulario("");
    try {
      if (proveedorEditando) {
        await actualizarProveedor(proveedorEditando.id, cuerpo);
      } else {
        await crearProveedor(cuerpo);
      }
      setModalAbierto(false);
      recargar();
    } catch (err) {
      setErrorFormulario(err.message);
    } finally {
      setEnviando(false);
    }
  };

  const handleEliminar = async () => {
    await eliminarProveedor(proveedorAEliminar.id);
    recargar();
  };

  const abrirSuspender = (proveedor) => {
    setProveedorASuspender(proveedor);
    setMotivoSuspension("");
    setErrorSuspension("");
  };

  const cerrarSuspender = () => {
    if (enviandoSuspension) return;
    setProveedorASuspender(null);
  };

  const handleConfirmarSuspension = async () => {
    const mensajeError = validarMotivoSuspension(motivoSuspension);
    if (mensajeError) {
      setErrorSuspension(mensajeError);
      return;
    }
    setEnviandoSuspension(true);
    setErrorSuspension("");
    try {
      await suspenderProveedor(proveedorASuspender.id, motivoSuspension);
      setProveedorASuspender(null);
      recargar();
    } catch (err) {
      setErrorSuspension(err.message);
    } finally {
      setEnviandoSuspension(false);
    }
  };

  const handleReactivar = async (proveedor) => {
    setError("");
    try {
      await reactivarProveedor(proveedor.id);
      recargar();
    } catch (err) {
      setError(err.message);
    }
  };

  const opcionesCategoriaConTodas = useMemo(
    () => [{ value: "", label: "Todas las categorías" }, ...CATEGORIAS_PROVEEDOR],
    []
  );

  return (
    <section className="rounded-2xl border border-beige/60 bg-cream p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-primary">Proveedores</h2>
          <p className="text-sm text-primary/70">
            Crear, editar y suspender: admin y empleado · Eliminar: solo admin.
          </p>
        </div>
        <Button onClick={abrirCrear}>
          <Icon path={ICON_PATHS.plus} className="h-4 w-4" />
          Nuevo proveedor
        </Button>
      </div>

      {/* Filtros: categoría, estado y búsqueda por texto (criterio 22). */}
      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <div className="relative">
          <Icon
            path={ICON_PATHS.search}
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-primary/40"
          />
          <input
            type="text"
            value={filtroBuscar}
            onChange={(evento) => setFiltroBuscar(evento.target.value)}
            placeholder="Buscar por razón social, NIT o contacto..."
            className="w-full rounded-lg border border-beige bg-cream py-2 pl-9 pr-3 text-sm text-primary outline-none transition placeholder:text-primary/40 focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <select
          value={filtroCategoria}
          onChange={(evento) => setFiltroCategoria(evento.target.value)}
          className="rounded-lg border border-beige bg-cream px-3 py-2 text-sm text-primary outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
        >
          {opcionesCategoriaConTodas.map((opcion) => (
            <option key={opcion.value} value={opcion.value}>
              {opcion.label}
            </option>
          ))}
        </select>
        <select
          value={filtroEstado}
          onChange={(evento) => setFiltroEstado(evento.target.value)}
          className="rounded-lg border border-beige bg-cream px-3 py-2 text-sm text-primary outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
        >
          <option value="">Todos los estados</option>
          {ESTADOS_PROVEEDOR.map((opcion) => (
            <option key={opcion.value} value={opcion.value}>
              {opcion.label}
            </option>
          ))}
        </select>
      </div>

      {cargando && <p className="text-sm text-primary/70">Cargando proveedores...</p>}
      {error && <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{error}</p>}

      {!cargando && !error && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-beige/60 text-primary/70">
                <th className="py-2 pr-3">Razón social</th>
                <th className="py-2 pr-3">NIT</th>
                <th className="py-2 pr-3">Categoría</th>
                <th className="py-2 pr-3">Ciudad</th>
                <th className="py-2 pr-3">Crédito</th>
                <th className="py-2 pr-3">Productos</th>
                <th className="py-2 pr-3">Estado</th>
                <th className="py-2 pr-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {proveedores.map((proveedor) => (
                <tr key={proveedor.id} className="border-b border-beige/30">
                  <td className="py-2 pr-3 font-medium text-primary">
                    {proveedor.razonSocial}
                    <p className="text-xs font-normal text-primary/70">{proveedor.contactoNombre}</p>
                  </td>
                  <td className="py-2 pr-3 text-primary/70">{proveedor.nit}</td>
                  <td className="py-2 pr-3 text-primary/70">
                    {CATEGORIAS_PROVEEDOR.find((c) => c.value === proveedor.categoria)?.label ??
                      proveedor.categoria}
                  </td>
                  <td className="py-2 pr-3 text-primary/70">{proveedor.ciudad}</td>
                  <td className="py-2 pr-3 text-primary/70">
                    {proveedor.diasCredito > 0
                      ? `${proveedor.diasCredito} días · ${formatearPrecio(proveedor.cupoCredito)}`
                      : "Contado"}
                  </td>
                  <td className="py-2 pr-3 text-primary/70">{proveedor.totalProductos}</td>
                  <td className="py-2 pr-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badgeEstado(proveedor.estado)}`}>
                      {proveedor.estado === "activo" ? "Activo" : "Suspendido"}
                    </span>
                  </td>
                  <td className="py-2 pr-3">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => abrirEditar(proveedor)}
                        className="rounded-md px-2 py-1 text-primary hover:bg-section"
                      >
                        Editar
                      </button>
                      {proveedor.estado === "activo" ? (
                        <button
                          type="button"
                          onClick={() => abrirSuspender(proveedor)}
                          className="rounded-md px-2 py-1 text-aviso-fuerte hover:bg-aviso"
                        >
                          Suspender
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleReactivar(proveedor)}
                          className="rounded-md px-2 py-1 text-exito-fuerte hover:bg-exito"
                        >
                          Reactivar
                        </button>
                      )}
                      {esAdmin && (
                        <button
                          type="button"
                          onClick={() => setProveedorAEliminar(proveedor)}
                          className="rounded-md px-2 py-1 text-peligro-fuerte hover:bg-peligro"
                        >
                          Eliminar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {proveedores.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-6 text-center text-primary/70">
                    No hay proveedores que coincidan con los filtros.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <Paginacion
            pagina={paginacion.pagina}
            totalPaginas={paginacion.totalPaginas}
            total={paginacion.total}
            onCambiarPagina={handleCambiarPagina}
          />
        </div>
      )}

      {/* -------------------------- Crear / editar -------------------------- */}
      <Modal
        isOpen={modalAbierto}
        onClose={cerrarModal}
        title={proveedorEditando ? "Editar proveedor" : "Nuevo proveedor"}
      >
        <form onSubmit={handleGuardar} className="flex flex-col gap-4">
          {errorFormulario && (
            <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorFormulario}</p>
          )}

          <Input
            label="Razón social"
            name="razonSocial"
            value={values.razonSocial}
            onChange={handleChange}
            onBlur={handleBlur}
            error={errors.razonSocial}
            touched={touched.razonSocial}
            maxLength={120}
            required
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="NIT"
              name="nit"
              value={values.nit}
              onChange={handleChange}
              onBlur={handleBlur}
              error={errors.nit}
              touched={touched.nit}
              placeholder="900412873-6"
              required
            />
            <Select
              label="Categoría"
              name="categoria"
              value={values.categoria}
              onChange={handleChange}
              onBlur={handleBlur}
              error={errors.categoria}
              touched={touched.categoria}
              options={CATEGORIAS_PROVEEDOR}
              required
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Nombre de contacto"
              name="contactoNombre"
              value={values.contactoNombre}
              onChange={handleChange}
              onBlur={handleBlur}
              error={errors.contactoNombre}
              touched={touched.contactoNombre}
              maxLength={80}
              required
            />
            <Input
              label="Correo corporativo"
              name="correo"
              type="email"
              value={values.correo}
              onChange={handleChange}
              onBlur={handleBlur}
              error={errors.correo}
              touched={touched.correo}
              required
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Teléfono"
              name="telefono"
              value={values.telefono}
              onChange={handleChange}
              onBlur={handleBlur}
              error={errors.telefono}
              touched={touched.telefono}
              placeholder="+57 (602) 322-1144"
              required
            />
            <Input
              label="Ciudad"
              name="ciudad"
              value={values.ciudad}
              onChange={handleChange}
              onBlur={handleBlur}
              error={errors.ciudad}
              touched={touched.ciudad}
              maxLength={60}
              required
            />
          </div>

          <Input
            label="Dirección (opcional)"
            name="direccion"
            value={values.direccion}
            onChange={handleChange}
            onBlur={handleBlur}
            error={errors.direccion}
            touched={touched.direccion}
            maxLength={160}
          />

          <Input
            label="Sitio web (opcional)"
            name="sitioWeb"
            value={values.sitioWeb}
            onChange={handleChange}
            onBlur={handleBlur}
            error={errors.sitioWeb}
            touched={touched.sitioWeb}
            placeholder="https://..."
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Días de crédito"
              name="diasCredito"
              type="number"
              value={values.diasCredito}
              onChange={handleChange}
              onBlur={handleBlur}
              error={errors.diasCredito}
              touched={touched.diasCredito}
              required
            />
            <Input
              label="Cupo de crédito (COP)"
              name="cupoCredito"
              type="number"
              value={values.cupoCredito}
              onChange={handleChange}
              onBlur={handleBlur}
              error={errors.cupoCredito}
              touched={touched.cupoCredito}
              required
            />
          </div>
          <p className="-mt-2 text-xs text-primary/70">
            Usa 0 y 0 para pago de contado. Un plazo mayor a 0 exige un cupo mayor a 0, y viceversa.
          </p>

          <div className="mt-2 flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={cerrarModal} disabled={enviando}>
              Cancelar
            </Button>
            <Button type="submit" disabled={enviando}>
              {enviando ? "Guardando..." : proveedorEditando ? "Guardar cambios" : "Registrar proveedor"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* ------------------------------ Suspender ---------------------------- */}
      <Modal isOpen={Boolean(proveedorASuspender)} onClose={cerrarSuspender} title="Suspender proveedor">
        <p className="text-sm text-primary/80">
          {proveedorASuspender &&
            `Se suspenderá a "${proveedorASuspender.razonSocial}" y se retirarán del catálogo público todos sus productos activos.`}
        </p>
        <Textarea
          label="Motivo de la suspensión"
          name="motivoSuspension"
          value={motivoSuspension}
          onChange={(evento) => setMotivoSuspension(evento.target.value)}
          maxLength={200}
          required
        />
        {errorSuspension && (
          <p className="mt-2 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorSuspension}</p>
        )}
        <div className="mt-4 flex justify-end gap-3">
          <Button variant="ghost" onClick={cerrarSuspender} disabled={enviandoSuspension}>
            Cancelar
          </Button>
          <Button variant="danger" onClick={handleConfirmarSuspension} disabled={enviandoSuspension}>
            {enviandoSuspension ? "Suspendiendo..." : "Suspender"}
          </Button>
        </div>
      </Modal>

      {/* ------------------------------ Eliminar ------------------------------ */}
      <ConfirmModal
        isOpen={Boolean(proveedorAEliminar)}
        onClose={() => setProveedorAEliminar(null)}
        title="Eliminar proveedor"
        message={
          proveedorAEliminar &&
          `¿Eliminar "${proveedorAEliminar.razonSocial}"? Esta acción no se puede deshacer. Si el proveedor todavía tiene productos asociados, el servidor rechazará la eliminación.`
        }
        onConfirm={handleEliminar}
      />
    </section>
  );
}

export default GestionProveedores;
