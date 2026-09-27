import Button from "./Button";

/**
 * Paginacion
 * Controles simples de "Anterior / Siguiente" + info de página actual,
 * para usar junto a listados paginados por el backend (ver
 * GestionUsuarios.jsx y GestionProductos.jsx, que consumen
 * GET /api/usuarios y GET /api/productos con ?page=&limit=).
 *
 * No se muestra si solo hay una página (o ninguna), para no ensuciar
 * la vista con controles que no sirven de nada.
 */
function Paginacion({ pagina, totalPaginas, total, onCambiarPagina, deshabilitado = false }) {
  if (!totalPaginas || totalPaginas <= 1) return null;

  const esPrimera = pagina <= 1;
  const esUltima = pagina >= totalPaginas;

  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-beige/60 pt-4 text-sm">
      <p className="text-primary/70">
        Página {pagina} de {totalPaginas}
        {typeof total === "number" && ` · ${total} en total`}
      </p>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          onClick={() => onCambiarPagina(pagina - 1)}
          disabled={esPrimera || deshabilitado}
        >
          ← Anterior
        </Button>
        <Button
          variant="secondary"
          onClick={() => onCambiarPagina(pagina + 1)}
          disabled={esUltima || deshabilitado}
        >
          Siguiente →
        </Button>
      </div>
    </div>
  );
}

export default Paginacion;
