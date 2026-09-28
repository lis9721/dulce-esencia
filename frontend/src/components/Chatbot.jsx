import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { enviarMensajeChatbot, obtenerConversacionChatbot } from "../utils/api";
import { useCart } from "../hooks/useCart";
import { formatearPrecio, resolverUrlImagen } from "../utils/formato";

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
 *
 * Funcionalidades:
 *  - Respuestas rápidas (chips) para las consultas más comunes.
 *  - Tarjetas de producto con «Añadir al carrito» directo desde el chat
 *    (el backend las manda en `productos` cuando el mensaje habla de
 *    catálogo).
 *  - Rutas internas del sitio en la respuesta (/tienda, /carrito,
 *    /panel/...) se vuelven enlaces clicables.
 *  - «Nueva conversación» para empezar de cero.
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
    "¡Hola! Soy el asistente virtual de Dulce Esencia Pastelería. Puedo recomendarte productos, contarte el estado de tus pedidos, resolver dudas de compra o registrar una PQR. ¿En qué te ayudo?",
};

const RESPUESTAS_RAPIDAS = [
  "¿Qué tortas tienen?",
  "Quiero algo para 10 personas",
  "¿Cómo puedo pagar?",
  "¿Cómo va mi pedido?",
  "Tengo una queja",
];

// Rutas internas que el asistente puede mencionar; se enlazan con el router.
const REGEX_RUTAS = /(\/(?:tienda|carrito|checkout|contacto|quienes-somos|panel(?:\/[a-z-]+)?))(?![\w/-])/g;

function TextoConEnlaces({ texto, onNavegar }) {
  const partes = texto.split(REGEX_RUTAS);
  return partes.map((parte, i) =>
    i % 2 === 1 ? (
      <Link key={i} to={parte} onClick={onNavegar} className="font-semibold text-accent underline underline-offset-2">
        {parte}
      </Link>
    ) : (
      <span key={i}>{parte}</span>
    )
  );
}

