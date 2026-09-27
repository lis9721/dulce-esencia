import { useEffect, useState } from "react";
import useForm from "../../hooks/useForm";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import Modal from "../../components/ui/Modal";
import ConfirmModal from "../../components/ui/ConfirmModal";
import Paginacion from "../../components/ui/Paginacion";
import {
  validarNombreServicio,
  validarDescripcionServicio,
  validarImagenServicio,
  validarOrden,
  validarPrecio,
  validarDuracionMinutos,
  validarCodigoServicio,
} from "../../utils/validators";
import { formatearPrecio, resolverUrlImagen } from "../../utils/formato";
import {
  listarServiciosAdmin,
  crearServicio,
  actualizarServicio,
  eliminarServicio,
  subirImagenServicio,
} from "../../utils/api";
import { useAuth } from "../../hooks/useAuth";

const valoresIniciales = {
  nombre: "",
  descripcion: "",
  imagen: "",
  orden: "",
  precio: "",
  duracionMinutos: "",
  codigo: "",
  activo: true,
};
const validadores = {
  nombre: validarNombreServicio,
  descripcion: validarDescripcionServicio,
  imagen: validarImagenServicio,
  orden: validarOrden,
  precio: validarPrecio,
  duracionMinutos: validarDuracionMinutos,
  codigo: validarCodigoServicio,
};
const SERVICIOS_POR_PAGINA = 10;

