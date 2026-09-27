import { useState } from "react";
import { useNavigate } from "react-router-dom";
import useForm from "../hooks/useForm";
import Input from "./ui/Input";
import Select from "./ui/Select";
import Button from "./ui/Button";
import Icon from "./ui/Icon";
import ICON_PATHS from "./ui/iconPaths";
import { registrarUsuario } from "../utils/api";
import {
  validarNombre,
  validarDocumento,
  validarDireccion,
  validarTelefono,
  validarCorreo,
  validarPassword,
  validarConfirmarPassword,
  validarSeleccion,
} from "../utils/validators";

const TIPOS_DOCUMENTO = [
  { value: "CC", label: "Cédula de ciudadanía" },
  { value: "TI", label: "Tarjeta de identidad" },
  { value: "CE", label: "Cédula de extranjería" },
  { value: "PA", label: "Pasaporte" },
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
};

/**
 * Formulario de registro de clientes, pensado para vivir dentro del
 * componente Modal. Usa el hook reutilizable useForm para el estado
 * y las validaciones en tiempo real.
 */
function RegisterModal({ onRegistroExitoso }) {
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
  // El registro ya no deja al usuario listo para iniciar sesión de
  // inmediato: el backend exige verificar el correo primero (ver
  // POST /usuarios/registro). "registrado" controla si mostramos el
  // formulario o el aviso de "revisa tu correo".
  const [registrado, setRegistrado] = useState(false);
  const [correoRegistrado, setCorreoRegistrado] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (evento) => {
    evento.preventDefault();
    setErrorServidor("");
    const esValido = validateAll();
    if (!esValido) return;

    setEnviando(true);
    try {
      await registrarUsuario(values);
      setCorreoRegistrado(values.correo);
      setRegistrado(true);
      resetForm();
    } catch (error) {
      setErrorServidor(error.message);
    } finally {
      setEnviando(false);
    }
  };

  // Cierra el modal (misma responsabilidad de siempre de
  // onRegistroExitoso) y lleva a la persona directo al formulario
  // donde escribe el código OTP de 6 dígitos que le acaba de llegar
  // por correo, con el correo ya precargado.
  const handleIrAVerificar = () => {
    onRegistroExitoso?.();
    navigate(`/verificar-correo?correo=${encodeURIComponent(correoRegistrado)}`);
  };

  if (registrado) {
    return (
      <div className="flex flex-col items-center gap-4 py-2 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Icon path={ICON_PATHS.check} className="h-6 w-6" />
        </div>
        <p className="text-sm text-primary/70">
          Cuenta creada. Te enviamos un código de 6 dígitos a{" "}
          <span className="font-medium text-primary">{correoRegistrado}</span>. Escríbelo para
          activar tu cuenta antes de iniciar sesión.
        </p>
        <Button onClick={handleIrAVerificar}>Verificar mi correo</Button>
      </div>
    );
  }

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
          placeholder="Repite tu contraseña"
          autoComplete="new-password"
        />
      </div>

      <p className="text-xs text-primary/70">
        La contraseña debe combinar mayúsculas, minúsculas y números.
      </p>

      {errorServidor && (
        <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorServidor}</p>
      )}

      <Button type="submit" fullWidth disabled={enviando}>
        {enviando ? "Creando cuenta..." : "Crear cuenta"}
      </Button>
    </form>
  );
}

export default RegisterModal;
