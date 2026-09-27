import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import useForm from "../hooks/useForm";
import Input from "../components/ui/Input";
import Button from "../components/ui/Button";
import { validarCorreo, validarCodigoOtp } from "../utils/validators";
import { verificarCorreo, reenviarVerificacion } from "../utils/api";
import useDocumentTitle from "../hooks/useDocumentTitle";

const validadores = { correo: validarCorreo, codigo: validarCodigoOtp };

/**
 * Página del segundo paso del registro (ver POST /api/usuarios/registro
 * y POST /api/usuarios/verificar-correo en el backend).
 *
 * A diferencia de la versión anterior (que verificaba sola al abrir un
 * enlace con un token largo en la URL), ahora el backend envía por
 * correo un CÓDIGO de 6 dígitos (OTP) que la persona debe escribir a
 * mano aquí. El correo puede venir precargado por query param
 * (?correo=...), como lo hace RegisterModal justo después de crear la
 * cuenta, pero siempre es editable: por si la persona abre esta
 * página directamente o quiere corregir un correo mal escrito.
 */
function VerificarCorreo() {
  useDocumentTitle(
    "Verificación de correo",
    "Verifica tu correo con el código de 6 dígitos para activar tu cuenta de Dulce Esencia Pastelería.",
    "/verificar-correo",
    true
  );

  const [parametros] = useSearchParams();
  const navigate = useNavigate();

  const { values, errors, touched, handleChange, handleBlur, validateAll } = useForm(
    { correo: parametros.get("correo") || "", codigo: "" },
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
    setReenviado(false);
    if (!validateAll()) return;

    setEnviando(true);
    try {
      await verificarCorreo({ correo: values.correo, codigo: values.codigo });
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
      // El backend responde el mismo mensaje genérico exista o no la
      // cuenta (ver POST /usuarios/reenviar-verificacion), así que
      // siempre mostramos la confirmación.
      await reenviarVerificacion({ correo: values.correo });
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
        <h1 className="mb-1 text-2xl font-bold">Verificación de correo</h1>

        {listo ? (
          <>
            <p className="mt-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
              Correo verificado correctamente. Redirigiendo al inicio de sesión...
            </p>
            <Link to="/login" className="mt-6 inline-block">
              <Button>Ir a iniciar sesión</Button>
            </Link>
          </>
        ) : (
          <>
            <p className="mb-6 text-sm text-primary/70">
              Te enviamos un código de 6 dígitos por correo. Escríbelo aquí para
              activar tu cuenta (vigente por 15 minutos).
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
                label="Código de verificación"
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

              <Button type="submit" fullWidth disabled={enviando}>
                {enviando ? "Verificando..." : "Verificar cuenta"}
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
                Si tu cuenta sigue pendiente de verificar, te enviamos un nuevo código.
              </p>
            )}

            <p className="mt-6 text-sm text-primary/70">
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

export default VerificarCorreo;
