"""
Capa CRUD: todo el acceso a la base de datos de cada recurso, aislado de
HTTP (criterios 6 y 9 de la lista de chequeo).

Convive con `app/repositories/` —la misma capa con otro nombre, usada
por los módulos de pagos y usuarios— y es la carpeta canónica para los
recursos nuevos. Ninguna función de aquí lanza `HTTPException`: solo
excepciones de `app/exceptions/dominio.py` (criterio 29).
"""

from app.crud import proveedores

__all__ = ["proveedores"]
