import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import useForm from "../hooks/useForm";
import Input from "../components/ui/Input";
import Button from "../components/ui/Button";
import {
  validarCorreo,
  validarCodigoOtp,
  validarPasswordNueva,
  validarConfirmarPassword,
} from "../utils/validators";
import { restablecerPassword, reenviarCodigoRecuperacion } from "../utils/api";
import useDocumentTitle from "../hooks/useDocumentTitle";

const validadores = {
  correo: validarCorreo,
  codigo: validarCodigoOtp,
  passwordNueva: validarPasswordNueva,
  confirmarPasswordNueva: (valor, valores) =>
    validarConfirmarPassword(valor, { password: valores.passwordNueva }),
};

/**
 * Segundo paso de "olvidé mi contraseña" (ver POST /api/usuarios/recuperar
 * y POST /api/usuarios/restablecer en el backend).
 *
 * A diferencia de la versión anterior (que leía token+correo de la URL
 * de un enlace), ahora el backend envía por correo un CÓDIGO de 6
 * dígitos (OTP) que la persona escribe a mano aquí junto con su
 * contraseña nueva. El correo llega precargado por query param
 * (?correo=...) desde RecoverPassword, pero sigue siendo editable.
 */
function ResetPassword() {
  useDocumentTitle(
    "Restablecer contraseña",
    "Elige una nueva contraseña para tu cuenta de Dulce Esencia Pastelería.",
    "/restablecer-password",
    true
  );

  const [parametros] = useSearchParams();
  const navigate = useNavigate();

  const { values, errors, touched, handleChange, handleBlur, validateAll } = useForm(
    { correo: parametros.get("correo") || "", codigo: "", passwordNueva: "", confirmarPasswordNueva: "" },
    validadores
  );
  const [enviando, setEnviando] = useState(false);
  const [errorServidor, setErrorServidor] = useState("");
  const [listo, setListo] = useState(false);
  const [reenviando, setReenviando] = useState(false);
  const [reenviado, setReenviado] = useState(false);

  const handleSubmit = async (evento) => {
    evento.preventDefault();
    setErrorServidor("");
    if (!validateAll()) return;

    setEnviando(true);
    try {
      await restablecerPassword({
        correo: values.correo,
        codigo: values.codigo,
        passwordNueva: values.passwordNueva,
      });
      setListo(true);
      setTimeout(() => navigate("/login", { replace: true }), 1500);
    } catch (err) {
      setErrorServidor(err.message);
    } finally {
      setEnviando(false);
    }
  };

  const handleReenviar = async () => {
    const errorCorreo = validarCorreo(values.correo);
    if (errorCorreo) {
      setErrorServidor(errorCorreo);
      return;
    }
    setErrorServidor("");
    setReenviando(true);
    try {
      // Mismo mensaje genérico exista o no el correo (ver POST
      // /usuarios/recuperar), así que siempre mostramos la confirmación.
      await reenviarCodigoRecuperacion({ correo: values.correo });
      setReenviado(true);
    } catch (err) {
      setErrorServidor(err.message);
    } finally {
      setReenviando(false);
    }
  };

  return (
    <main className="flex flex-1 items-center justify-center bg-section px-4 py-12">
      <div className="animate-fade-in-up w-full max-w-md rounded-2xl bg-cream p-8 shadow-lg shadow-primary/10">
        <h1 className="mb-1 text-2xl font-bold">Restablecer contraseña</h1>

        {listo ? (
          <p className="mt-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
            Contraseña restablecida correctamente. Redirigiendo al inicio de sesión...
          </p>
        ) : (
          <>
            {parametros.get("enviado") === "1" && (
              <div className="mb-4 flex items-center gap-2 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 p-3 text-sm text-emerald-800 dark:text-emerald-300">
                <span>📨</span>
                <span>
                  Te enviamos un código de 6 dígitos a tu correo. Ingrésalo a continuación junto con tu nueva contraseña.
                </span>
              </div>
            )}

            <p className="mb-6 text-sm text-primary/70">
              Escribe el código de 6 dígitos que te enviamos por correo
              (vigente por 10 minutos) junto con tu nueva contraseña.
            </p>

            <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
              <Input
                label="Correo electrónico"
                name="correo"
                type="email"
                required
                maxLength={60}
                value={values.correo}
                onChange={handleChange}
                onBlur={handleBlur}
                error={errors.correo}
                touched={touched.correo}
                placeholder="tucorreo@ejemplo.com"
                autoComplete="email"
              />
              <Input
                label="Código de recuperación"
                name="codigo"
                type="text"
                required
                maxLength={6}
                value={values.codigo}
                onChange={handleChange}
                onBlur={handleBlur}
                error={errors.codigo}
                touched={touched.codigo}
                placeholder="123456"
                autoComplete="one-time-code"
              />
              <Input
                label="Contraseña nueva"
                name="passwordNueva"
                type="password"
                required
                maxLength={32}
                value={values.passwordNueva}
                onChange={handleChange}
                onBlur={handleBlur}
                error={errors.passwordNueva}
                touched={touched.passwordNueva}
                autoComplete="new-password"
              />
              <Input
                label="Confirmar contraseña nueva"
                name="confirmarPasswordNueva"
                type="password"
                required
                maxLength={32}
                value={values.confirmarPasswordNueva}
                onChange={handleChange}
                onBlur={handleBlur}
                error={errors.confirmarPasswordNueva}
                touched={touched.confirmarPasswordNueva}
                autoComplete="new-password"
              />

              <Button type="submit" fullWidth disabled={enviando}>
                {enviando ? "Guardando..." : "Guardar nueva contraseña"}
              </Button>
            </form>

            {errorServidor && (
              <p className="mt-4 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">
                {errorServidor}
              </p>
            )}

            {!reenviado ? (
              <Button
                variant="ghost"
                className="mt-4"
                onClick={handleReenviar}
                disabled={reenviando}
              >
                {reenviando ? "Enviando..." : "Reenviar código"}
              </Button>
            ) : (
              <p className="mt-4 text-sm text-primary/70">
                Si tu correo está registrado, te enviamos un nuevo código.
              </p>
            )}

            <p className="mt-6 text-center text-sm text-primary/70">
              <Link to="/login" className="font-medium text-primary hover:underline">
                Volver al inicio de sesión
              </Link>
            </p>
          </>
        )}
      </div>
    </main>
  );
}

export default ResetPassword;
