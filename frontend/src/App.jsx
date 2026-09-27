import { BrowserRouter, Routes, Route } from "react-router-dom";
import Header from "./components/Header";
import Footer from "./components/Footer";
import ErrorBoundary from "./components/ErrorBoundary";
import ProtectedRoute from "./components/ProtectedRoute";
import WhatsAppButton from "./components/WhatsAppButton";
import Chatbot from "./components/Chatbot";
import Index from "./pages/Index";
import Tienda from "./pages/Tienda";
import QuienesSomos from "./pages/QuienesSomos";
import Contacto from "./pages/Contacto";
import Login from "./pages/Login";
import ResetPassword from "./pages/ResetPassword";
import VerificarCorreo from "./pages/VerificarCorreo";
import Carrito from "./pages/Carrito";
import Checkout from "./pages/Checkout";
import PagoResultado from "./pages/PagoResultado";
import PedidoDetalle from "./pages/PedidoDetalle";
import Panel from "./pages/Panel";
import MiPerfil from "./pages/panel/MiPerfil";
import GestionProductos from "./pages/panel/GestionProductos";
import GestionServicios from "./pages/panel/GestionServicios";
import GestionProveedores from "./pages/panel/GestionProveedores";
import GestionUsuarios from "./pages/panel/GestionUsuarios";
import MisPedidos from "./pages/panel/MisPedidos";
import GestionPedidos from "./pages/panel/GestionPedidos";
import GestionCupones from "./pages/panel/GestionCupones";
import Dashboard from "./pages/panel/Dashboard";
import GestionVentas from "./pages/panel/GestionVentas";
import Facturas from "./pages/panel/Facturas";
import GestionPQR from "./pages/panel/GestionPQR";
import { ROLES_PANEL } from "./constants/rolesPanel";

function App() {
  return (
    <BrowserRouter>
      <a href="#contenido-principal" className="saltar-al-contenido">
        Saltar al contenido
      </a>
      <Header />
      <ErrorBoundary>
        <main id="contenido-principal">
        <Routes>
          <Route path="/" element={<Index />} />
          {/* Pública, sin ProtectedRoute: cualquiera (invitado, cliente,
              admin o empleado) puede entrar a ver y comprar el catálogo
              real. El propio backend (verificarTokenOpcional en
              GET /api/productos) ya filtra los productos inactivos para
              quien no sea admin/empleado, así que no hace falta lógica
              de roles adicional a nivel de router — a diferencia de
              /panel/productos, que sí exige rol para gestionar
              (crear/editar/eliminar). */}
          <Route path="/tienda" element={<Tienda />} />
          <Route path="/quienes-somos" element={<QuienesSomos />} />
          <Route path="/contacto" element={<Contacto />} />
          <Route path="/login" element={<Login />} />
          <Route path="/restablecer-password" element={<ResetPassword />} />
          <Route path="/verificar-correo" element={<VerificarCorreo />} />
          {/* Pública, con o sin sesión: un invitado también puede
              revisar su carrito (localStorage) sin loguearse — ver
              CartContext.jsx. */}
          <Route path="/carrito" element={<Carrito />} />
          {/* Checkout y detalle de pedido SÍ exigen sesión (a diferencia
              del carrito): ProtectedRoute ya se encarga de mandar a
              /login y traer de vuelta a esta misma ruta al autenticarse
              (ver el "desde" que lee Login.jsx), así que Carrito.jsx no
              necesita reimplementar ese redirect a mano. */}
          <Route
            path="/checkout"
            element={
              <ProtectedRoute>
                <Checkout />
              </ProtectedRoute>
            }
          />
          <Route
            path="/pago/resultado"
            element={
              <ProtectedRoute>
                <PagoResultado />
              </ProtectedRoute>
            }
          />
          <Route
            path="/pedidos/:id"
            element={
              <ProtectedRoute>
                <PedidoDetalle />
              </ProtectedRoute>
            }
          />
          {/* Ruta protegida: exige sesión iniciada. Panel.jsx es el layout
              (encabezado + pestañas) y renderiza la sub-sección activa
              mediante <Outlet />. Cada sub-sección declara aquí mismo,
              a nivel de router, qué roles pueden entrar — no solo qué
              pestañas se muestran en la UI (ver ROLES_PANEL en
              constants/rolesPanel.js, usado también por Panel.jsx). */}
          <Route
            path="/panel"
            element={
              <ProtectedRoute>
                <Panel />
              </ProtectedRoute>
            }
          >
            <Route index element={<MiPerfil />} />
            {/* Mis pedidos NO tiene rolesPermitidos: cualquier usuario
                autenticado (cliente, empleado o admin) tiene sus propios
                pedidos que revisar. La autorización de "solo los míos"
                la hace el backend (GET /api/pedidos), no esta ruta. */}
            <Route path="mis-pedidos" element={<MisPedidos />} />
            {/* Facturas y PQR (Quinto Avance): sin rolesPermitidos, igual
                que "mis-pedidos" — cualquier usuario autenticado tiene
                sus propias facturas/PQR que consultar. El backend filtra
                "solo lo mío" para un cliente (ver GET /api/facturas,
                GET /api/pqr). */}
            <Route path="facturas" element={<Facturas />} />
            <Route path="pqr" element={<GestionPQR />} />
            <Route
              path="dashboard"
              element={
                <ProtectedRoute rolesPermitidos={ROLES_PANEL.dashboard}>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="ventas"
              element={
                <ProtectedRoute rolesPermitidos={ROLES_PANEL.ventas}>
                  <GestionVentas />
                </ProtectedRoute>
              }
            />
            <Route
              path="productos"
              element={
                <ProtectedRoute rolesPermitidos={ROLES_PANEL.productos}>
                  <GestionProductos />
                </ProtectedRoute>
              }
            />
            <Route
              path="servicios"
              element={
                <ProtectedRoute rolesPermitidos={ROLES_PANEL.servicios}>
                  <GestionServicios />
                </ProtectedRoute>
              }
            />
            <Route
              path="proveedores"
              element={
                <ProtectedRoute rolesPermitidos={ROLES_PANEL.proveedores}>
                  <GestionProveedores />
                </ProtectedRoute>
              }
            />
            <Route
              path="usuarios"
              element={
                <ProtectedRoute rolesPermitidos={ROLES_PANEL.usuarios}>
                  <GestionUsuarios />
                </ProtectedRoute>
              }
            />
            <Route
              path="pedidos"
              element={
                <ProtectedRoute rolesPermitidos={ROLES_PANEL.pedidos}>
                  <GestionPedidos />
                </ProtectedRoute>
              }
            />
            <Route
              path="cupones"
              element={
                <ProtectedRoute rolesPermitidos={ROLES_PANEL.cupones}>
                  <GestionCupones />
                </ProtectedRoute>
              }
            />
          </Route>
        </Routes>
        </main>
      </ErrorBoundary>
      <Footer />
      <WhatsAppButton />
      <Chatbot />
    </BrowserRouter>
  );
}

export default App;
