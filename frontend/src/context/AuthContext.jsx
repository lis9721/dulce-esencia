import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { obtenerPerfil, cerrarSesion as cerrarSesionApi } from "../utils/api";

const AuthContext = createContext(null);

/**
 * AuthProvider
 * Envuelve toda la app (ver main.jsx) y le da a cualquier componente
 * acceso a: usuario, isAuthenticated, cargando, login(), logout().
 * Así el Header ("navbar autenticado"), las rutas protegidas y los
 * paneles saben en todo momento quién está conectado y con qué rol.
 *
 * El JWT vive únicamente en una cookie httpOnly puesta por el backend
 * (ver /login en backend/routes/usuarios.routes.js): este componente
 * nunca lo lee, guarda ni manipula directamente. Como JavaScript no
 * puede leer una cookie httpOnly, no hay token expuesto que un XSS
 * pueda robar — a diferencia del esquema anterior con
 * localStorage/sessionStorage.
 *
 * Al no tener acceso al token, este componente no puede "saber" si hay
 * sesión iniciada solo mirando el almacenamiento local: se lo pregunta
 * al backend (GET /usuarios/perfil, protegido) al montar la app. Si la
 * cookie es válida, el backend responde con los datos del usuario; si
 * no, responde 401 y se asume que no hay sesión.
 */
export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);

  const logout = useCallback(async () => {
    try {
      await cerrarSesionApi();
    } catch {
      // Si la petición de logout falla (p. ej. sin conexión), igual
      // limpiamos el estado local: para el usuario, la sesión se cierra
      // de inmediato en esta pestaña.
    } finally {
      setUsuario(null);
    }
  }, []);

  // Al cargar la app, pregunta al backend si la cookie de sesión sigue
  // siendo válida y, de ser así, trae los datos del usuario.
  useEffect(() => {
    let cancelado = false;

    obtenerPerfil()
      .then((datos) => {
        if (!cancelado) setUsuario(datos);
      })
      .catch(() => {
        if (!cancelado) setUsuario(null);
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });

    return () => {
      cancelado = true;
    };
  }, []);

  // Si CUALQUIER petición protegida responde 401 (el token expiró o fue
  // invalidado mientras la persona seguía usando la app), api.js dispara
  // este evento y cerramos la sesión de inmediato, no solo al recargar.
  useEffect(() => {
    const alTokenInvalido = () => setUsuario(null);
    window.addEventListener("essentia:token-invalido", alTokenInvalido);
    return () => window.removeEventListener("essentia:token-invalido", alTokenInvalido);
  }, []);

  // Se llama después de un login exitoso. El backend ya dejó la cookie
  // httpOnly con el JWT; aquí solo guardamos en memoria los datos del
  // usuario que devolvió la respuesta de /login, para la UI (avatar,
  // nombre, rol, etc.).
  const login = useCallback((datosUsuario) => {
    setUsuario(datosUsuario);
  }, []);

  const value = useMemo(
    () => ({
      usuario,
      cargando,
      isAuthenticated: Boolean(usuario),
      login,
      logout,
    }),
    [usuario, cargando, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthContext;
