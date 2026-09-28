import { useEffect, useState } from "react";
import useForm from "../../hooks/useForm";
import Input from "../../components/ui/Input";
import Select from "../../components/ui/Select";
import Button from "../../components/ui/Button";
import Modal from "../../components/ui/Modal";
import ConfirmModal from "../../components/ui/ConfirmModal";
import Paginacion from "../../components/ui/Paginacion";
import {
  validarCodigoCupon,
  validarTipoCupon,
  validarValorCupon,
  validarMontoMinimoCupon,
  validarUsosMaximosCupon,
  validarValidoDesde,
  validarValidoHasta,
} from "../../utils/validators";
import { formatearPrecio, formatearFecha } from "../../utils/formato";
import { listarCupones, crearCupon, actualizarCupon, eliminarCupon } from "../../utils/api";

const OPCIONES_TIPO = [
  { value: "porcentaje", label: "Porcentaje" },
  { value: "monto_fijo", label: "Monto fijo" },
];

const valoresIniciales = {
  codigo: "",
  tipo: "",
  valor: "",
  montoMinimo: "",
  usosMaximos: "",
  validoDesde: "",
  validoHasta: "",
  activo: true,
};
const validadores = {
  codigo: validarCodigoCupon,
  tipo: validarTipoCupon,
  valor: validarValorCupon,
  montoMinimo: validarMontoMinimoCupon,
  usosMaximos: validarUsosMaximosCupon,
  validoDesde: validarValidoDesde,
  validoHasta: validarValidoHasta,
};
const CUPONES_POR_PAGINA = 10;

/**
 * cupones.valido_desde/valido_hasta llegan del backend como
 * "YYYY-MM-DD HH:mm:ss" (dateStrings: true en config/db.js), pero el
 * input <input type="datetime-local"> necesita "YYYY-MM-DDTHH:mm".
 * Al enviar, el backend acepta cualquier formato que `new Date()`
 * entienda (ver validarValidoDesde/validarValidoHasta del backend), así
 * que el valor del input ya sirve tal cual, sin reconvertir.
 */
function aFormatoDatetimeLocal(valorMysql) {
  if (!valorMysql) return "";
  return valorMysql.replace(" ", "T").slice(0, 16);
}

/**
 * "YYYY-MM-DDTHH:mm" del momento actual, en hora local del navegador
 * (igual formato que necesita <input type="datetime-local">). Se usa
 * como `min` para que el calendario no deje elegir una fecha/hora ya
 * pasada al crear un cupón nuevo.
 */
function ahoraFormatoDatetimeLocal() {
  const ahora = new Date();
  ahora.setSeconds(0, 0);
  ahora.setMinutes(ahora.getMinutes() - ahora.getTimezoneOffset());
  return ahora.toISOString().slice(0, 16);
}

function describirVigencia(cupon) {
  const ahora = new Date();
  const desde = new Date(cupon.validoDesde);
  const hasta = new Date(cupon.validoHasta);
  if (ahora < desde) return { texto: "Aún no inicia", clase: "bg-beige/60 text-primary/70" };
  if (ahora > hasta) return { texto: "Vencido", clase: "bg-beige/60 text-primary/70" };
  if (cupon.usosMaximos !== null && cupon.usosActuales >= cupon.usosMaximos) {
    return { texto: "Agotado", clase: "bg-beige/60 text-primary/70" };
  }
  return { texto: "Vigente", clase: "bg-exito text-exito-fuerte" };
}

