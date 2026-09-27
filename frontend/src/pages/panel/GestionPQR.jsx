import { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import Paginacion from "../../components/ui/Paginacion";
import Button from "../../components/ui/Button";
import { listarPQR, crearPQR, gestionarPQR } from "../../utils/api";
import { formatearFecha, obtenerEstadoPQR, obtenerTipoPQR } from "../../utils/formato";

const PQR_POR_PAGINA = 10;
const TIPOS = ["peticion", "queja", "reclamo", "sugerencia"];
const ESTADOS = ["pendiente", "en_proceso", "respondida", "cerrada"];

/**
 * GestionPQR — requerimiento 16 del quinto avance.
 * Cualquier usuario puede registrar y ver sus propias PQR; admin y
 * empleado además ven TODAS y pueden responder/cambiar el estado
 * (el backend ya resuelve el alcance, ver GET/PATCH /api/pqr).
 */
function GestionPQR() {
  const { usuario } = useAuth();
  const esGestion = usuario?.rol === "admin" || usuario?.rol === "empleado";

  const [lista, setLista] = useState([]);
  const [paginacion, setPaginacion] = useState({ pagina: 1, limite: PQR_POR_PAGINA, total: 0, totalPaginas: 0 });
  const [filtroEstado, setFiltroEstado] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [tipo, setTipo] = useState("peticion");
  const [asunto, setAsunto] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [errorFormulario, setErrorFormulario] = useState("");

  const [respuestas, setRespuestas] = useState({});
  const [gestionandoId, setGestionandoId] = useState(null);

  const cargar = (pagina = 1, estado = filtroEstado) => {
    setCargando(true);
    listarPQR({ pagina, limite: PQR_POR_PAGINA, estado })
      .then((respuesta) => {
        setLista(respuesta.datos);
        setPaginacion(respuesta.paginacion);
      })
      .catch((err) => setError(err.message))
      .finally(() => setCargando(false));
  };

  useEffect(() => {
    cargar(1, "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCambiarFiltro = (estado) => {
    setFiltroEstado(estado);
    cargar(1, estado);
  };

  const enviarPQR = async (evento) => {
    evento.preventDefault();
    setErrorFormulario("");
    if (!asunto.trim() || descripcion.trim().length < 10) {
      setErrorFormulario("Escribe un asunto y una descripción de al menos 10 caracteres.");
      return;
    }
    setGuardando(true);
    try {
      await crearPQR({ tipo, asunto: asunto.trim(), descripcion: descripcion.trim() });
      setAsunto("");
      setDescripcion("");
      setTipo("peticion");
      setMostrarFormulario(false);
      cargar(1, filtroEstado);
    } catch (err) {
      setErrorFormulario(err.message);
    } finally {
      setGuardando(false);
    }
  };

  const responder = async (item) => {
    const respuesta = (respuestas[item.id] || "").trim();
    setGestionandoId(item.id);
    try {
      await gestionarPQR(item.id, { respuesta: respuesta || undefined, estado: "respondida" });
      cargar(paginacion.pagina, filtroEstado);
    } catch (err) {
      setError(err.message);
    } finally {
      setGestionandoId(null);
    }
  };

  const cambiarEstado = async (item, estadoNuevo) => {
    setGestionandoId(item.id);
    try {
      await gestionarPQR(item.id, { estado: estadoNuevo });
      setLista((prev) => prev.map((p) => (p.id === item.id ? { ...p, estado: estadoNuevo } : p)));
    } catch (err) {
      setError(err.message);
    } finally {
      setGestionandoId(null);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-2xl border border-beige/60 bg-cream p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-primary">Peticiones, quejas y reclamos</h2>
            <p className="text-sm text-primary/70">
              {esGestion ? "Gestiona las solicitudes de los clientes." : "Registra tu solicitud y consulta su estado."}
            </p>
          </div>
          <Button variant="secondary" onClick={() => setMostrarFormulario((v) => !v)}>
            {mostrarFormulario ? "Cancelar" : "Nueva solicitud"}
          </Button>
        </div>

        {mostrarFormulario && (
          <form onSubmit={enviarPQR} className="mb-2 flex flex-col gap-3 border-b border-beige/60 pb-5">
            {errorFormulario && (
              <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte dark:bg-peligro dark:text-peligro-fuerte">
                {errorFormulario}
              </p>
            )}
            <div className="flex flex-col gap-1">
              <label htmlFor="tipo" className="text-sm font-medium text-primary/80">Tipo</label>
              <select
                id="tipo"
                value={tipo}
                onChange={(e) => setTipo(e.target.value)}
                className="w-48 rounded-lg border border-beige bg-cream px-3 py-2 text-sm text-primary outline-none focus:border-primary"
              >
                {TIPOS.map((t) => (
                  <option key={t} value={t}>{obtenerTipoPQR(t)}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="asunto" className="text-sm font-medium text-primary/80">Asunto *</label>
              <input
                id="asunto"
                type="text"
                maxLength={120}
                value={asunto}
                onChange={(e) => setAsunto(e.target.value)}
                className="rounded-lg border border-beige bg-cream px-3 py-2 text-sm text-primary outline-none focus:border-primary"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="descripcion" className="text-sm font-medium text-primary/80">Descripción *</label>
              <textarea
                id="descripcion"
                rows={4}
                maxLength={2000}
                value={descripcion}
                onChange={(e) => setDescripcion(e.target.value)}
                className="rounded-lg border border-beige bg-cream px-3 py-2 text-sm text-primary outline-none focus:border-primary"
              />
            </div>
            <Button type="submit" disabled={guardando} className="self-start">
              {guardando ? "Enviando..." : "Enviar solicitud"}
            </Button>
          </form>
        )}

        {esGestion && (
          <div className="mt-4 flex flex-wrap gap-2">
            {["", ...ESTADOS].map((estado) => (
              <button
                key={estado || "todos"}
                type="button"
                onClick={() => handleCambiarFiltro(estado)}
                className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                  filtroEstado === estado ? "bg-primary text-cream" : "bg-section text-primary/70 hover:text-primary"
                }`}
              >
                {estado ? obtenerEstadoPQR(estado).texto : "Todos"}
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-beige/60 bg-cream p-6">
        {cargando && <p className="text-sm text-primary/70">Cargando...</p>}
        {error && <p className="mb-3 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte dark:bg-peligro dark:text-peligro-fuerte">{error}</p>}

        {!cargando && (
          <ul className="flex flex-col gap-4">
            {lista.map((item) => (
              <li key={item.id} className="rounded-xl border border-beige/50 p-4">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-primary">
                      #{item.id} · {obtenerTipoPQR(item.tipo)} · {item.asunto}
                    </p>
                    <p className="text-xs text-primary/70">{formatearFecha(item.creadoEn)}</p>
                  </div>
                  <span
                    className="rounded-full px-2.5 py-1 text-xs font-semibold"
                    style={{
                      color: obtenerEstadoPQR(item.estado).color,
                      backgroundColor: obtenerEstadoPQR(item.estado).fondo,
                    }}
                  >
                    {obtenerEstadoPQR(item.estado).texto}
                  </span>
                </div>
                <p className="text-sm text-primary/80">{item.descripcion}</p>

                {item.respuesta && (
                  <div className="mt-3 rounded-lg bg-section p-3 text-sm text-primary/80">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-primary/70">Respuesta</p>
                    {item.respuesta}
                  </div>
                )}

                {esGestion && item.estado !== "cerrada" && (
                  <div className="mt-3 flex flex-col gap-2 border-t border-beige/50 pt-3">
                    <textarea
                      rows={2}
                      placeholder="Escribe una respuesta..."
                      value={respuestas[item.id] || ""}
                      onChange={(e) => setRespuestas((prev) => ({ ...prev, [item.id]: e.target.value }))}
                      className="rounded-lg border border-beige bg-cream px-3 py-2 text-sm text-primary outline-none focus:border-primary"
                    />
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="secondary"
                        disabled={gestionandoId === item.id}
                        onClick={() => responder(item)}
                      >
                        Responder
                      </Button>
                      {item.estado === "pendiente" && (
                        <Button
                          variant="ghost"
                          disabled={gestionandoId === item.id}
                          onClick={() => cambiarEstado(item, "en_proceso")}
                        >
                          Marcar en proceso
                        </Button>
                      )}
                      {item.estado !== "cerrada" && (
                        <Button
                          variant="ghost"
                          disabled={gestionandoId === item.id}
                          onClick={() => cambiarEstado(item, "cerrada")}
                        >
                          Cerrar
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </li>
            ))}
            {lista.length === 0 && (
              <p className="py-6 text-center text-sm text-primary/70">No hay solicitudes registradas todavía.</p>
            )}
          </ul>
        )}

        <Paginacion
          pagina={paginacion.pagina}
          totalPaginas={paginacion.totalPaginas}
          total={paginacion.total}
          onCambiarPagina={(pagina) => cargar(pagina, filtroEstado)}
          deshabilitado={cargando}
        />
      </section>
    </div>
  );
}

export default GestionPQR;