function GestionServicios() {
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "admin";

  const [servicios, setServicios] = useState([]);
  const [paginacion, setPaginacion] = useState({ pagina: 1, limite: SERVICIOS_POR_PAGINA, total: 0, totalPaginas: 0 });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [modalAbierto, setModalAbierto] = useState(false);
  const [servicioEditando, setServicioEditando] = useState(null); // null = crear
  const [servicioAEliminar, setServicioAEliminar] = useState(null); // null = modal cerrado

  // Mismo patrón que GestionProductos.jsx: la carga inicial ya arranca
  // en true (useState(true) de arriba); recargar (crear/editar/eliminar
  // o cambiar de página) sí vuelve a mostrar el spinner explícitamente.
  const obtenerServicios = (pagina = paginacion.pagina) => {
    // Admin/empleado: /servicios/admin/todos (activos e inactivos) —
    // ver la misma nota en GestionProductos.jsx.
    listarServiciosAdmin({ pagina, limite: SERVICIOS_POR_PAGINA })
      .then((respuesta) => {
        setServicios(respuesta.datos);
        setPaginacion(respuesta.paginacion);
      })
      .catch((err) => setError(err.message))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    obtenerServicios(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const recargarServicios = () => {
    setCargando(true);
    obtenerServicios(paginacion.pagina);
  };

  const handleCambiarPagina = (paginaNueva) => {
    setCargando(true);
    obtenerServicios(paginaNueva);
  };

  const abrirCrear = () => {
    setServicioEditando(null);
    setModalAbierto(true);
  };

  const abrirEditar = (servicio) => {
    setServicioEditando(servicio);
    setModalAbierto(true);
  };

  const handleEliminar = async () => {
    await eliminarServicio(servicioAEliminar.id);
    recargarServicios();
  };

  return (
    <section className="rounded-2xl border border-beige/60 bg-cream p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-primary">Catálogo de servicios</h2>
          <p className="text-sm text-primary/70">
            Crear y editar: admin y empleado · Eliminar: solo admin.
          </p>
        </div>
        <Button onClick={abrirCrear}>+ Nuevo servicio</Button>
      </div>

      {cargando && <p className="text-sm text-primary/70">Cargando servicios...</p>}
      {error && <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{error}</p>}

      {!cargando && !error && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-beige/60 text-primary/70">
                <th className="py-2 pr-3">Orden</th>
                <th className="py-2 pr-3">Nombre</th>
                <th className="py-2 pr-3">Precio</th>
                <th className="py-2 pr-3">Duración</th>
                <th className="py-2 pr-3">Estado</th>
                <th className="py-2 pr-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {servicios.map((servicio) => (
                <tr key={servicio.id} className="border-b border-beige/30">
                  <td className="py-2 pr-3 text-primary/70">{servicio.orden}</td>
                  <td className="py-2 pr-3 font-medium text-primary">{servicio.nombre}</td>
                  <td className="py-2 pr-3 text-primary/70">{formatearPrecio(servicio.precio)}</td>
                  <td className="py-2 pr-3 text-primary/70">
                    {servicio.duracion_minutos ? `${servicio.duracion_minutos} min` : "—"}
                  </td>
                  <td className="py-2 pr-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        servicio.activo
                          ? "bg-exito text-exito-fuerte"
                          : "bg-beige/60 text-primary/70"
                      }`}
                    >
                      {servicio.activo ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="py-2 pr-3">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => abrirEditar(servicio)}
                        className="rounded-md px-2 py-1 text-primary hover:bg-section"
                      >
                        Editar
                      </button>
                      {esAdmin && (
                        <button
                          type="button"
                          onClick={() => setServicioAEliminar(servicio)}
                          className="rounded-md px-2 py-1 text-peligro-fuerte hover:bg-peligro"
                        >
                          Eliminar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {servicios.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-primary/70">
                    Todavía no hay servicios.
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

      <Modal
        isOpen={modalAbierto}
        onClose={() => setModalAbierto(false)}
        title={servicioEditando ? "Editar servicio" : "Nuevo servicio"}
      >
        <FormularioServicio
          servicio={servicioEditando}
          onGuardado={() => {
            setModalAbierto(false);
            recargarServicios();
          }}
        />
      </Modal>

      <ConfirmModal
        isOpen={Boolean(servicioAEliminar)}
        onClose={() => setServicioAEliminar(null)}
        title="Eliminar servicio"
        message={
          servicioAEliminar &&
          `¿Eliminar "${servicioAEliminar.nombre}"? Esta acción no se puede deshacer.`
        }
        onConfirm={handleEliminar}
      />
    </section>
  );
}

function FormularioServicio({ servicio, onGuardado }) {
  const esEdicion = Boolean(servicio);
  const { values, errors, touched, handleChange, handleBlur, validateAll } = useForm(
    servicio
      ? {
          nombre: servicio.nombre,
          descripcion: servicio.descripcion,
          imagen: servicio.imagen ?? "",
          orden: String(servicio.orden ?? ""),
          precio: String(servicio.precio ?? ""),
          duracionMinutos: servicio.duracion_minutos ? String(servicio.duracion_minutos) : "",
          codigo: servicio.codigo ?? "",
          activo: servicio.activo === undefined ? true : Boolean(servicio.activo),
        }
      : valoresIniciales,
    validadores
  );
  const [enviando, setEnviando] = useState(false);
  const [errorServidor, setErrorServidor] = useState("");
  const [subiendoImagen, setSubiendoImagen] = useState(false);
  const [errorImagen, setErrorImagen] = useState("");

  const handleSeleccionarImagen = async (evento) => {
    const archivo = evento.target.files[0];
    if (!archivo) return;

    setErrorImagen("");
    setSubiendoImagen(true);
    try {
      const datos = await subirImagenServicio(archivo);
      handleChange({ target: { name: "imagen", value: datos.rutaImagen, type: "text" } });
    } catch (err) {
      setErrorImagen(err.message);
    } finally {
      setSubiendoImagen(false);
      evento.target.value = "";
    }
  };

  const handleSubmit = async (evento) => {
    evento.preventDefault();
    setErrorServidor("");
    if (!validateAll()) return;

    const payload = {
      nombre: values.nombre.trim(),
      descripcion: values.descripcion.trim(),
      imagen: values.imagen.trim() || undefined,
      orden: values.orden ? Number(values.orden) : 0,
      precio: Number(values.precio),
      duracionMinutos: values.duracionMinutos ? Number(values.duracionMinutos) : undefined,
      codigo: values.codigo.trim() || undefined,
      activo: Boolean(values.activo),
    };

    setEnviando(true);
    try {
      if (esEdicion) {
        await actualizarServicio(servicio.id, payload);
      } else {
        await crearServicio(payload);
      }
      onGuardado();
    } catch (err) {
      setErrorServidor(err.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <Input
        label="Nombre"
        name="nombre"
        required
        maxLength={80}
        value={values.nombre}
        onChange={handleChange}
        onBlur={handleBlur}
        error={errors.nombre}
        touched={touched.nombre}
        placeholder="Torta Personalizada"
      />
      <Input
        label="Descripción"
        name="descripcion"
        required
        maxLength={255}
        value={values.descripcion}
        onChange={handleChange}
        onBlur={handleBlur}
        error={errors.descripcion}
        touched={touched.descripcion}
        placeholder="Diseñamos contigo la torta ideal: sabor, tamaño y decoración."
      />
      <div className="flex flex-col gap-2">
        <label htmlFor="imagenArchivoServicio" className="text-sm font-medium text-primary/80">
          Imagen del servicio (opcional)
        </label>

        {values.imagen && (
          <img
            src={resolverUrlImagen(values.imagen)}
            alt="Vista previa del servicio"
            className="h-24 w-24 rounded-lg border border-beige object-cover"
          />
        )}

        <input
          id="imagenArchivoServicio"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          disabled={subiendoImagen}
          onChange={handleSeleccionarImagen}
          className="text-sm text-primary/80 file:mr-3 file:rounded-lg file:border-0 file:bg-primary file:px-3 file:py-2 file:text-sm file:font-medium file:text-cream file:cursor-pointer hover:file:opacity-90 disabled:opacity-60"
        />

        {subiendoImagen && <p className="text-xs text-primary/70">Subiendo imagen...</p>}
        {errorImagen && <p className="text-xs text-peligro-fuerte">{errorImagen}</p>}
        {!subiendoImagen && !errorImagen && touched.imagen && errors.imagen && (
          <p className="text-xs text-peligro-fuerte">{errors.imagen}</p>
        )}
      </div>
      <Input
        label="Orden"
        name="orden"
        value={values.orden}
        onChange={handleChange}
        onBlur={handleBlur}
        error={errors.orden}
        touched={touched.orden}
        placeholder="1"
      />
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Precio (COP)"
          name="precio"
          type="number"
          required
          value={values.precio}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.precio}
          touched={touched.precio}
          placeholder="45000"
        />
        <Input
          label="Duración (minutos, opcional)"
          name="duracionMinutos"
          type="number"
          value={values.duracionMinutos}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.duracionMinutos}
          touched={touched.duracionMinutos}
          placeholder="30"
        />
      </div>
      <Input
        label="Código (opcional)"
        name="codigo"
        maxLength={30}
        value={values.codigo}
        onChange={handleChange}
        onBlur={handleBlur}
        error={errors.codigo}
        touched={touched.codigo}
        placeholder="SERV-TOR-001"
      />
      <label className="flex items-center gap-2 text-sm text-primary/80">
        <input
          type="checkbox"
          name="activo"
          checked={values.activo}
          onChange={handleChange}
          className="h-4 w-4 rounded border-beige text-accent focus:ring-primary/20"
        />
        Servicio activo (visible en la tienda)
      </label>

      <Button type="submit" fullWidth disabled={enviando}>
        {enviando ? "Guardando..." : esEdicion ? "Guardar cambios" : "Crear servicio"}
      </Button>

      {errorServidor && (
        <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorServidor}</p>
      )}
    </form>
  );
}

export default GestionServicios;