function GestionCupones() {
  const [cupones, setCupones] = useState([]);
  const [paginacion, setPaginacion] = useState({ pagina: 1, limite: CUPONES_POR_PAGINA, total: 0, totalPaginas: 0 });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [modalAbierto, setModalAbierto] = useState(false);
  const [cuponEditando, setCuponEditando] = useState(null); // null = crear
  const [cuponAEliminar, setCuponAEliminar] = useState(null); // null = modal cerrado

  // Misma convención que GestionProductos.jsx: la carga inicial ya
  // arranca en `cargando = true` (useState(true) arriba), así que este
  // helper no lo vuelve a poner en true por sí mismo — eso lo hacen
  // los wrappers de abajo cuando de verdad hace falta mostrar el
  // spinner de nuevo (recargar tras guardar, o cambiar de página).
  const obtenerCupones = (pagina = paginacion.pagina) => {
    listarCupones({ pagina, limite: CUPONES_POR_PAGINA })
      .then((respuesta) => {
        setCupones(respuesta.datos);
        setPaginacion(respuesta.paginacion);
      })
      .catch((err) => setError(err.message))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    obtenerCupones(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const recargarCupones = () => {
    setCargando(true);
    // Igual que en GestionProductos.jsx: se vuelve a pedir la página
    // ACTUAL (no siempre la 1), para que un cupón editado en la
    // página 2 se siga viendo en la página 2 después de guardar.
    obtenerCupones(paginacion.pagina);
  };

  const handleCambiarPagina = (paginaNueva) => {
    setCargando(true);
    obtenerCupones(paginaNueva);
  };

  const abrirCrear = () => {
    setCuponEditando(null);
    setModalAbierto(true);
  };

  const abrirEditar = (cupon) => {
    setCuponEditando(cupon);
    setModalAbierto(true);
  };

  const handleEliminar = async () => {
    await eliminarCupon(cuponAEliminar.id);
    // Se recarga desde el servidor (no se filtra en memoria) para que
    // "total"/"totalPaginas" queden correctos, igual que en
    // GestionProductos.jsx.
    recargarCupones();
  };

  return (
    <section className="rounded-2xl border border-beige/60 bg-cream p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-primary">Cupones de descuento</h2>
          <p className="text-sm text-primary/70">Crear, editar y eliminar cupones: solo admin.</p>
        </div>
        <Button onClick={abrirCrear}>+ Nuevo cupón</Button>
      </div>

      {cargando && <p className="text-sm text-primary/70">Cargando cupones...</p>}
      {error && <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{error}</p>}

      {!cargando && !error && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-beige/60 text-primary/70">
                <th className="py-2 pr-3">Código</th>
                <th className="py-2 pr-3">Valor</th>
                <th className="py-2 pr-3">Usos</th>
                <th className="py-2 pr-3">Vigencia</th>
                <th className="py-2 pr-3">Estado</th>
                <th className="py-2 pr-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {cupones.map((cupon) => {
                const vigencia = describirVigencia(cupon);
                return (
                  <tr key={cupon.id} className="border-b border-beige/30">
                    <td className="py-2 pr-3 font-medium text-primary">{cupon.codigo}</td>
                    <td className="py-2 pr-3 text-primary/70">
                      {cupon.tipo === "porcentaje" ? `${Number(cupon.valor)}%` : formatearPrecio(cupon.valor)}
                      {Number(cupon.montoMinimo) > 0 && (
                        <span className="block text-xs text-primary/70">
                          Mín. {formatearPrecio(cupon.montoMinimo)}
                        </span>
                      )}
                    </td>
                    <td className="py-2 pr-3 text-primary/70">
                      {cupon.usosActuales} / {cupon.usosMaximos ?? "∞"}
                    </td>
                    <td className="py-2 pr-3 text-primary/70">
                      {formatearFecha(cupon.validoDesde)} — {formatearFecha(cupon.validoHasta)}
                    </td>
                    <td className="py-2 pr-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${vigencia.clase}`}>
                        {cupon.activo ? vigencia.texto : "Inactivo"}
                      </span>
                    </td>
                    <td className="py-2 pr-3">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => abrirEditar(cupon)}
                          aria-label={`Editar cupón ${cupon.codigo}`}
                          className="rounded-md px-2 py-1 text-primary hover:bg-section"
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={() => setCuponAEliminar(cupon)}
                          aria-label={`Eliminar cupón ${cupon.codigo}`}
                          className="rounded-md px-2 py-1 text-peligro-fuerte hover:bg-peligro"
                        >
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {cupones.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-primary/70">
                    Todavía no hay cupones.
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
        title={cuponEditando ? "Editar cupón" : "Nuevo cupón"}
      >
        <FormularioCupon
          cupon={cuponEditando}
          onGuardado={() => {
            setModalAbierto(false);
            recargarCupones();
          }}
        />
      </Modal>

      <ConfirmModal
        isOpen={Boolean(cuponAEliminar)}
        onClose={() => setCuponAEliminar(null)}
        title="Eliminar cupón"
        message={
          cuponAEliminar &&
          `¿Eliminar el cupón "${cuponAEliminar.codigo}"? Esta acción no se puede deshacer. Los pedidos que ya lo usaron conservan su descuento tal cual quedó aplicado.`
        }
        onConfirm={handleEliminar}
      />
    </section>
  );
}

function FormularioCupon({ cupon, onGuardado }) {
  const esEdicion = Boolean(cupon);
  const { values, errors, touched, handleChange, handleBlur, validateAll } = useForm(
    cupon
      ? {
          codigo: cupon.codigo,
          tipo: cupon.tipo,
          valor: String(cupon.valor ?? ""),
          montoMinimo: String(cupon.montoMinimo ?? ""),
          usosMaximos: cupon.usosMaximos === null ? "" : String(cupon.usosMaximos),
          validoDesde: aFormatoDatetimeLocal(cupon.validoDesde),
          validoHasta: aFormatoDatetimeLocal(cupon.validoHasta),
          activo: cupon.activo === undefined ? true : Boolean(cupon.activo),
        }
      : valoresIniciales,
    validadores
  );
  const [enviando, setEnviando] = useState(false);
  const [errorServidor, setErrorServidor] = useState("");

  const handleSubmit = async (evento) => {
    evento.preventDefault();
    setErrorServidor("");
    if (!validateAll()) return;

    const payload = {
      codigo: values.codigo.trim(),
      tipo: values.tipo,
      valor: Number(values.valor),
      montoMinimo: values.montoMinimo ? Number(values.montoMinimo) : 0,
      usosMaximos: values.usosMaximos ? Number(values.usosMaximos) : null,
      validoDesde: values.validoDesde,
      validoHasta: values.validoHasta,
      activo: Boolean(values.activo),
    };

    setEnviando(true);
    try {
      if (esEdicion) {
        await actualizarCupon(cupon.id, payload);
      } else {
        await crearCupon(payload);
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
        label="Código"
        name="codigo"
        required
        maxLength={30}
        value={values.codigo}
        onChange={handleChange}
        onBlur={handleBlur}
        error={errors.codigo}
        touched={touched.codigo}
        placeholder="VERANO20"
      />
      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Tipo"
          name="tipo"
          required
          value={values.tipo}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.tipo}
          touched={touched.tipo}
          options={OPCIONES_TIPO}
        />
        <Input
          label={values.tipo === "monto_fijo" ? "Valor (COP)" : "Valor (%)"}
          name="valor"
          type="number"
          required
          value={values.valor}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.valor}
          touched={touched.valor}
          placeholder={values.tipo === "monto_fijo" ? "20000" : "20"}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Monto mínimo (opcional)"
          name="montoMinimo"
          type="number"
          value={values.montoMinimo}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.montoMinimo}
          touched={touched.montoMinimo}
          placeholder="0"
        />
        <Input
          label="Usos máximos (opcional)"
          name="usosMaximos"
          type="number"
          value={values.usosMaximos}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.usosMaximos}
          touched={touched.usosMaximos}
          placeholder="Ilimitado"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Válido desde"
          name="validoDesde"
          type="datetime-local"
          required
          min={ahoraFormatoDatetimeLocal()}
          value={values.validoDesde}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.validoDesde}
          touched={touched.validoDesde}
        />
        <Input
          label="Válido hasta"
          name="validoHasta"
          type="datetime-local"
          required
          min={values.validoDesde || ahoraFormatoDatetimeLocal()}
          value={values.validoHasta}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.validoHasta}
          touched={touched.validoHasta}
        />
      </div>
      <label className="flex items-center gap-2 text-sm text-primary/80">
        <input
          type="checkbox"
          name="activo"
          checked={values.activo}
          onChange={handleChange}
          className="h-4 w-4 rounded border-beige text-accent focus:ring-primary/20"
        />
        Cupón activo
      </label>

      <Button type="submit" fullWidth disabled={enviando}>
        {enviando ? "Guardando..." : esEdicion ? "Guardar cambios" : "Crear cupón"}
      </Button>

      {errorServidor && (
        <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorServidor}</p>
      )}
    </form>
  );
}

export default GestionCupones;
