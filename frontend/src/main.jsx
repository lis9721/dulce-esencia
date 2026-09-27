import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import { CartProvider } from './context/CartContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      {/* CartProvider va DENTRO de AuthProvider: necesita saber si hay
          sesión iniciada (useAuth) para decidir si el carrito vive en
          el backend o en localStorage, y para disparar la fusión al
          iniciar sesión (ver context/CartContext.jsx). */}
      <CartProvider>
        <App />
      </CartProvider>
    </AuthProvider>
  </StrictMode>,
)
