import { useEffect, useState } from "react";
import useForm from "../../hooks/useForm";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import {
  validarNombre,
  validarDireccion,
  validarTelefono,
  validarPasswordLogin,
  validarPasswordNueva,
  validarConfirmarPassword,
} from "../../utils/validators";
import { obtenerPerfil, actualizarPerfil, cambiarPassword } from "../../utils/api";

const validadoresDatos = {
  nombre: validarNombre,
  apellido: validarNombre,
  direccion: validarDireccion,
  telefono: validarTelefono,
};

const validadoresPassword = {
  passwordActual: validarPasswordLogin,
  passwordNueva: validarPasswordNueva,
  confirmarPasswordNueva: (valor, valores) =>
    validarConfirmarPassword(valor, { password: valores.passwordNueva }),
};

function MiPerfil() {
  const [perfil, setPerfil] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    obtenerPerfil()
      .then(setPerfil)
      .catch((err) => setError(err.message))
      .finally(() => setCargando(false));
  }, []);

  if (cargando) return <p className="text-sm text-primary/70">Cargando tu perfil...</p>;
  if (error) return <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{error}</p>;
  if (!perfil) return null;

  return (
    <div className="flex flex-col gap-8">
      <FormularioDatos perfil={perfil} onActualizado={setPerfil} />
      <FormularioPassword />
    </div>
  );
}

function FormularioDatos({ perfil, onActualizado }) {
  const { values, errors, touched, handleChange, handleBlur, validateAll } = useForm(
    {
      nombre: perfil.nombre,
      apellido: perfil.apellido,
      direccion: perfil.direccion,
      telefono: perfil.telefono,
    },
    validadoresDatos
  );
  const [enviando, setEnviando] = useState(false);
  const [mensaje, setMensaje] = useState("");
  const [errorServidor, setErrorServidor] = useState("");

  const handleSubmit = async (evento) => {
    evento.preventDefault();
    setMensaje("");
    setErrorServidor("");
    if (!validateAll()) return;

    setEnviando(true);
    try {
      await actualizarPerfil(values);
      onActualizado({ ...perfil, ...values });
      setMensaje("Tus datos se actualizaron correctamente.");
    } catch (err) {
      setErrorServidor(err.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <section className="rounded-2xl border border-beige/60 bg-cream p-6">
      <h2 className="mb-1 text-lg font-semibold text-primary">Mis datos</h2>
      <p className="mb-4 text-sm text-primary/70">
        Correo: <span className="font-medium text-primary">{perfil.correo}</span> · Rol:{" "}
        <span className="font-medium capitalize text-primary">{perfil.rol}</span>
      </p>

      <form onSubmit={handleSubmit} noValidate className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Nombre"
          name="nombre"
          required
          maxLength={30}
          value={values.nombre}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.nombre}
          touched={touched.nombre}
        />
        <Input
          label="Apellido"
          name="apellido"
          required
          maxLength={30}
          value={values.apellido}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.apellido}
          touched={touched.apellido}
        />
        <Input
          label="Dirección"
          name="direccion"
          required
          maxLength={80}
          value={values.direccion}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.direccion}
          touched={touched.direccion}
        />
        <Input
          label="Teléfono"
          name="telefono"
          required
          maxLength={15}
          value={values.telefono}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.telefono}
          touched={touched.telefono}
        />

        <div className="sm:col-span-2">
          <Button type="submit" disabled={enviando}>
            {enviando ? "Guardando..." : "Guardar cambios"}
          </Button>
        </div>
      </form>

      {errorServidor && (
        <p className="mt-3 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorServidor}</p>
      )}
      {mensaje && (
        <p className="mt-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">{mensaje}</p>
      )}
    </section>
  );
}

function FormularioPassword() {
  const { values, errors, touched, handleChange, handleBlur, validateAll, resetForm } = useForm(
    { passwordActual: "", passwordNueva: "", confirmarPasswordNueva: "" },
    validadoresPassword
  );
  const [enviando, setEnviando] = useState(false);
  const [mensaje, setMensaje] = useState("");
  const [errorServidor, setErrorServidor] = useState("");

  const handleSubmit = async (evento) => {
    evento.preventDefault();
    setMensaje("");
    setErrorServidor("");
    if (!validateAll()) return;

    setEnviando(true);
    try {
      await cambiarPassword({
        passwordActual: values.passwordActual,
        passwordNueva: values.passwordNueva,
      });
      setMensaje("Contraseña actualizada correctamente.");
      resetForm();
    } catch (err) {
      setErrorServidor(err.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <section className="rounded-2xl border border-beige/60 bg-cream p-6">
      <h2 className="mb-1 text-lg font-semibold text-primary">Cambiar contraseña</h2>
      <p className="mb-4 text-sm text-primary/70">
        Tu contraseña se guarda siempre cifrada (bcrypt); ni el equipo de Dulce Esencia puede verla en texto plano.
      </p>

      <form onSubmit={handleSubmit} noValidate className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Contraseña actual"
          name="passwordActual"
          type="password"
          required
          maxLength={32}
          value={values.passwordActual}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.passwordActual}
          touched={touched.passwordActual}
          autoComplete="current-password"
        />
        <div className="hidden sm:block" />
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

        <div className="sm:col-span-2">
          <Button type="submit" variant="secondary" disabled={enviando}>
            {enviando ? "Actualizando..." : "Actualizar contraseña"}
          </Button>
        </div>
      </form>

      {errorServidor && (
        <p className="mt-3 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorServidor}</p>
      )}
      {mensaje && (
        <p className="mt-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">{mensaje}</p>
      )}
    </section>
  );
}

export default MiPerfil;
