/**
 * Catálogo de categorías de un producto real (columna `productos.familia`
 * en la BD, ver backend/database/schema_fastapi.sql y
 * backend/app/models/producto.py → FamiliaProducto).
 *
 * Usa los mismos `id` que `data/coleccionesData.js` (la sección
 * "Nuestra vitrina" del home) a propósito: esa sección es contenido
 * editorial sin conexión a productos reales, pero comparte el mismo
 * vocabulario de categorías para que el filtro de /tienda no introduzca
 * una segunda taxonomía con nombres distintos.
 *
 * Se usa tanto en el formulario de admin (GestionProductos.jsx, como
 * <Select>) como en el filtro de /tienda (Tienda.jsx).
 */
const FAMILIAS_PRODUCTO = [
  { value: "tortas", label: "Tortas" },
  { value: "cupcakes", label: "Cupcakes" },
  { value: "galletas", label: "Galletas" },
  { value: "postres", label: "Postres" },
  { value: "hojaldres", label: "Hojaldres" },
  { value: "panaderia", label: "Panadería" },
];

export default FAMILIAS_PRODUCTO;
