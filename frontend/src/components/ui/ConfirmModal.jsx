import { useState } from "react";
import Modal from "./Modal";
import Button from "./Button";

/**
 * ConfirmModal
 * Reemplaza window.confirm() para acciones destructivas (eliminar
 * producto/usuario). A diferencia del diálogo nativo del navegador:
 * - Reutiliza el propio Modal.jsx del proyecto (mismo look & feel,
 *   mismo manejo de Escape/click-afuera) en vez de un diálogo que no
 *   se puede estilizar ni theme-ar.
 * - No bloquea el hilo principal (window.confirm sí lo hace).
 * - Muestra el error del servidor dentro del propio modal si la
 *   confirmación falla, en vez de un alert() nativo aparte.
 *
 * Uso:
 *   <ConfirmModal
 *     isOpen={...} onClose={...} title="Eliminar producto"
 *     message={`¿Eliminar "${producto.titulo}"? Esta acción no se puede deshacer.`}
 *     onConfirm={async () => eliminarProducto(producto.id)}
 *   />
 */
function ConfirmModal({
  isOpen,
  onClose,
  title = "Confirmar acción",
  message,
  confirmLabel = "Eliminar",
  cancelLabel = "Cancelar",
  onConfirm,
}) {
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");

  const handleConfirmar = async () => {
    setError("");
    setEnviando(true);
    try {
      await onConfirm();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  };

  const handleClose = () => {
    if (enviando) return;
    setError("");
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={title}>
      <p className="text-sm text-primary/80">{message}</p>

      {error && (
        <p className="mt-3 rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{error}</p>
      )}

      <div className="mt-6 flex justify-end gap-3">
        <Button variant="ghost" onClick={handleClose} disabled={enviando}>
          {cancelLabel}
        </Button>
        <Button variant="danger" onClick={handleConfirmar} disabled={enviando}>
          {enviando ? "Eliminando..." : confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}

export default ConfirmModal;
