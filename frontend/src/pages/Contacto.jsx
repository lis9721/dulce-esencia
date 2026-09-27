import { useState } from "react";
import useForm from "../hooks/useForm";
import Input from "../components/ui/Input";
import Textarea from "../components/ui/Textarea";
import Button from "../components/ui/Button";
import Reveal from "../components/Reveal";
import { validarNombreContacto, validarCorreo } from "../utils/validators";
import { enviarMensajeContacto } from "../utils/api";
import useDocumentTitle from "../hooks/useDocumentTitle";

const valoresIniciales = { nombre: "", correo: "", mensaje: "" };

function validarMensaje(value) {
  const valor = (value || "").trim();
  if (!valor) return "El mensaje es obligatorio.";
  if (valor.length < 10) return "Cuéntanos un poco más (mínimo 10 caracteres).";
  if (valor.length > 500) return "Debe tener máximo 500 caracteres.";
  return "";
}

const validadores = { nombre: validarNombreContacto, correo: validarCorreo, mensaje: validarMensaje };

function Contacto() {
  useDocumentTitle(
    "Contacto",
    "Escríbenos y te responderemos lo antes posible. Correo, teléfono y dirección de Dulce Esencia Pastelería.",
    "/contacto"
  );

  const { values, errors, touched, handleChange, handleBlur, validateAll, resetForm } = useForm(
    valoresIniciales,
    validadores
  );
  const [enviando, setEnviando] = useState(false);
  const [mensajeExito, setMensajeExito] = useState("");
  const [errorServidor, setErrorServidor] = useState("");

  const handleSubmit = async (evento) => {
    evento.preventDefault();
    setErrorServidor("");
    setMensajeExito("");
    const esValido = validateAll();
    if (!esValido) return;

    setEnviando(true);
    try {
      const respuesta = await enviarMensajeContacto(values);
      setMensajeExito(respuesta.mensaje);
      resetForm();
    } catch (error) {
      setErrorServidor(error.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <main className="flex-1">
      <Reveal>
        <section className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6">
          <h1 className="text-3xl font-bold sm:text-4xl">Contacto</h1>
          <p className="mx-auto mt-3 max-w-md text-primary/70">
            ¿Tienes alguna pregunta? Escríbenos y te responderemos lo antes posible.
          </p>
        </section>
      </Reveal>

      <Reveal>
        <section className="mx-auto grid max-w-4xl gap-8 px-4 pb-16 sm:px-6 md:grid-cols-2">
          {/* Datos de contacto */}
          <div className="flex flex-col gap-3">
            <div className="rounded-xl border border-beige/70 bg-cream px-5 py-4 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-md">
              <p className="text-xs font-medium uppercase tracking-wide text-primary/70">Correo</p>
              <p className="text-primary/80">contacto@dulceesencia.com</p>
            </div>
            <div className="rounded-xl border border-beige/70 bg-cream px-5 py-4 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-md">
              <p className="text-xs font-medium uppercase tracking-wide text-primary/70">Teléfono</p>
              <p className="text-primary/80">+57 300 000 0000</p>
            </div>
            <div className="rounded-xl border border-beige/70 bg-cream px-5 py-4 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-md">
              <p className="text-xs font-medium uppercase tracking-wide text-primary/70">Dirección</p>
              <p className="text-primary/80">Pastelería Dulce Esencia, Medellín, Colombia</p>
            </div>
          </div>

          {/* Formulario de contacto */}
          <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4 text-left">
            <Input
              label="Nombre"
              name="nombre"
              required
              maxLength={60}
              value={values.nombre}
              onChange={handleChange}
              onBlur={handleBlur}
              error={errors.nombre}
              touched={touched.nombre}
              placeholder="Tu nombre"
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
            <Textarea
              label="Mensaje"
              name="mensaje"
              required
              rows={5}
              maxLength={500}
              value={values.mensaje}
              onChange={handleChange}
              onBlur={handleBlur}
              error={errors.mensaje}
              touched={touched.mensaje}
              placeholder="Cuéntanos en qué podemos ayudarte"
            />

            {errorServidor && (
              <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{errorServidor}</p>
            )}
            {mensajeExito && (
              <p className="rounded-lg bg-emerald-50 dark:bg-emerald-950/40 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
                {mensajeExito}
              </p>
            )}

            <Button type="submit" fullWidth disabled={enviando}>
              {enviando ? "Enviando..." : "Enviar mensaje"}
            </Button>
          </form>
        </section>
      </Reveal>
    </main>
  );
}

export default Contacto;
