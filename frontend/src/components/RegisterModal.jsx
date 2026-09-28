import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
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

  const handleIrAVerificar = () => {
    onRegistroExitoso?.();
    navigate(`/verificar-correo?correo=${encodeURIComponent(correoRegistrado)}`);
  };

  return (
    <AnimatePresence mode="wait">
      {registrado ? (
        <motion.div
          key="success"
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 1.05, y: -10 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col items-center gap-4 py-2 text-center"
        >
          <motion.div 
            initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", bounce: 0.5, delay: 0.2 }}
            className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary"
          >
            <Icon path={ICON_PATHS.check} className="h-6 w-6" />
          </motion.div>
          <p className="text-sm text-primary/70">
            Cuenta creada. Te enviamos un código de 6 dígitos a{" "}
            <span className="font-medium text-primary">{correoRegistrado}</span>. Escríbelo para
            activar tu cuenta antes de iniciar sesión.
          </p>
          <Button onClick={handleIrAVerificar}>Verificar mi correo</Button>
        </motion.div>
      ) : (
        <motion.form
          key="form"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 20 }}
          transition={{ duration: 0.3 }}
          onSubmit={handleSubmit}
          noValidate
          className="flex flex-col gap-4"
        >
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
            <motion.p initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorServidor}</motion.p>
          )}

          <Button type="submit" fullWidth disabled={enviando}>
            {enviando ? "Creando cuenta..." : "Crear cuenta"}
          </Button>
        </motion.form>
      )}
    </AnimatePresence>
  );
}

export default RegisterModal;
