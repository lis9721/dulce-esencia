/**
 * Enlaces principales de navegación, usados tanto por Header.jsx como por
 * Footer.jsx. Antes vivían duplicados en cada componente; al tener una
 * sola fuente de verdad, agregar/renombrar una sección del sitio no
 * requiere recordar actualizar dos listas por separado.
 */
const ENLACES = [
  { to: "/", label: "Inicio", end: true },
  { to: "/tienda", label: "Tienda" },
  { to: "/quienes-somos", label: "Quiénes Somos" },
  { to: "/contacto", label: "Contacto" },
];

export default ENLACES;
