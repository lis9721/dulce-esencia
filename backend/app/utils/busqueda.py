"""
utils/busqueda.py

Ayudas para búsquedas con LIKE/ILIKE.

`ilike(f"%{texto}%")` ya va como parámetro ligado (no hay inyección
SQL), pero `%` y `_` que escriba el usuario SÍ funcionan como comodines
de LIKE: buscar "%" devolvería todo el catálogo. Estas funciones los
escapan para que se busquen como caracteres normales.
"""

CARACTER_ESCAPE = "\\"


def escapar_like(texto: str) -> str:
    return (
        texto.replace(CARACTER_ESCAPE, CARACTER_ESCAPE * 2)
        .replace("%", CARACTER_ESCAPE + "%")
        .replace("_", CARACTER_ESCAPE + "_")
    )


def patron_contiene(texto: str) -> str:
    """Patrón `%texto%` con los comodines del usuario ya escapados."""
    return f"%{escapar_like(texto.strip())}%"
