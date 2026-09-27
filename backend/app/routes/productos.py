"""
Router de /api/productos.

Migración 1 a 1 de las rutas de productos: catálogo público de solo
lectura (GET) + gestión protegida (POST/PUT/PATCH/DELETE) para el
panel de administración (GestionProductos.jsx).

Convención de roles (misma que routes/usuarios.py): crear/editar el
catálogo lo pueden hacer admin y empleado; borrar un producto (acción
destructiva e irreversible) solo admin.

La lógica de datos vive en app/crud/productos.py (criterio 9): este
router no contiene ni un `db.query(...)`, `db.add(...)` ni
`db.commit(...)` para el recurso `producto` — solo valida el rol, arma
la respuesta y traduce parámetros de consulta. La única excepción es
`subir_imagen_producto`, que no toca la base de datos en absoluto (solo
el sistema de archivos), así que no aplica.
"""

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import requiere_rol
from app.crud import productos as crud
from app.database import get_db
from app.models.producto import FamiliaProducto
from app.schemas.producto import ProductoActualizar, ProductoCrear, ProductoSalida
from app.utils.paginacion import construir_meta_paginacion, obtener_parametros_paginacion

# Parámetro de ruta validado con Annotated + Path: debe ser un entero >= 1
# (id = 0 o negativo responde 422 sin tocar la base de datos).
IdProducto = Annotated[int, Path(ge=1, description="Id numérico del producto.", examples=[1])]

router = APIRouter(prefix="/api/productos", tags=["productos"])

# Mismo directorio que sirve StaticFiles en app/main.py
# (app.mount("/uploads", StaticFiles(directory="uploads"))): un archivo
# guardado aquí queda accesible en /uploads/productos/<archivo>.
DIRECTORIO_IMAGENES_PRODUCTOS = "uploads/productos"
EXTENSIONES_IMAGEN_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES_IMAGEN = 5 * 1024 * 1024  # 5 MB


@router.get(
    "",
    response_model=None,
    summary="Listar el catálogo público (paginado y filtrable)",
    responses={422: {"description": "Parámetro de consulta inválido (p. ej. page=0)."}},
)
def listar_productos(
    page: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    pagina: int | None = Query(default=None, ge=1),
    limite: int | None = Query(default=None, ge=1),
    familia: FamiliaProducto | None = None,
    buscar: str | None = Query(default=None, max_length=60),
    db: Session = Depends(get_db),
):
    """
    Catálogo público de productos (vitrina de la tienda), paginado.
    Ruta PÚBLICA — solo muestra productos `activo=True`; para ver
    también los inactivos usa GET /api/productos/admin/todos (rol
    admin/empleado). Acepta ?familia= para filtrar por categoría
    (tortas, cupcakes, galletas...) y ?buscar= para una búsqueda simple por título.
    """
    pagina_final, limite_final, offset = obtener_parametros_paginacion(page, limit, pagina, limite)

    productos, total = crud.listar(
        db, offset=offset, limite=limite_final, solo_activos=True, familia=familia, buscar=buscar
    )

    return {
        "datos": [ProductoSalida.model_validate(p) for p in productos],
        "paginacion": construir_meta_paginacion(pagina_final, limite_final, total),
    }


