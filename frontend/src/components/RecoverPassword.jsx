import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Input from "./ui/Input";
import Button from "./ui/Button";
import Icon from "./ui/Icon";
import ICON_PATHS from "./ui/iconPaths";
import { validarCorreo } from "../utils/validators";
import { recuperarPassword } from "../utils/api";

/**
 * Componente reutilizable e independiente del Login.
 * Gestiona sus propios valores, estado y validaciones con Hooks.
 */
function RecoverPassword({ onVolver }) {
  const [correo, setCorreo] = useState("");
  const [error, setError] = useState("");
  const [tocado, setTocado] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [errorServidor, setErrorServidor] = useState("");
  const navigate = useNavigate();

  const handleChange = (evento) => {
    const valor = evento.target.value;
    setCorreo(valor);
    if (tocado) setError(validarCorreo(valor));
  };

  const handleBlur = () => {
    setTocado(true);
    setError(validarCorreo(correo));
  };

  const handleSubmit = async (evento) => {
    evento.preventDefault();
    setTocado(true);
    setErrorServidor("");
    const errorActual = validarCorreo(correo);
    setError(errorActual);
    if (errorActual) return;

    setEnviando(true);
    try {
      // El backend siempre responde con el mismo mensaje exista o no el
      // correo, para no revelar qué cuentas están registradas.
      await recuperarPassword({ correo });
      setEnviado(true);
    } catch (err) {
      setErrorServidor(err.message);
    } finally {
      setEnviando(false);
    }
  };

  // Lleva a la persona al formulario donde escribe el código de 6
  // dígitos (OTP) junto con su contraseña nueva, con el correo ya
  // precargado — así no tiene que volver a escribirlo.
  const handleContinuar = () => {
    navigate(`/restablecer-password?correo=${encodeURIComponent(correo)}`);
  };

  if (enviado) {
    return (
      <div className="flex flex-col items-center gap-4 py-2 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Icon path={ICON_PATHS.check} className="h-6 w-6" />
        </div>
        <p className="text-sm text-primary/70">
          Si <span className="font-medium text-primary">{correo}</span> está
          registrado, te enviamos un código de 6 dígitos para restablecer tu
          contraseña.
        </p>
        <Button onClick={handleContinuar} fullWidth>
          Ya tengo el código
        </Button>
        <button
          type="button"
          onClick={onVolver}
          className="text-sm font-medium text-primary hover:underline"
        >
          ← Volver al inicio de sesión
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <p className="text-sm text-primary/70">
        Escribe tu correo electrónico y te enviaremos un código de 6 dígitos
        para recuperar tu contraseña.
      </p>

      <Input
        label="Correo electrónico"
        name="correo"
        type="email"
        required
        maxLength={60}
        value={correo}
        onChange={handleChange}
        onBlur={handleBlur}
        error={error}
        touched={tocado}
        placeholder="tucorreo@ejemplo.com"
        autoComplete="email"
      />

      <Button type="submit" fullWidth disabled={enviando}>
        {enviando ? "Enviando..." : "Enviar código"}
      </Button>

      {errorServidor && (
        <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorServidor}</p>
      )}

      <button
        type="button"
        onClick={onVolver}
        className="text-sm font-medium text-primary hover:underline"
      >
        ← Volver al inicio de sesión
      </button>
    </form>
  );
}

export default RecoverPassword;
