import { useEffect } from "react";

const NOMBRE_SITIO = "Dulce Esencia Pastelería";

// TODO: cuando el dominio real esté activo, reemplazar esta constante
// (se usa para construir URLs absolutas en canonical/Open Graph/Twitter Card).
const URL_BASE = "https://dulceesencia.com";

function setMetaPorAtributo(atributo, clave, contenido) {
  if (!contenido) return;
  let elemento = document.querySelector(`meta[${atributo}="${clave}"]`);
  if (!elemento) {
    elemento = document.createElement("meta");
    elemento.setAttribute(atributo, clave);
    document.head.appendChild(elemento);
  }
  elemento.setAttribute("content", contenido);
}

function setCanonical(ruta) {
  let enlace = document.querySelector('link[rel="canonical"]');
  if (!enlace) {
    enlace = document.createElement("link");
    enlace.setAttribute("rel", "canonical");
    document.head.appendChild(enlace);
  }
  enlace.setAttribute("href", `${URL_BASE}${ruta}`);
}

/**
 * Actualiza <title>, meta description, Open Graph, Twitter Card y el
 * <link rel="canonical"> de la página activa.
 *
 * Como este proyecto es una SPA de React puro (sin SSR/prerender), el
 * index.html solo puede tener UN título y UNA descripción fijos. Este
 * hook los sobreescribe en cada página al montarse, para que cada ruta
 * pública (/, /quienes-somos, /contacto...) tenga su propio título y
 * descripción — lo que ven tanto la pestaña del navegador como (para
 * crawlers que ejecutan JS, como Google) los resultados de búsqueda.
 *
 * @param {string} titulo - Título específico de la página (sin el nombre del sitio).
 * @param {string} descripcion - Meta description específica de la página.
 * @param {string} ruta - Ruta de la página (ej. "/contacto"), para canonical y og:url.
 * @param {boolean} noIndexar - true para páginas privadas/transaccionales que no deben indexarse.
 */
function useDocumentTitle(titulo, descripcion, ruta = "/", noIndexar = false) {
  useEffect(() => {
    const tituloCompleto = titulo ? `${titulo} | ${NOMBRE_SITIO}` : NOMBRE_SITIO;
    document.title = tituloCompleto;

    setMetaPorAtributo("name", "description", descripcion);
    setMetaPorAtributo("property", "og:title", tituloCompleto);
    setMetaPorAtributo("property", "og:description", descripcion);
    setMetaPorAtributo("property", "og:url", `${URL_BASE}${ruta}`);
    setMetaPorAtributo("name", "twitter:title", tituloCompleto);
    setMetaPorAtributo("name", "twitter:description", descripcion);
    setCanonical(ruta);

    // Páginas privadas (panel) o puramente transaccionales (restablecer
    // contraseña, verificar correo) no deben aparecer en buscadores.
    setMetaPorAtributo("name", "robots", noIndexar ? "noindex, nofollow" : "index, follow");
  }, [titulo, descripcion, ruta, noIndexar]);
}

export default useDocumentTitle;
