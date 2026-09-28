import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import useForm from "../hooks/useForm";
import Input from "../components/ui/Input";
import Button from "../components/ui/Button";
import Modal from "../components/ui/Modal";
import RecoverPassword from "../components/RecoverPassword";
import RegisterModal from "../components/RegisterModal";
import { validarCorreo, validarPasswordLogin } from "../utils/validators";
import { iniciarSesion, reenviarVerificacion } from "../utils/api";
import { useAuth } from "../hooks/useAuth";
import useDocumentTitle from "../hooks/useDocumentTitle";

const valoresIniciales = { correo: "", password: "", recordarme: false };
const validadores = { correo: validarCorreo, password: validarPasswordLogin };

function Login() {
  const { values, errors, touched, handleChange, handleBlur, validateAll } =
    useForm(valoresIniciales, validadores);

  const [vista, setVista] = useState("login"); // "login" | "recuperar"
  const [paso, setPaso] = useState(1); // 1 = correo, 2 = contraseña
  const [errorPaso1, setErrorPaso1] = useState("");

  useDocumentTitle(
    vista === "login" ? "Iniciar sesión" : "Recuperar contraseña",
    "Accede a tu cuenta de Dulce Esencia Pastelería para gestionar tus pedidos y preferencias.",
    "/login"
  );
  const [modalRegistroAbierto, setModalRegistroAbierto] = useState(false);
  const [mensaje, setMensaje] = useState("");
  const [errorServidor, setErrorServidor] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [correoSinVerificar, setCorreoSinVerificar] = useState(false);
  const [reenviando, setReenviando] = useState(false);
  const [reenviado, setReenviado] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const ubicacion = useLocation();

  const handleContinuar = (evento) => {
    evento.preventDefault();
    setErrorServidor("");
    const error = validarCorreo(values.correo);
    setErrorPaso1(error);
    if (!error) setPaso(2);
  };

  const handleCambiarCorreo = () => {
    setPaso(1);
    setErrorServidor("");
    setCorreoSinVerificar(false);
    setReenviado(false);
  };

  const handleSubmit = async (evento) => {
    evento.preventDefault();
    setErrorServidor("");
    setCorreoSinVerificar(false);
    setReenviado(false);
    const esValido = validateAll();
    if (!esValido) return;

    setEnviando(true);
    try {
      const respuesta = await iniciarSesion({
        correo: values.correo,
        password: values.password,
        recordarme: values.recordarme,
      });

      login(respuesta.usuario);
      setMensaje(`Bienvenido/a, ${respuesta.usuario.nombre}. Sesión iniciada correctamente.`);
      const destino = ubicacion.state?.desde || "/panel";
      setTimeout(() => navigate(destino, { replace: true }), 600);
    } catch (error) {
      setErrorServidor(error.message);
      if (error.status === 403) setCorreoSinVerificar(true);
    } finally {
      setEnviando(false);
    }
  };

  const handleReenviarVerificacion = async () => {
    setReenviando(true);
    try {
      await reenviarVerificacion({ correo: values.correo });
      setReenviado(true);
    } catch {
      // Ignore
    } finally {
      setReenviando(false);
    }
  };

  return (
    <main className="flex flex-1 items-center justify-center bg-section px-4 py-12">
      <motion.div 
        className="w-full max-w-md rounded-2xl bg-cream p-8 shadow-lg shadow-primary/10 overflow-hidden"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <AnimatePresence mode="wait">
          {vista === "login" ? (
            <motion.div
              key="login-view"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
            >
              <h1 className="mb-1 text-2xl font-bold">Inicia sesión</h1>
              <p className="mb-6 text-sm text-primary/70">
                Accede a tu cuenta para gestionar tus pedidos y tus preferencias.
              </p>

              <form
                onSubmit={paso === 1 ? handleContinuar : handleSubmit}
                noValidate
                className="flex flex-col gap-4"
              >
                <AnimatePresence mode="wait">
                  {paso === 1 ? (
                    <motion.div
                      key="paso-1"
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      transition={{ duration: 0.3 }}
                      className="flex flex-col gap-4"
                    >
                      <Input
                        label="Correo electrónico"
                        name="correo"
                        type="email"
                        required
                        value={values.correo}
                        onChange={(e) => {
                          setErrorPaso1("");
                          handleChange(e);
                        }}
                        error={errorPaso1}
                        touched={Boolean(errorPaso1)}
                        placeholder="tucorreo@ejemplo.com"
                        autoComplete="email"
                      />
                      <Button type="submit" fullWidth>
                        Continuar
                      </Button>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="paso-2"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ duration: 0.3 }}
                      className="flex flex-col gap-4"
                    >
                      <div className="flex items-center justify-between gap-3 rounded-lg border border-beige/60 px-3 py-2 text-sm">
                        <span className="truncate text-primary/80" title={values.correo}>
                          {values.correo}
                        </span>
                        <button
                          type="button"
                          onClick={handleCambiarCorreo}
                          className="whitespace-nowrap font-medium text-primary hover:underline"
                        >
                          Cambiar
                        </button>
                      </div>

                      <Input
                        label="Contraseña"
                        name="password"
                        type="password"
                        required
                        maxLength={32}
                        value={values.password}
                        onChange={handleChange}
                        onBlur={handleBlur}
                        error={errors.password}
                        touched={touched.password}
                        placeholder="Tu contraseña"
                        autoComplete="current-password"
                      />

                      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                        <label className="flex items-center gap-2 text-primary/70">
                          <input
                            type="checkbox"
                            name="recordarme"
                            checked={values.recordarme}
                            onChange={handleChange}
                            className="h-4 w-4 rounded border-beige text-primary focus:ring-primary"
                          />
                          Recordarme
                        </label>
                        <button
                          type="button"
                          onClick={() => setVista("recuperar")}
                          className="font-medium text-primary hover:underline"
                        >
                          ¿Olvidaste tu contraseña?
                        </button>
                      </div>

                      <Button type="submit" fullWidth disabled={enviando}>
                        {enviando ? "Iniciando sesión..." : "Iniciar sesión"}
                      </Button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </form>

              {errorServidor && (
                <motion.p 
                  initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                  className="mt-4 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte"
                >
                  {errorServidor}
                </motion.p>
              )}

              {correoSinVerificar && !reenviado && (
                <Button
                  variant="ghost"
                  className="mt-2"
                  onClick={handleReenviarVerificacion}
                  disabled={reenviando}
                >
                  {reenviando ? "Enviando..." : "Reenviar código de verificación"}
                </Button>
              )}

              {reenviado && (
                <p className="mt-2 text-sm text-primary/70">
                  Si tu cuenta sigue pendiente de verificar, te enviamos un nuevo código.{" "}
                  <Link
                    to={`/verificar-correo?correo=${encodeURIComponent(values.correo)}`}
                    className="font-medium text-primary hover:underline"
                  >
                    Escribir el código
                  </Link>
                </p>
              )}

              {mensaje && (
                <motion.p 
                  initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                  className="mt-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300"
                >
                  {mensaje}
                </motion.p>
              )}

              <p className="mt-6 text-center text-sm text-primary/70">
                ¿No tienes cuenta?{" "}
                <button
                  type="button"
                  onClick={() => setModalRegistroAbierto(true)}
                  className="font-semibold text-primary hover:underline"
                >
                  Crear una cuenta
                </button>
              </p>
            </motion.div>
          ) : (
            <motion.div
              key="recuperar-view"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <h1 className="mb-1 text-2xl font-bold">Recuperar contraseña</h1>
              <div className="mt-4">
                <RecoverPassword onVolver={() => setVista("login")} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      <Modal
        isOpen={modalRegistroAbierto}
        onClose={() => setModalRegistroAbierto(false)}
        title="Crear una cuenta"
      >
        <RegisterModal onRegistroExitoso={() => setModalRegistroAbierto(false)} />
      </Modal>
    </main>
  );
}

export default Login;
