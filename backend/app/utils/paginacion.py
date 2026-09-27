"""
Helper compartido para paginar listados (GET /api/usuarios, y
cualquier otro que se agregue después — GET /api/productos, etc.).

Réplica en Python de backend-node/utils/paginacion.js (fuente de
verdad): sanea "page"/"limit" (o "pagina"/"limite") de los query
params, aplica un límite máximo para que nadie pueda pedir
`limit=999999` y forzar traer la tabla completa, y arma el objeto de
metadatos de paginación que acompaña a "datos" en la respuesta.
"""

LIMITE_POR_DEFECTO = 10
LIMITE_MAXIMO = 50


def _a_entero_positivo(valor) -> int | None:
    """Convierte un valor de query string a entero positivo, o None si no es válido (>= 1)."""
    if valor is None:
        return None
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return None
    return numero if numero >= 1 else None


def obtener_parametros_paginacion(
    page: int | None = None,
    limit: int | None = None,
    pagina: int | None = None,
    limite: int | None = None,
) -> tuple[int, int, int]:
    """
    Acepta tanto los nombres en inglés (page/limit) como en español
    (pagina/limite), igual que obtenerParametrosPaginacion() en Node.
    Retorna (pagina, limite, offset).
    """
    pagina_solicitada = _a_entero_positivo(page) or _a_entero_positivo(pagina)
    limite_solicitado = _a_entero_positivo(limit) or _a_entero_positivo(limite)

    pagina_final = pagina_solicitada or 1
    limite_final = min(limite_solicitado or LIMITE_POR_DEFECTO, LIMITE_MAXIMO)
    offset = (pagina_final - 1) * limite_final

    return pagina_final, limite_final, offset


def construir_meta_paginacion(pagina: int, limite: int, total: int) -> dict:
    """Réplica de construirMetaPaginacion() en Node."""
    return {
        "pagina": pagina,
        "limite": limite,
        "total": total,
        "totalPaginas": 0 if total == 0 else -(-total // limite),  # ceil sin importar math
    }
