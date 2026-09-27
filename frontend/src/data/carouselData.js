import img1 from "../assets/images/img1.jpg";
import img2 from "../assets/images/img2.jpg";
import img3 from "../assets/images/img3.jpg";
import img4 from "../assets/images/img4.jpg";
import img5 from "../assets/images/img5.jpg";
import img6 from "../assets/images/img6.jpg";
import img7 from "../assets/images/img7.jpg";
import img8 from "../assets/images/img8.jpg";
import img9 from "../assets/images/img9.jpg";
import img10 from "../assets/images/img10.jpg";

// id/titulo/precio/stock/activo de acá coinciden con el seed de
// backend/seed.py (mismo orden → mismo id 1..10, mismo precio y stock).
// Este carrusel usa datos locales/estáticos para las imágenes importadas
// con Vite, no la API: la página /tienda es la que refleja el inventario
// real. Mientras tanto, "Añadir al carrito" manda ese mismo id como
// productoId al backend, que igual valida el stock real al agregar, así
// que nunca se puede comprar de más — esto solo afecta si el botón se ve
// "Agotado" a destiempo si alguien edita el stock desde el panel admin.
const carouselData = [
  { id: 1, imagen: img1, titulo: "Torta de Chocolate Intenso", descripcion: "Bizcocho húmedo de cacao con ganache de chocolate semiamargo y cobertura brillante.", precio: 85000, stock: 12, activo: 1 },
  { id: 2, imagen: img2, titulo: "Torta de Fresas y Crema", descripcion: "Bizcocho de vainilla con crema chantilly y fresas frescas en cada capa.", precio: 78000, stock: 15, activo: 1 },
  { id: 3, imagen: img3, titulo: "Cupcakes de Vainilla x6", descripcion: "Seis cupcakes esponjosos de vainilla con buttercream cremoso y chispas de colores.", precio: 36000, stock: 30, activo: 1 },
  { id: 4, imagen: img4, titulo: "Cupcakes Red Velvet x6", descripcion: "Seis cupcakes red velvet con frosting suave de queso crema.", precio: 42000, stock: 24, activo: 1 },
  { id: 5, imagen: img5, titulo: "Galletas con Chips de Chocolate x12", descripcion: "Docena de galletas crujientes por fuera y suaves por dentro, con chips de chocolate.", precio: 32000, stock: 40, activo: 1 },
  { id: 6, imagen: img6, titulo: "Macarons Surtidos x12", descripcion: "Caja de doce macarons de almendra en sabores fresa, pistacho, limón y chocolate.", precio: 58000, stock: 18, activo: 1 },
  { id: 7, imagen: img7, titulo: "Cheesecake de Frutos Rojos", descripcion: "Cheesecake horneado sobre base de galleta, con salsa de fresa y mora.", precio: 68000, stock: 9, activo: 1 },
  { id: 8, imagen: img8, titulo: "Croissants de Mantequilla x4", descripcion: "Cuatro croissants de hojaldre laminado con mantequilla, horneados cada mañana.", precio: 24000, stock: 35, activo: 1 },
  { id: 9, imagen: img9, titulo: "Pan de Bono x10", descripcion: "Diez panes de bono calientes, con queso costeño y almidón de yuca.", precio: 18000, stock: 50, activo: 1 },
  { id: 10, imagen: img10, titulo: "Torta Tres Leches", descripcion: "Bizcocho esponjoso bañado en tres leches, con crema chantilly y canela.", precio: 72000, stock: 10, activo: 1 },
];

export default carouselData;
