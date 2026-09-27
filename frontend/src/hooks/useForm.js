import { useCallback, useMemo, useState } from "react";

/**
 * Hook reutilizable para manejar el estado, el "touched" y las
 * validaciones en tiempo real de cualquier formulario.
 * @param {Object} valoresIniciales - valores iniciales del formulario.
 * @param {Object} validadores - objeto { nombreCampo: funcionValidadora }.
 *   Cada función recibe (valor, valoresCompletos) y retorna un mensaje
 *   de error o "" si el campo es válido.
 */
// Dado el nombre de un campo de confirmación (p. ej. "confirmarPassword" o
// "confirmarPasswordNueva"), devuelve el nombre del campo "fuente" del que
// depende (p. ej. "password" o "passwordNueva"). Esto permite que el hook
// funcione con cualquier convención de nombres del tipo confirmarX -> X,
// en vez de tener hardcodeados los nombres usados por un único formulario.
function obtenerCampoFuenteDeConfirmacion(nombreCampo) {
  if (!nombreCampo.startsWith("confirmar")) return null;
  const resto = nombreCampo.slice("confirmar".length);
  if (!resto) return null;
  return resto.charAt(0).toLowerCase() + resto.slice(1);
}

function useForm(valoresIniciales, validadores = {}) {
  const [values, setValues] = useState(valoresIniciales);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});

  // Mapa { campoFuente: campoConfirmacion } derivado de los validadores
  // registrados, para saber qué revalidar cuando cambia el campo fuente.
  const camposDeConfirmacion = useMemo(() => {
    const mapa = {};
    Object.keys(validadores).forEach((nombreCampo) => {
      const fuente = obtenerCampoFuenteDeConfirmacion(nombreCampo);
      if (fuente) mapa[fuente] = nombreCampo;
    });
    return mapa;
  }, [validadores]);

  const validarCampo = useCallback(
    (nombre, valor, todosLosValores) => {
      const validar = validadores[nombre];
      if (!validar) return "";
      return validar(valor, todosLosValores) || "";
    },
    [validadores]
  );

  const handleChange = useCallback(
    (evento) => {
      const { name, value, type, checked } = evento.target;
      const nuevoValor = type === "checkbox" ? checked : value;
      const nuevosValores = { ...values, [name]: nuevoValor };

      setValues(nuevosValores);

      // Validación en tiempo real: solo una vez que el campo fue tocado,
      // para no mostrar errores mientras el usuario aún no ha interactuado.
      if (touched[name]) {
        setErrors((prev) => ({
          ...prev,
          [name]: validarCampo(name, nuevoValor, nuevosValores),
        }));
      }

      // Si el campo que cambió es la "fuente" de algún campo de confirmación
      // registrado (p. ej. "password" -> "confirmarPassword", o
      // "passwordNueva" -> "confirmarPasswordNueva"), ese campo de
      // confirmación también se revalida en vivo, siempre que ya haya sido
      // tocado por el usuario.
      const campoConfirmacion = camposDeConfirmacion[name];
      if (campoConfirmacion && touched[campoConfirmacion]) {
        setErrors((prev) => ({
          ...prev,
          [campoConfirmacion]: validarCampo(
            campoConfirmacion,
            nuevosValores[campoConfirmacion],
            nuevosValores
          ),
        }));
      }
    },
    [values, touched, validarCampo, camposDeConfirmacion]
  );

  const handleBlur = useCallback(
    (evento) => {
      const { name, value } = evento.target;
      setTouched((prev) => ({ ...prev, [name]: true }));
      setErrors((prev) => ({
        ...prev,
        [name]: validarCampo(name, value, values),
      }));
    },
    [validarCampo, values]
  );

  const validateAll = useCallback(() => {
    const nuevosErrores = {};
    Object.keys(validadores).forEach((nombre) => {
      nuevosErrores[nombre] = validarCampo(nombre, values[nombre], values);
    });

    setErrors(nuevosErrores);
    setTouched(
      Object.keys(validadores).reduce((acumulado, nombre) => {
        acumulado[nombre] = true;
        return acumulado;
      }, {})
    );

    return Object.values(nuevosErrores).every((error) => !error);
  }, [validadores, validarCampo, values]);

  const resetForm = useCallback(() => {
    setValues(valoresIniciales);
    setErrors({});
    setTouched({});
  }, [valoresIniciales]);

  const isValid = useMemo(
    () => Object.values(errors).every((error) => !error),
    [errors]
  );

  return {
    values,
    errors,
    touched,
    handleChange,
    handleBlur,
    validateAll,
    resetForm,
    isValid,
    setValues,
  };
}

export default useForm;