@router.get(
    "/admin/todos",
    response_model=None,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def listar_productos_admin(
    page: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    pagina: int | None = Query(default=None, ge=1),
    limite: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """
    Listado completo (activos e inactivos) para GestionProductos.jsx.
    Ruta PROTEGIDA para admin y empleado.
    """
    pagina_final, limite_final, offset = obtener_parametros_paginacion(page, limit, pagina, limite)

    productos, total = crud.listar(db, offset=offset, limite=limite_final, solo_activos=False)

    return {
        "datos": [ProductoSalida.model_validate(p) for p in productos],
        "paginacion": construir_meta_paginacion(pagina_final, limite_final, total),
    }


@router.get(
    "/{producto_id}",
    response_model=ProductoSalida,
    summary="Consultar un producto por id",
    responses={404: {"description": "El producto no existe."}},
)
def obtener_producto(producto_id: IdProducto, db: Session = Depends(get_db)):
    """Detalle de un producto por id. Ruta PÚBLICA (necesaria para la página de detalle y para el formulario de edición)."""
    return crud.obtener_por_id(db, producto_id)


@router.post(
    "/imagen",
    response_model=None,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
async def subir_imagen_producto(imagen: UploadFile = File(...)):
    """
    Sube el archivo de imagen de un producto a `uploads/productos/` y
    devuelve el nombre generado, listo para guardar como el campo
    `imagen` de POST/PUT /api/productos (que esperan solo el nombre de
    archivo, no una URL completa — ver validar_imagen en
    schemas/producto.py). Ruta PROTEGIDA para admin y empleado. Esta
    ruta faltaba por completo: GestionProductos.jsx no tenía dónde
    subir el archivo antes de crear o editar un producto.

    El nombre original del archivo NUNCA se reutiliza tal cual (evita
    colisiones entre dos archivos con el mismo nombre y cualquier
    intento de path traversal vía el nombre): se genera uno aleatorio,
    conservando solo la extensión, validada contra la misma lista de
    formatos que acepta validar_imagen().
    """
    extension = os.path.splitext(imagen.filename or "")[1].lower()
    if extension not in EXTENSIONES_IMAGEN_PERMITIDAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen debe ser .jpg, .jpeg, .png o .webp.",
        )

    contenido = await imagen.read()
    if len(contenido) > MAX_BYTES_IMAGEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen no puede pesar más de 5 MB.",
        )

    os.makedirs(DIRECTORIO_IMAGENES_PRODUCTOS, exist_ok=True)
    nombre_archivo = f"{uuid.uuid4().hex}{extension}"
    with open(os.path.join(DIRECTORIO_IMAGENES_PRODUCTOS, nombre_archivo), "wb") as destino:
        destino.write(contenido)

    # La ruta devuelta debe empezar con "/uploads/" porque
    # resolverUrlImagen() en frontend/src/utils/formato.js solo antepone
    # el origen del backend (ORIGEN_API) cuando la ruta empieza así; de
    # lo contrario la deja tal cual y el navegador la busca (mal) en el
    # propio origen del frontend, mostrando la imagen rota en todas
    # partes (vista previa del panel, Tienda.jsx, tarjetas de producto).
    return {"ruta_imagen": f"/uploads/productos/{nombre_archivo}"}


@router.post(
    "",
    response_model=ProductoSalida,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
    summary="Crear un producto",
    responses={
        401: {"description": "Sin token."},
        403: {"description": "El rol no es admin ni empleado."},
        409: {"description": "Ya existe un producto con ese SKU."},
        422: {"description": "Datos inválidos (título, precio, familia, imagen...)."},
    },
)
def crear_producto(datos: ProductoCrear, db: Session = Depends(get_db)):
    """Crea un producto nuevo. Ruta PROTEGIDA para admin y empleado."""
    return crud.crear(db, datos.model_dump())


@router.put(
    "/{producto_id}",
    response_model=ProductoSalida,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
    summary="Actualizar un producto (reemplazo completo)",
    responses={404: {"description": "El producto no existe."}, 409: {"description": "SKU duplicado."}, 422: {"description": "Datos inválidos."}},
)
def actualizar_producto(producto_id: IdProducto, datos: ProductoActualizar, db: Session = Depends(get_db)):
    """
    Reemplaza todos los campos editables de un producto (el formulario
    de GestionProductos.jsx siempre reenvía el registro completo, no
    un parche). Ruta PROTEGIDA para admin y empleado.
    """
    producto = crud.obtener_por_id(db, producto_id)
    return crud.reemplazar(db, producto, datos.model_dump())


@router.patch(
    "/{producto_id}/estado",
    response_model=None,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def cambiar_estado_producto(producto_id: IdProducto, activo: bool, db: Session = Depends(get_db)):
    """
    Publica o despublica un producto sin borrarlo (equivalente al
    "activo" de usuarios). Ruta PROTEGIDA para admin y empleado.
    """
    producto = crud.obtener_por_id(db, producto_id)
    crud.cambiar_estado(db, producto, activo)

    return {
        "mensaje": "Producto publicado correctamente." if activo else "Producto despublicado correctamente.",
        "activo": activo,
    }


@router.delete(
    "/{producto_id}",
    response_model=None,
    dependencies=[Depends(requiere_rol("admin"))],
    summary="Eliminar un producto (solo admin)",
    responses={404: {"description": "El producto no existe."}, 409: {"description": "Ya fue comprado; despublícalo en vez de borrarlo."}},
)
def eliminar_producto(producto_id: IdProducto, db: Session = Depends(get_db)):
    """
    Elimina un producto. Ruta PROTEGIDA solo para admin. Si el
    producto ya fue comprado (FK en `pedido_items.producto_id`, sin
    ON DELETE CASCADE — el historial de compras no debe romperse),
    se responde 409 en vez de dejar que la base de datos rechace el
    DELETE con un error crudo. Sugerencia en el mensaje: despublicarlo
    (PATCH /estado) en vez de borrarlo.
    """
    producto = crud.obtener_por_id(db, producto_id)
    crud.eliminar(db, producto)
    return {"mensaje": "Producto eliminado correctamente."}
