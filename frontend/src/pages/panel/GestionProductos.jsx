import { useEffect, useState } from "react";
import useForm from "../../hooks/useForm";
import Input from "../../components/ui/Input";
import Select from "../../components/ui/Select";
import Button from "../../components/ui/Button";
import Modal from "../../components/ui/Modal";
import ConfirmModal from "../../components/ui/ConfirmModal";
import Paginacion from "../../components/ui/Paginacion";
import FAMILIAS_PRODUCTO from "../../constants/familiasProducto";
import {
  validarTitulo,
  validarDescripcionProducto,
  validarImagen,
  validarOrden,
  validarPrecio,
  validarStock,
  validarSku,
  validarFamilia,
  validarPesoG,
} from "../../utils/validators";
import { formatearPrecio, resolverUrlImagen } from "../../utils/formato";
import {
  listarProductosAdmin,
  crearProducto,
  actualizarProducto,
  eliminarProducto,
  subirImagenProducto,
  listarProveedores,
} from "../../utils/api";
import { useAuth } from "../../hooks/useAuth";

const valoresIniciales = {
  titulo: "",
  descripcion: "",
  imagen: "",
  orden: "",
  precio: "",
  stock: "",
  sku: "",
  familia: "",
  pesoG: "",
  activo: true,
  proveedorId: "",
};
const validadores = {
  titulo: validarTitulo,
  descripcion: validarDescripcionProducto,
  imagen: validarImagen,
  orden: validarOrden,
  precio: validarPrecio,
  stock: validarStock,
  sku: validarSku,
  familia: validarFamilia,
  pesoG: validarPesoG,
};
const PRODUCTOS_POR_PAGINA = 10;

