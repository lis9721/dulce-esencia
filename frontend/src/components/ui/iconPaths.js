/** Paths de los iconos SVG reutilizados en la interfaz (ver ui/Icon.jsx). */
const ICON_PATHS = {
  menu: "M3.75 6.75h16.5M3.75 12h16.5M3.75 17.25h16.5",
  close: "M6 18 18 6M6 6l12 12",
  chevronLeft: "M15.75 19.5 8.25 12l7.5-7.5",
  chevronRight: "m8.25 4.5 7.5 7.5-7.5 7.5",
  chevronDown: "m19.5 8.25-7.5 7.5-7.5-7.5",
  check: "M4.5 12.75l6 6 9-13.5",
  sparkle: "M12 2.5 13.6 8.4 19.5 10 13.6 11.6 12 17.5 10.4 11.6 4.5 10 10.4 8.4 12 2.5Z",
  truck: "M3 7h11v8H3V7Zm11 3h4l3 3v2h-7v-5ZM6 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm12 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
  shieldCheck: "M12 3 5 6v5c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6l-7-3Z M9.5 12.5 11 14l3.5-3.5",
  cart: "M2.25 3h1.5l1.5 12.75A2.25 2.25 0 0 0 7.5 18h9.75a2.25 2.25 0 0 0 2.25-1.98l1.1-8.02H5.53 M8.25 21a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm9 0a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z",
  plus: "M12 4.5v15m7.5-7.5h-15",
  minus: "M4.5 12h15",
  trash: "M4.5 6.75h15M9.75 6.75V4.5h4.5v2.25M6 6.75l.75 12.75A1.5 1.5 0 0 0 8.25 21h7.5a1.5 1.5 0 0 0 1.5-1.5L18 6.75",
  download: "M12 3v12.75m0 0-4.5-4.5m4.5 4.5 4.5-4.5M4.5 18.75h15",
  search: "M10.5 18a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15ZM21 21l-5.197-5.197",
  sun: "M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-6.364-2.386 1.591-1.591M3 12h2.25m.386-6.364 1.591 1.591M16.5 12a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0Z",
  moon: "M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z",
  // Redes sociales del footer (components/Footer.jsx). Trazos simples,
  // consistentes con el resto de íconos (mismo viewBox/strokeWidth de
  // Icon.jsx), no logos oficiales pixel-perfect.
  instagram:
    "M7 2h10a5 5 0 0 1 5 5v10a5 5 0 0 1-5 5H7a5 5 0 0 1-5-5V7a5 5 0 0 1 5-5Z M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z M17.5 6.5 17.51 6.5",
  facebook: "M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z",
  // No hay un glifo de trazo estándar para el logo de TikTok; se usa una
  // nota musical (asociada a su contenido con sonido) como equivalente
  // genérico, en el mismo estilo del resto del set de íconos.
  tiktok: "M9 18V5l12-2v13 M3 18a3 3 0 1 0 6 0 3 3 0 0 0-6 0Z M15 16a3 3 0 1 0 6 0 3 3 0 0 0-6 0Z",
};

export default ICON_PATHS;
