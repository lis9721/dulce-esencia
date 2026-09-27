import { Component } from "react";
import Button from "./ui/Button";

/**
 * ErrorBoundary
 * Los Error Boundary de React solo pueden implementarse como componentes
 * de clase (no existe un hook equivalente): React exige exactamente los
 * métodos de ciclo de vida `getDerivedStateFromError` / `componentDidCatch`
 * usados aquí para poder "atrapar" el error.
 *
 * Sin esto, cualquier error de render en un componente hijo (por ejemplo,
 * Panel.jsx asumiendo que `usuario` nunca es null) tumba toda la
 * aplicación y deja al usuario con una pantalla en blanco, sin ningún
 * mensaje ni forma de recuperarse salvo recargar manualmente la página.
 *
 * Envuelve <Routes> en App.jsx: un error dentro de cualquier página cae
 * aquí en vez de romper el layout completo (Header/Footer siguen visibles).
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { tieneError: false };
  }

  static getDerivedStateFromError() {
    return { tieneError: true };
  }

  componentDidCatch(error, infoError) {
    // En un proyecto con monitoreo real (Sentry, etc.) aquí se reportaría
    // el error. Por ahora lo dejamos en consola para no perder la traza
    // durante el desarrollo/sustentación.
    console.error("Error capturado por ErrorBoundary:", error, infoError);
  }

  handleReintentar = () => {
    this.setState({ tieneError: false });
  };

  render() {
    if (this.state.tieneError) {
      return (
        <main className="flex flex-1 items-center justify-center bg-section px-4 py-16">
          <div className="w-full max-w-md rounded-2xl border border-beige/60 bg-cream p-8 text-center">
            <h1 className="text-lg font-semibold text-primary">
              Ocurrió un error inesperado
            </h1>
            <p className="mt-2 text-sm text-primary/70">
              Algo falló al mostrar esta página. Puedes intentar de nuevo o
              volver al inicio.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <Button onClick={this.handleReintentar} variant="secondary">
                Reintentar
              </Button>
              <Button onClick={() => window.location.assign("/")}>
                Volver al inicio
              </Button>
            </div>
          </div>
        </main>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