function GestionProductos() {
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "admin";

  const [productos, setProductos] = useState([]);
  const [paginacion, setPaginacion] = useState({ pagina: 1, limite: PRODUCTOS_POR_PAGINA, total: 0, totalPaginas: 0 });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [modalAbierto, setModalAbierto] = useState(false);
  const [productoEditando, setProductoEditando] = useState(null); // null = crear
  const [productoAEliminar, setProductoAEliminar] = useState(null); // null = modal cerrado

  // `obtenerProductos` no marca "cargando" a true por sí misma: la carga
  // inicial ya arranca en true (useState(true) de arriba). Para recargar
  // después de crear/editar/eliminar, o al cambiar de página, sí
  // queremos mostrar el spinner de nuevo — eso lo hacen los wrappers
  // `recargarProductos` y `handleCambiarPagina` de abajo.
  const obtenerProductos = (pagina = paginacion.pagina) => {
    // Admin/empleado: usa /productos/admin/todos (activos E inactivos),
    // no la ruta pública, o el panel nunca podría reactivar un producto
    // que ya fue desactivado (ver CAMBIOS-SESION-ACTUAL.md, punto 4).
    listarProductosAdmin({ pagina, limite: PRODUCTOS_POR_PAGINA })
      .then((respuesta) => {
        setProductos(respuesta.datos);
        setPaginacion(respuesta.paginacion);
      })
      .catch((err) => setError(err.message))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    obtenerProductos(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const recargarProductos = () => {
    setCargando(true);
    // Tras crear/editar/eliminar se vuelve a pedir la página ACTUAL
    // (no siempre la 1): así un producto editado en la página 2 sigue
    // viéndose en la página 2 después de guardar.
    obtenerProductos(paginacion.pagina);
  };

  const handleCambiarPagina = (paginaNueva) => {
    setCargando(true);
    obtenerProductos(paginaNueva);
  };

  const abrirCrear = () => {
    setProductoEditando(null);
    setModalAbierto(true);
  };

  const abrirEditar = (producto) => {
    setProductoEditando(producto);
    setModalAbierto(true);
  };

  const handleEliminar = async () => {
    await eliminarProducto(productoAEliminar.id);
    // Se recarga la página actual desde el servidor (no solo se filtra
    // en memoria) para que "total"/"totalPaginas" queden correctos y no
    // se muestre una página vacía de más si era la última fila de la
    // última página.
    recargarProductos();
  };

  return (
    <section className="rounded-2xl border border-beige/60 bg-cream p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-primary">Catálogo de productos</h2>
          <p className="text-sm text-primary/70">
            Crear y editar: admin y empleado · Eliminar: solo admin.
          </p>
        </div>
        <Button onClick={abrirCrear}>+ Nuevo producto</Button>
      </div>

      {cargando && <p className="text-sm text-primary/70">Cargando productos...</p>}
      {error && <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{error}</p>}

      {!cargando && !error && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-beige/60 text-primary/70">
                <th className="py-2 pr-3">Orden</th>
                <th className="py-2 pr-3">Título</th>
                <th className="py-2 pr-3">Categoría</th>
                <th className="py-2 pr-3">Peso</th>
                <th className="py-2 pr-3">Precio</th>
                <th className="py-2 pr-3">Stock</th>
                <th className="py-2 pr-3">Proveedor</th>
                <th className="py-2 pr-3">Estado</th>
                <th className="py-2 pr-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {productos.map((producto) => (
                <tr key={producto.id} className="border-b border-beige/30">
                  <td className="py-2 pr-3 text-primary/70">{producto.orden}</td>
                  <td className="py-2 pr-3 font-medium text-primary">{producto.titulo}</td>
                  <td className="py-2 pr-3 text-primary/70">
                    {FAMILIAS_PRODUCTO.find((f) => f.value === producto.familia)?.label ??
                      producto.familia}
                  </td>
                  <td className="py-2 pr-3 text-primary/70">
                    {producto.pesoG != null ? `${producto.pesoG} g` : "—"}
                  </td>
                  <td className="py-2 pr-3 text-primary/70">{formatearPrecio(producto.precio)}</td>
                  <td className="py-2 pr-3 text-primary/70">{producto.stock}</td>
                  <td className="py-2 pr-3 text-primary/70">
                    {producto.proveedor?.razonSocial ?? "—"}
                  </td>
                  <td className="py-2 pr-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        producto.activo
                          ? "bg-exito text-exito-fuerte"
                          : "bg-beige/60 text-primary/70"
                      }`}
                    >
                      {producto.activo ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="py-2 pr-3">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => abrirEditar(producto)}
                        className="rounded-md px-2 py-1 text-primary hover:bg-section"
                      >
                        Editar
                      </button>
                      {esAdmin && (
                        <button
                          type="button"
                          onClick={() => setProductoAEliminar(producto)}
                          className="rounded-md px-2 py-1 text-peligro-fuerte hover:bg-peligro"
                        >
                          Eliminar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {productos.length === 0 && (
                <tr>
                  <td colSpan={9} className="py-4 text-center text-primary/70">
                    Todavía no hay productos.
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
        title={productoEditando ? "Editar producto" : "Nuevo producto"}
      >
        <FormularioProducto
          producto={productoEditando}
          onGuardado={() => {
            setModalAbierto(false);
            recargarProductos();
          }}
        />
      </Modal>

      <ConfirmModal
        isOpen={Boolean(productoAEliminar)}
        onClose={() => setProductoAEliminar(null)}
        title="Eliminar producto"
        message={
          productoAEliminar &&
          `¿Eliminar "${productoAEliminar.titulo}"? Esta acción no se puede deshacer.`
        }
        onConfirm={handleEliminar}
      />
    </section>
  );
}

function FormularioProducto({ producto, onGuardado }) {
  const esEdicion = Boolean(producto);
  const { values, errors, touched, handleChange, handleBlur, validateAll } = useForm(
    producto
      ? {
          titulo: producto.titulo,
          descripcion: producto.descripcion,
          imagen: producto.imagen,
          orden: String(producto.orden ?? ""),
          precio: String(producto.precio ?? ""),
          stock: String(producto.stock ?? ""),
          sku: producto.sku ?? "",
          familia: producto.familia ?? "",
          pesoG: String(producto.pesoG ?? ""),
          activo: producto.activo === undefined ? true : Boolean(producto.activo),
          proveedorId: producto.proveedorId ? String(producto.proveedorId) : "",
        }
      : valoresIniciales,
    validadores
  );
  const [enviando, setEnviando] = useState(false);
  const [errorServidor, setErrorServidor] = useState("");
  const [subiendoImagen, setSubiendoImagen] = useState(false);
  const [errorImagen, setErrorImagen] = useState("");

  // Proveedores ACTIVOS únicamente: asignar un producto a un proveedor
  // suspendido no tendría sentido comercial (ver el módulo de
  // proveedores, GestionProveedores.jsx). Se traen los primeros 50 —
  // más que suficiente para el selector de un formulario; si el
  // catálogo de proveedores creciera más, este selector necesitaría
  // búsqueda en vivo en vez de una lista completa.
  const [proveedores, setProveedores] = useState([]);
  const [cargandoProveedores, setCargandoProveedores] = useState(true);

  useEffect(() => {
    listarProveedores({ limite: 50, estado: "activo" })
      .then((respuesta) => setProveedores(respuesta.datos))
      .catch(() => setProveedores([])) // el selector queda vacío; el campo sigue siendo opcional
      .finally(() => setCargandoProveedores(false));
  }, []);

  const opcionesProveedor = proveedores.map((p) => ({
    value: String(p.id),
    label: `${p.razonSocial} · ${p.ciudad}`,
  }));

  /**
   * Sube el archivo elegido en cuanto el usuario lo selecciona (no
   * espera al submit del formulario): así se ve la vista previa real
   * de inmediato y, si algo falla (formato no soportado, archivo
   * demasiado pesado), se avisa ahí mismo en vez de hasta el final.
   * El valor que termina en `values.imagen` es la ruta que devuelve
   * el backend (`/uploads/productos/...`), no el nombre del archivo
   * local — por eso se empuja con `handleChange` como si fuera un
   * campo de texto más.
   */
  const handleSeleccionarImagen = async (evento) => {
    const archivo = evento.target.files[0];
    if (!archivo) return;

    setErrorImagen("");
    setSubiendoImagen(true);
    try {
      const datos = await subirImagenProducto(archivo);
      handleChange({ target: { name: "imagen", value: datos.rutaImagen, type: "text" } });
    } catch (err) {
      setErrorImagen(err.message);
    } finally {
      setSubiendoImagen(false);
      // Limpia el <input type="file"> para que, si el usuario elige de
      // nuevo el mismo archivo (ej. tras corregir algo y reintentar),
      // el evento onChange se dispare igual.
      evento.target.value = "";
    }
  };

  const handleSubmit = async (evento) => {
    evento.preventDefault();
    setErrorServidor("");
    if (!validateAll()) return;

    const payload = {
      titulo: values.titulo.trim(),
      descripcion: values.descripcion.trim(),
      imagen: values.imagen.trim(),
      orden: values.orden ? Number(values.orden) : 0,
      precio: Number(values.precio),
      stock: values.stock ? Number(values.stock) : 0,
      sku: values.sku.trim() || undefined,
      familia: values.familia,
      pesoG: values.pesoG ? Number(values.pesoG) : undefined,
      activo: Boolean(values.activo),
      proveedorId: values.proveedorId ? Number(values.proveedorId) : null,
    };

    setEnviando(true);
    try {
      if (esEdicion) {
        await actualizarProducto(producto.id, payload);
      } else {
        await crearProducto(payload);
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
        label="Título"
        name="titulo"
        required
        maxLength={80}
        value={values.titulo}
        onChange={handleChange}
        onBlur={handleBlur}
        error={errors.titulo}
        touched={touched.titulo}
        placeholder="Torta de Chocolate Intenso"
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
        placeholder="Bizcocho húmedo de cacao con ganache de chocolate semiamargo."
      />
      <div className="flex flex-col gap-2">
        <label htmlFor="imagenArchivo" className="text-sm font-medium text-primary/80">
          Imagen del producto <span className="text-primary">*</span>
        </label>

        {values.imagen && (
          <img
            src={resolverUrlImagen(values.imagen)}
            alt="Vista previa del producto"
            className="h-24 w-24 rounded-lg border border-beige object-cover"
          />
        )}

        <input
          id="imagenArchivo"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          disabled={subiendoImagen}
          onChange={handleSeleccionarImagen}
          className="text-sm text-primary/80 file:mr-3 file:rounded-lg file:border-0 file:bg-primary file:px-3 file:py-2 file:text-sm file:font-medium file:text-cream file:cursor-pointer hover:file:opacity-90 disabled:opacity-60"
        />

        {subiendoImagen && <p className="text-xs text-primary/70">Subiendo imagen...</p>}
        {errorImagen && (
          <p className="text-xs text-peligro-fuerte">{errorImagen}</p>
        )}
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
          placeholder="85000"
        />
        <Input
          label="Stock"
          name="stock"
          type="number"
          value={values.stock}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.stock}
          touched={touched.stock}
          placeholder="25"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Categoría"
          name="familia"
          required
          value={values.familia}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.familia}
          touched={touched.familia}
          options={FAMILIAS_PRODUCTO}
        />
        <Input
          label="Peso (g, opcional)"
          name="pesoG"
          type="number"
          value={values.pesoG}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.pesoG}
          touched={touched.pesoG}
          placeholder="1200"
        />
      </div>
      <Input
        label="SKU (opcional)"
        name="sku"
        maxLength={30}
        value={values.sku}
        onChange={handleChange}
        onBlur={handleBlur}
        error={errors.sku}
        touched={touched.sku}
        placeholder="TOR-001"
      />
      <Select
        label={cargandoProveedores ? "Proveedor (cargando...)" : "Proveedor (opcional)"}
        name="proveedorId"
        value={values.proveedorId}
        onChange={handleChange}
        onBlur={handleBlur}
        options={opcionesProveedor}
        placeholder={
          !cargandoProveedores && opcionesProveedor.length === 0
            ? "No hay proveedores activos registrados"
            : "Sin asignar"
        }
      />
      <label className="flex items-center gap-2 text-sm text-primary/80">
        <input
          type="checkbox"
          name="activo"
          checked={values.activo}
          onChange={handleChange}
          className="h-4 w-4 rounded border-beige text-accent focus:ring-primary/20"
        />
        Producto activo (visible en la tienda)
      </label>

      <Button type="submit" fullWidth disabled={enviando || subiendoImagen}>
        {enviando ? "Guardando..." : esEdicion ? "Guardar cambios" : "Crear producto"}
      </Button>

      {errorServidor && (
        <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorServidor}</p>
      )}
    </form>
  );
}

export default GestionProductos;
