import { useState } from "react";
import useForm from "../../hooks/useForm";
import Input from "./Input";
import Select from "./Select";
import Button from "./Button";
import { crearUsuario } from "../../utils/api";
import {
  validarNombre,
  validarDocumento,
  validarDireccion,
  validarTelefono,
  validarCorreo,
  validarPassword,
  validarConfirmarPassword,
  validarSeleccion,
} from "../../utils/validators";

const TIPOS_DOCUMENTO = [
  { value: "CC", label: "Cédula de ciudadanía" },
  { value: "TI", label: "Tarjeta de identidad" },
  { value: "CE", label: "Cédula de extranjería" },
  { value: "PA", label: "Pasaporte" },
];

const ROLES = [
  { value: "cliente", label: "Cliente" },
  { value: "empleado", label: "Empleado" },
  { value: "admin", label: "Admin" },
];

const valoresIniciales = {
  nombre: "",
  apellido: "",
  tipoDocumento: "",
  numeroDocumento: "",
  direccion: "",
  telefono: "",
  correo: "",
  password: "",
  confirmarPassword: "",
  rol: "",
};

const validadores = {
  nombre: validarNombre,
  apellido: validarNombre,
  tipoDocumento: validarSeleccion,
  numeroDocumento: validarDocumento,
  direccion: validarDireccion,
  telefono: validarTelefono,
  correo: validarCorreo,
  password: validarPassword,
  confirmarPassword: validarConfirmarPassword,
  rol: validarSeleccion,
};

/**
 * Formulario para que un admin cree un usuario directamente desde
 * `/panel/usuarios` (a diferencia de RegisterModal, que es público y
 * siempre crea un `cliente`): pide los mismos campos del registro,
 * más el rol, y el backend marca la cuenta como ya verificada y
 * activa (POST /api/usuarios, ver comentario en usuarios.routes.js).
 *
 * Reutiliza el mismo hook useForm y los mismos validadores del
 * registro público, para que las reglas (longitud, formato, etc.)
 * sean idénticas en los dos formularios.
 */
function CrearUsuarioModal({ onCreado }) {
  const {
    values,
    errors,
    touched,
    handleChange,
    handleBlur,
    validateAll,
    resetForm,
  } = useForm(valoresIniciales, validadores);
  const [enviando, setEnviando] = useState(false);
  const [errorServidor, setErrorServidor] = useState("");

  const handleSubmit = async (evento) => {
    evento.preventDefault();
    setErrorServidor("");
    const esValido = validateAll();
    if (!esValido) return;

    setEnviando(true);
    try {
      // confirmarPassword solo existe para la validación en el frontend;
      // el backend no la espera (ver POST /api/usuarios).
      const { confirmarPassword: _confirmarPassword, ...datos } = values;
      await crearUsuario(datos);
      resetForm();
      onCreado?.();
    } catch (error) {
      setErrorServidor(error.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
          placeholder="Ej: Luisa"
          autoComplete="given-name"
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
          placeholder="Ej: Gómez"
          autoComplete="family-name"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Select
          label="Tipo de documento"
          name="tipoDocumento"
          required
          value={values.tipoDocumento}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.tipoDocumento}
          touched={touched.tipoDocumento}
          options={TIPOS_DOCUMENTO}
        />
        <Input
          label="Número de documento"
          name="numeroDocumento"
          required
          maxLength={15}
          value={values.numeroDocumento}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.numeroDocumento}
          touched={touched.numeroDocumento}
          placeholder="Ej: 1020304050"
        />
      </div>

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
        placeholder="Ej: Cra 45 # 12-30, Medellín"
        autoComplete="street-address"
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
          placeholder="Ej: 3001234567"
          autoComplete="tel"
        />
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
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
          placeholder="Mínimo 8 caracteres"
          autoComplete="new-password"
        />
        <Input
          label="Confirmar contraseña"
          name="confirmarPassword"
          type="password"
          required
          maxLength={32}
          value={values.confirmarPassword}
          onChange={handleChange}
          onBlur={handleBlur}
          error={errors.confirmarPassword}
          touched={touched.confirmarPassword}
          placeholder="Repite la contraseña"
          autoComplete="new-password"
        />
      </div>

      <Select
        label="Rol"
        name="rol"
        required
        value={values.rol}
        onChange={handleChange}
        onBlur={handleBlur}
        error={errors.rol}
        touched={touched.rol}
        options={ROLES}
      />

      <p className="text-xs text-primary/70">
        La contraseña debe combinar mayúsculas, minúsculas y números. A
        diferencia del registro público, esta cuenta queda activa y
        verificada de inmediato: la persona ya puede iniciar sesión sin
        pasar por el correo de verificación.
      </p>

      {errorServidor && (
        <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorServidor}</p>
      )}

      <Button type="submit" fullWidth disabled={enviando}>
        {enviando ? "Creando usuario..." : "Crear usuario"}
      </Button>
    </form>
  );
}

export default CrearUsuarioModal;