function TarjetaProducto({ producto, onAgregar, estado }) {
  const agotado = Number(producto.stock) <= 0;
  const etiqueta = agotado
    ? "Agotado"
    : estado === "agregando"
      ? "Añadiendo..."
      : estado === "agregado"
        ? "¡Añadido!"
        : estado === "error"
          ? "Reintentar"
          : "Añadir al carrito";

  return (
    <div className="flex items-center gap-3 rounded-xl border border-beige/70 bg-cream p-2">
      {producto.imagen && (
        <img
          src={resolverUrlImagen(producto.imagen)}
          alt=""
          loading="lazy"
          className="h-14 w-14 shrink-0 rounded-lg object-cover"
        />
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-primary">{producto.titulo}</p>
        <p className="text-xs text-primary/70">{formatearPrecio(producto.precio)}</p>
      </div>
      <button
        type="button"
        onClick={() => onAgregar(producto)}
        disabled={agotado || estado === "agregando"}
        className="shrink-0 rounded-lg bg-primary px-2.5 py-1.5 text-xs font-semibold text-cream transition hover:bg-primary-dark disabled:opacity-50"
      >
        {etiqueta}
      </button>
    </div>
  );
}

function Chatbot() {
  const { agregar } = useCart();
  const [abierto, setAbierto] = useState(false);
  const [mensajes, setMensajes] = useState([MENSAJE_BIENVENIDA]);
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");
  // Estado del botón «Añadir» de cada producto: { [id]: "agregando" | "agregado" | "error" }
  const [estadoAgregar, setEstadoAgregar] = useState({});
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
  // mostrar siempre el mensaje de bienvenida solo.
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

  const enviarTexto = async (mensaje) => {
    const limpio = mensaje.trim();
    if (!limpio || enviando) return;

    setMensajes((prev) => [...prev, { rol: "usuario", contenido: limpio }]);
    setTexto("");
    setEnviando(true);
    setError("");

    try {
      const respuesta = await enviarMensajeChatbot({
        mensaje: limpio,
        conversacionId: conversacionIdRef.current || undefined,
        sesionId: obtenerSesionId(),
      });
      conversacionIdRef.current = respuesta.conversacionId;
      sessionStorage.setItem(CLAVE_CONVERSACION, String(respuesta.conversacionId));
      setMensajes((prev) => [
        ...prev,
        { rol: "asistente", contenido: respuesta.respuesta, productos: respuesta.productos || [] },
      ]);
    } catch (err) {
      setError(err.message || "No se pudo enviar el mensaje. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  const enviar = (evento) => {
    evento.preventDefault();
    enviarTexto(texto);
  };

  const agregarDesdeChat = async (producto) => {
    setEstadoAgregar((prev) => ({ ...prev, [producto.id]: "agregando" }));
    try {
      await agregar(producto, 1);
      setEstadoAgregar((prev) => ({ ...prev, [producto.id]: "agregado" }));
      setTimeout(() => {
        setEstadoAgregar((prev) => ({ ...prev, [producto.id]: undefined }));
      }, 1800);
    } catch {
      setEstadoAgregar((prev) => ({ ...prev, [producto.id]: "error" }));
    }
  };

  const nuevaConversacion = () => {
    conversacionIdRef.current = null;
    restauradaRef.current = true;
    sessionStorage.removeItem(CLAVE_CONVERSACION);
    setMensajes([MENSAJE_BIENVENIDA]);
    setEstadoAgregar({});
    setError("");
  };

  const soloBienvenida = mensajes.length === 1;

  return (
    <>
      {abierto && (
        <div className="fixed bottom-24 right-5 z-50 flex h-[32rem] max-h-[calc(100vh-7rem)] w-[23rem] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-2xl border border-beige/60 bg-cream shadow-2xl">
          <header className="flex items-center justify-between bg-primary px-4 py-3 text-cream">
            <div>
              <p className="text-sm font-semibold">Asistente Dulce Esencia</p>
              <p className="text-xs opacity-80">Atención con IA</p>
            </div>
            <div className="flex items-center gap-1">
              {!soloBienvenida && (
                <button
                  type="button"
                  onClick={nuevaConversacion}
                  className="rounded-full px-2 py-1 text-xs text-cream/80 hover:bg-cream/10 hover:text-cream"
                >
                  Nueva
                </button>
              )}
              <button
                type="button"
                aria-label="Cerrar chat"
                onClick={() => setAbierto(false)}
                className="rounded-full p-1 text-cream/80 hover:bg-cream/10 hover:text-cream"
              >
                ✕
              </button>
            </div>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-3 py-3">
            {mensajes.map((m, indice) => (
              <div key={indice} className={m.rol === "usuario" ? "flex justify-end" : "flex flex-col items-start gap-2"}>
                <div
                  className={`max-w-[88%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm ${
                    m.rol === "usuario" ? "bg-primary text-cream" : "bg-section text-primary/90"
                  }`}
                >
                  {m.rol === "usuario" ? (
                    m.contenido
                  ) : (
                    <TextoConEnlaces texto={m.contenido} onNavegar={() => setAbierto(false)} />
                  )}
                </div>
                {m.productos?.length > 0 && (
                  <div className="flex w-full max-w-[95%] flex-col gap-2">
                    {m.productos.map((producto) => (
                      <TarjetaProducto
                        key={producto.id}
                        producto={producto}
                        estado={estadoAgregar[producto.id]}
                        onAgregar={agregarDesdeChat}
                      />
                    ))}
                    <Link
                      to="/carrito"
                      onClick={() => setAbierto(false)}
                      className="text-xs font-semibold text-accent underline underline-offset-2"
                    >
                      Ver mi carrito
                    </Link>
                  </div>
                )}
              </div>
            ))}

            {soloBienvenida && (
              <div className="flex flex-wrap gap-2">
                {RESPUESTAS_RAPIDAS.map((sugerencia) => (
                  <button
                    key={sugerencia}
                    type="button"
                    onClick={() => enviarTexto(sugerencia)}
                    disabled={enviando}
                    className="rounded-full border border-accent/40 bg-cream px-3 py-1.5 text-xs font-medium text-accent-dark transition hover:bg-accent/10 disabled:opacity-50 dark:text-accent-soft"
                  >
                    {sugerencia}
                  </button>
                ))}
              </div>
            )}

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
