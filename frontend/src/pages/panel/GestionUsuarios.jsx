import { useEffect, useState } from "react";
import { listarUsuarios, cambiarRolUsuario, cambiarEstadoUsuario, eliminarUsuario } from "../../utils/api";
import { useAuth } from "../../hooks/useAuth";
import ConfirmModal from "../../components/ui/ConfirmModal";
import Modal from "../../components/ui/Modal";
import CrearUsuarioModal from "../../components/ui/CrearUsuarioModal";
import Button from "../../components/ui/Button";
import Paginacion from "../../components/ui/Paginacion";

const ROLES = ["cliente", "empleado", "admin"];
const USUARIOS_POR_PAGINA = 10;

function GestionUsuarios() {
  const { usuario: usuarioActual } = useAuth();
  const esAdmin = usuarioActual?.rol === "admin";

  const [usuarios, setUsuarios] = useState([]);
  const [paginacion, setPaginacion] = useState({ pagina: 1, limite: USUARIOS_POR_PAGINA, total: 0, totalPaginas: 0 });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [guardandoId, setGuardandoId] = useState(null);
  const [errorRol, setErrorRol] = useState("");
  const [cambiandoEstadoId, setCambiandoEstadoId] = useState(null);
  const [errorEstado, setErrorEstado] = useState("");
  const [usuarioAEliminar, setUsuarioAEliminar] = useState(null); // null = modal cerrado
  const [modalCrearAbierto, setModalCrearAbierto] = useState(false);

  // No hace falta setCargando(true) aquí en el efecto de montaje: el
  // estado ya arranca en true (useState(true) de arriba). Al cambiar
  // de página sí queremos mostrar el spinner de nuevo (ver handleCambiarPagina).
  const cargar = (pagina = paginacion.pagina) => {
    listarUsuarios({ pagina, limite: USUARIOS_POR_PAGINA })
      .then((respuesta) => {
        setUsuarios(respuesta.datos);
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

  const handleCambiarRol = async (id, rolNuevo) => {
    setGuardandoId(id);
    setErrorRol("");
    try {
      await cambiarRolUsuario(id, rolNuevo);
      setUsuarios((prev) => prev.map((u) => (u.id === id ? { ...u, rol: rolNuevo } : u)));
    } catch (err) {
      setErrorRol(err.message);
    } finally {
      setGuardandoId(null);
    }
  };

  const handleCambiarEstado = async (usuario) => {
    const activoNuevo = !usuario.activo;
    setCambiandoEstadoId(usuario.id);
    setErrorEstado("");
    try {
      await cambiarEstadoUsuario(usuario.id, activoNuevo);
      setUsuarios((prev) => prev.map((u) => (u.id === usuario.id ? { ...u, activo: activoNuevo } : u)));
    } catch (err) {
      setErrorEstado(err.message);
    } finally {
      setCambiandoEstadoId(null);
    }
  };

  const handleEliminar = async () => {
    await eliminarUsuario(usuarioAEliminar.id);
    // Tras eliminar, se recarga la página actual desde el servidor en
    // vez de solo filtrar en memoria: así "total" y "totalPaginas"
    // quedan correctos y no se muestra una página vacía de más si esta
    // era la última fila de la última página.
    setCargando(true);
    cargar(paginacion.pagina);
  };

  const handleUsuarioCreado = () => {
    setModalCrearAbierto(false);
    // El usuario nuevo queda primero (ORDER BY creado_en DESC), así que
    // se recarga desde la página 1 para que aparezca de inmediato sin
    // que el admin tenga que ir a buscarlo.
    setCargando(true);
    cargar(1);
  };

  return (
    <section className="rounded-2xl border border-beige/60 bg-cream p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-primary">Usuarios registrados</h2>
          <p className="text-sm text-primary/70">
            {esAdmin
              ? "Puedes agregar, cambiar el rol, activar/desactivar o eliminar una cuenta."
              : "Vista de solo lectura: solo un administrador puede agregar, cambiar roles, el estado o eliminar cuentas."}
          </p>
        </div>
        {esAdmin && (
          <Button onClick={() => setModalCrearAbierto(true)}>Agregar usuario</Button>
        )}
      </div>

      {cargando && <p className="text-sm text-primary/70">Cargando usuarios...</p>}
      {error && <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{error}</p>}
      {errorRol && (
        <p className="mb-4 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorRol}</p>
      )}
      {errorEstado && (
        <p className="mb-4 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorEstado}</p>
      )}

      {!cargando && !error && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-beige/60 text-primary/70">
                <th className="py-2 pr-3">Nombre</th>
                <th className="py-2 pr-3">Correo</th>
                <th className="py-2 pr-3">Teléfono</th>
                <th className="py-2 pr-3">Rol</th>
                <th className="py-2 pr-3">Estado</th>
                {esAdmin && <th className="py-2 pr-3 text-right">Acciones</th>}
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => {
                const esUnoMismo = u.id === usuarioActual.id;
                return (
                  <tr key={u.id} className="border-b border-beige/30">
                    <td className="py-2 pr-3 font-medium text-primary">
                      {u.nombre} {u.apellido}
                    </td>
                    <td className="py-2 pr-3 text-primary/70">{u.correo}</td>
                    <td className="py-2 pr-3 text-primary/70">{u.telefono}</td>
                    <td className="py-2 pr-3">
                      {esAdmin && !esUnoMismo ? (
                        <select
                          value={u.rol}
                          disabled={guardandoId === u.id}
                          onChange={(evento) => handleCambiarRol(u.id, evento.target.value)}
                          className="rounded-md border border-beige bg-cream px-2 py-1 text-sm text-primary outline-none focus:border-primary"
                        >
                          {ROLES.map((rol) => (
                            <option key={rol} value={rol}>
                              {rol}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="capitalize text-primary/70">{u.rol}</span>
                      )}
                    </td>
                    <td className="py-2 pr-3">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                          u.activo
                            ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300"
                            : "bg-peligro text-peligro-fuerte"
                        }`}
                      >
                        {u.activo ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    {esAdmin && (
                      <td className="py-2 pr-3 text-right">
                        {!esUnoMismo && (
                          <div className="flex items-center justify-end gap-3">
                            <button
                              type="button"
                              onClick={() => handleCambiarEstado(u)}
                              disabled={cambiandoEstadoId === u.id}
                              className="rounded-md px-2 py-1 text-primary/70 hover:bg-section disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              {u.activo ? "Desactivar" : "Activar"}
                            </button>
                            <button
                              type="button"
                              onClick={() => setUsuarioAEliminar(u)}
                              className="rounded-md px-2 py-1 text-peligro-fuerte hover:bg-peligro"
                            >
                              Eliminar
                            </button>
                          </div>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
              {usuarios.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-primary/70">
                    No hay usuarios registrados.
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

      <ConfirmModal
        isOpen={Boolean(usuarioAEliminar)}
        onClose={() => setUsuarioAEliminar(null)}
        title="Eliminar usuario"
        message={
          usuarioAEliminar &&
          `¿Eliminar la cuenta de ${usuarioAEliminar.nombre} ${usuarioAEliminar.apellido}? Esta acción no se puede deshacer.`
        }
        onConfirm={handleEliminar}
      />

      <Modal
        isOpen={modalCrearAbierto}
        onClose={() => setModalCrearAbierto(false)}
        title="Agregar usuario"
      >
        <CrearUsuarioModal onCreado={handleUsuarioCreado} />
      </Modal>
    </section>
  );
}

export default GestionUsuarios;
