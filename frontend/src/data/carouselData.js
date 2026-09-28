import { resolverUrlImagen } from "../utils/formato";

// Fotos REALES de la tienda: viven en el backend (backend/uploads/productos,
// servidas en /uploads/...). OJO: los archivos con nombre de producto
// (torta-fresas-crema.jpg, etc.) son las ilustraciones del seed; las fotos
// son los archivos con nombre hash que se subieron desde el panel.
// Estas son solo el valor de respaldo: Index.jsx las reemplaza con el campo
// `imagen` que devuelve la API (GET /productos), la misma fuente de /tienda.
const foto = (archivo) => resolverUrlImagen(`/uploads/productos/${archivo}.jpg`);

// id/titulo/precio/stock/activo de acá coinciden con el seed de
// backend/seed.py (mismo orden → mismo id 1..10, mismo precio y stock).
// Este carrusel usa datos locales/estáticos (con las fotos del backend), no la API: la página /tienda es la que refleja el inventario
// real. Mientras tanto, "Añadir al carrito" manda ese mismo id como
// productoId al backend, que igual valida el stock real al agregar, así
// que nunca se puede comprar de más — esto solo afecta si el botón se ve
// "Agotado" a destiempo si alguien edita el stock desde el panel admin.
const carouselData = [
  { id: 1, imagen: foto("8ea7d75e227e4fa1ba026afb679ba40e"), titulo: "Torta de Chocolate Intenso", descripcion: "Bizcocho húmedo de cacao con ganache de chocolate semiamargo y cobertura brillante.", precio: 85000, stock: 12, activo: 1 },
  { id: 2, imagen: foto("e183cb186c224d0b9baab1f5965352cd"), titulo: "Torta de Fresas y Crema", descripcion: "Bizcocho de vainilla con crema chantilly y fresas frescas en cada capa.", precio: 78000, stock: 15, activo: 1 },
  { id: 3, imagen: foto("b1ce99c5b1bf4fbfba081eb5e8e6c37a"), titulo: "Cupcakes de Vainilla x6", descripcion: "Seis cupcakes esponjosos de vainilla con buttercream cremoso y chispas de colores.", precio: 36000, stock: 30, activo: 1 },
  { id: 4, imagen: foto("4efaf51499a74b28b74867fee2eae667"), titulo: "Cupcakes Red Velvet x6", descripcion: "Seis cupcakes red velvet con frosting suave de queso crema.", precio: 42000, stock: 24, activo: 1 },
  { id: 5, imagen: foto("7b4d2e12d62c4b68bc04fcc1806be19a"), titulo: "Galletas con Chips de Chocolate x12", descripcion: "Docena de galletas crujientes por fuera y suaves por dentro, con chips de chocolate.", precio: 32000, stock: 40, activo: 1 },
  { id: 6, imagen: foto("1f0e732f48dd4f05b1117b92f0543718"), titulo: "Macarons Surtidos x12", descripcion: "Caja de doce macarons de almendra en sabores fresa, pistacho, limón y chocolate.", precio: 58000, stock: 18, activo: 1 },
  { id: 7, imagen: foto("45c619778c59494c912663da18a45a55"), titulo: "Cheesecake de Frutos Rojos", descripcion: "Cheesecake horneado sobre base de galleta, con salsa de fresa y mora.", precio: 68000, stock: 9, activo: 1 },
  { id: 8, imagen: foto("1e3b4e3325204722a257b1e4b2fc8ab2"), titulo: "Croissants de Mantequilla x4", descripcion: "Cuatro croissants de hojaldre laminado con mantequilla, horneados cada mañana.", precio: 24000, stock: 35, activo: 1 },
  { id: 9, imagen: foto("cfd268f556d74c568838e0b3ecfb2bcb"), titulo: "Pan de Bono x10", descripcion: "Diez panes de bono calientes, con queso costeño y almidón de yuca.", precio: 18000, stock: 50, activo: 1 },
  { id: 10, imagen: foto("8c8e382456ac4a7290ea5ed458b797d8"), titulo: "Torta Tres Leches", descripcion: "Bizcocho esponjoso bañado en tres leches, con crema chantilly y canela.", precio: 72000, stock: 10, activo: 1 },
];

export default carouselData;
