import { useEffect, useRef, useState } from "react";
import { enviarMensajeChatbot, obtenerConversacionChatbot } from "../utils/api";

/**
 * Chatbot
 * Widget flotante de atención al cliente con IA (requerimientos 17-19
 * del quinto avance). Se monta una sola vez en App.jsx, igual que
 * WhatsAppButton, para quedar disponible en todo el sitio.
 *
 * Funciona con o sin sesión iniciada: para un visitante sin cuenta se
 * guarda un `sesionId` propio en localStorage para poder mantener el
 * mismo hilo de conversación entre mensajes (ver
 * backend/app/routes/chatbot.py).
 */

const CLAVE_SESION = "essentia_chat_sesion";
const CLAVE_CONVERSACION = "essentia_chat_conversacion";

function obtenerSesionId() {
  let sesionId = localStorage.getItem(CLAVE_SESION);
  if (!sesionId) {
    sesionId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
    localStorage.setItem(CLAVE_SESION, sesionId);
  }
  return sesionId;
}

const MENSAJE_BIENVENIDA = {
  rol: "asistente",
  contenido:
    "¡Hola! Soy el asistente virtual de Dulce Esencia Pastelería. Puedo ayudarte con dudas sobre productos, servicios, el proceso de compra o registrar una PQR. ¿En qué te ayudo?",
};

function Chatbot() {
  const [abierto, setAbierto] = useState(false);
  const [mensajes, setMensajes] = useState([MENSAJE_BIENVENIDA]);
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");
  const conversacionIdRef = useRef(
    typeof window !== "undefined" ? sessionStorage.getItem(CLAVE_CONVERSACION) : null
  );
  const restauradaRef = useRef(false);
  const finalRef = useRef(null);

  useEffect(() => {
    if (abierto) finalRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensajes, abierto]);

  // Restaura el historial de la conversación (mismo hilo guardado en
  // sessionStorage) la primera vez que se abre el widget, en vez de
  // mostrar siempre el mensaje de bienvenida solo: `obtenerConversacionChatbot`
  // ya existía en utils/api.js pero nunca se llamaba desde acá.
  useEffect(() => {
    if (!abierto || restauradaRef.current || !conversacionIdRef.current) return;
    restauradaRef.current = true;

    obtenerConversacionChatbot(conversacionIdRef.current)
      .then((conversacion) => {
        if (!conversacion.mensajes?.length) return;
        setMensajes([
          MENSAJE_BIENVENIDA,
          ...conversacion.mensajes.map((m) => ({
            rol: m.rol === "usuario" ? "usuario" : "asistente",
            contenido: m.contenido,
          })),
        ]);
      })
      .catch(() => {
        // El hilo ya no existe o no pertenece a este visitante/usuario
        // (por ejemplo, cerró sesión en otra pestaña): se empieza de
        // cero en vez de dejar el chat roto.
        conversacionIdRef.current = null;
        sessionStorage.removeItem(CLAVE_CONVERSACION);
      });
  }, [abierto]);

  const enviar = async (evento) => {
    evento.preventDefault();
    const mensaje = texto.trim();
    if (!mensaje || enviando) return;

    setMensajes((prev) => [...prev, { rol: "usuario", contenido: mensaje }]);
    setTexto("");
    setEnviando(true);
    setError("");

    try {
      const respuesta = await enviarMensajeChatbot({
        mensaje,
        conversacionId: conversacionIdRef.current || undefined,
        sesionId: obtenerSesionId(),
      });
      conversacionIdRef.current = respuesta.conversacionId;
      sessionStorage.setItem(CLAVE_CONVERSACION, String(respuesta.conversacionId));
      setMensajes((prev) => [...prev, { rol: "asistente", contenido: respuesta.respuesta }]);
    } catch (err) {
      setError(err.message || "No se pudo enviar el mensaje. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      {abierto && (
        <div className="fixed bottom-24 right-5 z-50 flex h-[28rem] w-[22rem] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-2xl border border-beige/60 bg-cream shadow-2xl">
          <header className="flex items-center justify-between bg-primary px-4 py-3 text-cream">
            <div>
              <p className="text-sm font-semibold">Asistente Dulce Esencia</p>
              <p className="text-xs opacity-80">Atención con IA</p>
            </div>
            <button
              type="button"
              aria-label="Cerrar chat"
              onClick={() => setAbierto(false)}
              className="rounded-full p-1 text-cream/80 hover:bg-cream/10 hover:text-cream"
            >
              ✕
            </button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-3 py-3">
            {mensajes.map((m, indice) => (
              <div
                key={indice}
                className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                  m.rol === "usuario"
                    ? "ml-auto bg-primary text-cream"
                    : "bg-section text-primary/90"
                }`}
              >
                {m.contenido}
              </div>
            ))}
            {enviando && <p className="text-xs text-primary/70">Escribiendo...</p>}
            <div ref={finalRef} />
          </div>

          {error && <p className="px-3 pb-1 text-xs text-peligro-fuerte">{error}</p>}

          <form onSubmit={enviar} className="flex items-center gap-2 border-t border-beige/60 p-3">
            <input
              type="text"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              placeholder="Escribe tu mensaje..."
              maxLength={1000}
              className="flex-1 rounded-full border border-beige bg-cream px-3 py-2 text-sm text-primary outline-none focus:border-primary"
            />
            <button
              type="submit"
              disabled={enviando || !texto.trim()}
              className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-cream transition hover:bg-primary-dark disabled:opacity-50"
            >
              Enviar
            </button>
          </form>
        </div>
      )}

      <button
        type="button"
        onClick={() => setAbierto((v) => !v)}
        aria-label={abierto ? "Cerrar asistente virtual" : "Abrir asistente virtual"}
        title="Asistente virtual"
        className="fixed bottom-5 right-24 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-accent text-paper shadow-lg transition-transform duration-200 hover:scale-110 hover:bg-accent-dark focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
      >
        <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z" />
        </svg>
      </button>
    </>
  );
}

export default Chatbot;
