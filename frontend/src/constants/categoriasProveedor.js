/**
 * Categorías del módulo de proveedores (columna `proveedores.categoria`
 * en la BD, ver backend/database/schema_fastapi.sql y
 * backend/app/models/proveedor.py).
 *
 * Se usa tanto en el formulario de GestionProveedores.jsx (como
 * <Select>) como en el filtro por categoría del mismo panel.
 */
const CATEGORIAS_PROVEEDOR = [
  { value: "materias_primas", label: "Materias primas" },
  { value: "lacteos", label: "Lácteos y huevos" },
  { value: "empaques", label: "Empaques" },
  { value: "insumos", label: "Insumos" },
  { value: "logistica", label: "Logística" },
];

export default CATEGORIAS_PROVEEDOR;
