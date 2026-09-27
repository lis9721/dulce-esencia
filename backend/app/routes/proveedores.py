"""
Router de `/api/proveedores` — módulo de proveedores de Dulce Esencia.

Diseño previo al código (criterio 3): la tabla completa
recurso–verbo–ruta–código vive en `docs/DISENO-API-PROVEEDORES.md`. Este
es su resumen:

| Verbo  | Ruta                                | Éxito | Errores               |
|--------|-------------------------------------|-------|-----------------------|
| GET    | /api/proveedores                    | 200   | 401, 403, 422         |
| GET    | /api/proveedores/{id}               | 200   | 401, 403, 404, 422    |
| POST   | /api/proveedores                    | 201   | 401, 403, 409, 422    |
| PUT    | /api/proveedores/{id}               | 200   | 401, 403, 404, 409, 422 |
| PATCH  | /api/proveedores/{id}               | 200   | 401, 403, 404, 409, 422 |
| DELETE | /api/proveedores/{id}               | 204   | 401, 403, 404, 409    |
| POST   | /api/proveedores/{id}/suspensiones  | 201   | 401, 403, 404, 409, 422 |
| POST   | /api/proveedores/{id}/reactivaciones| 201   | 401, 403, 404, 409    |

Notas de diseño
---------------
* Las rutas nombran RECURSOS en plural y no llevan verbos (criterio 1):
  nada de `/api/proveedores/crear` ni `/api/proveedores/{id}/suspender`.
* Suspender y reactivar son operaciones de negocio modeladas como
  SUB-RECURSOS que se crean (`POST .../suspensiones`), no un PATCH
  genérico sobre un campo `estado` (criterio 4). Así la suspensión tiene
  su propio cuerpo (el motivo), su propio código de respuesta y su
  propia regla de conflicto.
* Todo el router exige sesión y rol: `dependencies=[...]` a nivel de
  APIRouter (criterio 37), porque la regla aplica al recurso completo.
  La única diferencia por endpoint es DELETE, restringido a admin.
* Ninguna función de este archivo toca la base de datos directamente:
  todo pasa por `app/crud/proveedores.py` (criterio 9).
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, requiere_rol
from app.core.dependencias import Paginacion, ProveedorDeLaRuta
from app.crud import proveedores as crud
from app.database import get_db
from app.models.proveedor import CategoriaProveedor, EstadoProveedor
from app.schemas.proveedor import (
    ProveedorActualizar,
    ProveedorCrear,
    ProveedorReemplazar,
    ProveedorSalida,
    ProveedoresPagina,
    SuspensionCrear,
)
from app.services.proveedores import notificar_alta_de_proveedor

# Respuestas de error comunes a todo el recurso, declaradas para que
# aparezcan en /docs (criterio 26).
ERRORES_AUTENTICACION = {
    401: {"description": "Falta el token o está vencido."},
    403: {"description": "El rol autenticado no puede gestionar proveedores."},
}
ERROR_NO_ENCONTRADO = {404: {"description": "No existe un proveedor con ese id."}}

router = APIRouter(
    prefix="/api/proveedores",
    tags=["proveedores"],
    # Criterio 37: la regla «solo personal interno gestiona proveedores»
    # aplica a TODOS los endpoints, así que se declara una vez aquí en
    # vez de repetirse endpoint por endpoint.
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
    responses=ERRORES_AUTENTICACION,
)

SesionBD = Annotated[Session, Depends(get_db)]


@router.get(
    "",
    response_model=ProveedoresPagina,
    summary="Listar proveedores (paginado y filtrable)",
    responses={422: {"description": "Parámetro de consulta inválido (p. ej. page=0)."}},
)
def listar_proveedores(
    db: SesionBD,
    paginacion: Paginacion,
    categoria: Annotated[
        CategoriaProveedor | None, Query(description="Línea de suministro.")
    ] = None,
    estado: Annotated[EstadoProveedor | None, Query(description="activo o suspendido.")] = None,
    ciudad: Annotated[str | None, Query(max_length=60, description="Coincidencia parcial.")] = None,
    buscar: Annotated[
        str | None, Query(max_length=80, description="Busca en razón social, NIT y contacto.")
    ] = None,
    dias_credito_maximo: Annotated[
        int | None, Query(ge=0, le=180, description="Plazo de pago máximo aceptable.")
    ] = None,
):
    """
    Listado del panel. Cinco filtros opcionales y combinables entre sí
    (criterio 22) sobre la paginación estándar `?page=&limit=`.
    """
    datos, total = crud.listar(
        db,
        offset=paginacion.offset,
        limite=paginacion.limite,
        categoria=categoria,
        estado=estado,
        ciudad=ciudad,
        buscar=buscar,
        dias_credito_maximo=dias_credito_maximo,
    )
    return {"datos": datos, "paginacion": paginacion.meta(total)}


@router.get(
    "/{proveedor_id}",
    response_model=ProveedorSalida,
    summary="Consultar un proveedor",
    responses=ERROR_NO_ENCONTRADO,
)
def obtener_proveedor(proveedor: ProveedorDeLaRuta):
    """
    El proveedor lo resuelve la dependencia `obtener_proveedor_o_404`
    (criterio 35): si no existe, el request ni siquiera llega hasta aquí.
    """
    return proveedor


@router.post(
    "",
    response_model=ProveedorSalida,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un proveedor",
    responses={
        409: {"description": "Ya existe un proveedor con ese NIT o esa razón social."},
        422: {"description": "Datos inválidos (NIT con DV incorrecto, crédito incoherente...)."},
    },
)
def crear_proveedor(
    datos: ProveedorCrear,
    db: SesionBD,
    tareas: BackgroundTasks,
):
    """
    Crea el proveedor y responde **201** con el recurso completo
    (criterio 19), incluido el `id` que asignó la base de datos.

    El correo de bienvenida al área de compras sale como TAREA EN
    SEGUNDO PLANO (criterio 61): la respuesta no espera al servidor SMTP
    y un fallo de correo no deshace el alta ya confirmada.
    """
    proveedor = crud.crear(db, datos.model_dump())

    tareas.add_task(
        notificar_alta_de_proveedor,
        proveedor_id=proveedor.id,
        razon_social=proveedor.razon_social,
        correo=str(proveedor.correo),
    )
    return proveedor


@router.put(
    "/{proveedor_id}",
    response_model=ProveedorSalida,
    summary="Reemplazar por completo un proveedor",
    responses={
        **ERROR_NO_ENCONTRADO,
        409: {"description": "El NIT o la razón social ya pertenecen a otro proveedor."},
        422: {"description": "Datos inválidos."},
    },
)
def reemplazar_proveedor(
    proveedor: ProveedorDeLaRuta,
    datos: ProveedorReemplazar,
    db: SesionBD,
):
    """PUT = reemplazo total: se exigen todos los campos editables."""
    return crud.reemplazar(db, proveedor, datos.model_dump())


@router.patch(
    "/{proveedor_id}",
    response_model=ProveedorSalida,
    summary="Actualizar parcialmente un proveedor",
    responses={
        **ERROR_NO_ENCONTRADO,
        409: {"description": "El NIT ya pertenece a otro proveedor."},
        422: {"description": "Datos inválidos o crédito incoherente con lo ya guardado."},
    },
)
def actualizar_proveedor(
    proveedor: ProveedorDeLaRuta,
    datos: ProveedorActualizar,
    db: SesionBD,
):
    """
    `exclude_unset=True` (criterio 15): solo se escriben los campos que
    el cliente mencionó. Mandar `{"ciudad": "Medellín"}` no borra el
    sitio web ni la dirección poniéndolos en `null`.

    `estado` no está en el esquema, así que un PATCH nunca puede
    suspender un proveedor por la puerta de atrás: para eso existe el
    sub-recurso `/suspensiones`.
    """
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        return proveedor
    return crud.actualizar_parcial(db, proveedor, cambios)


@router.delete(
    "/{proveedor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    # Criterio 20: un 204 no lleva cuerpo, así que no se declara
    # response_model y la función no retorna nada.
    summary="Eliminar un proveedor sin productos asociados",
    dependencies=[Depends(requiere_rol("admin"))],
    responses={
        **ERROR_NO_ENCONTRADO,
        403: {"description": "Solo un administrador puede eliminar proveedores."},
        409: {"description": "El proveedor todavía surte productos del catálogo."},
        204: {"description": "Eliminado. Sin contenido."},
    },
)
def eliminar_proveedor(proveedor: ProveedorDeLaRuta, db: SesionBD):
    """
    Borrado duro, reservado a admin (misma convención que productos y
    usuarios). Si el proveedor todavía surte catálogo responde **409**,
    no 400 ni 500 (criterio 21): la salida es reasignar esos productos o
    suspender al proveedor.
    """
    crud.eliminar(db, proveedor)
    # Sin `return`: un 204 no lleva cuerpo.


# ----------------------------------------------------------------------
# Sub-recursos: operaciones de negocio (criterio 4)
# ----------------------------------------------------------------------


@router.post(
    "/{proveedor_id}/suspensiones",
    response_model=ProveedorSalida,
    status_code=status.HTTP_201_CREATED,
    summary="Suspender un proveedor y retirar su catálogo",
    responses={
        **ERROR_NO_ENCONTRADO,
        409: {"description": "El proveedor ya está suspendido."},
        422: {"description": "El motivo no cumple el mínimo exigido."},
    },
)
def suspender_proveedor(
    proveedor: ProveedorDeLaRuta,
    datos: SuspensionCrear,
    db: SesionBD,
    usuario=Depends(get_current_user),
):
    """
    Registra una suspensión: cambia el estado del proveedor y desactiva
    de una vez todos sus productos en la tienda, **en una sola
    transacción** (criterio 51).

    Se modela como creación de un sub-recurso (`POST .../suspensiones`)
    porque tiene entrada propia (el motivo), efectos de negocio propios
    y una regla de conflicto propia: suspender lo ya suspendido es 409.
    """
    proveedor_actualizado, _productos_desactivados = crud.suspender(db, proveedor, datos.motivo)
    return proveedor_actualizado


@router.post(
    "/{proveedor_id}/reactivaciones",
    response_model=ProveedorSalida,
    status_code=status.HTTP_201_CREATED,
    summary="Reactivar un proveedor suspendido",
    responses={
        **ERROR_NO_ENCONTRADO,
        409: {"description": "El proveedor ya estaba activo."},
    },
)
def reactivar_proveedor(proveedor: ProveedorDeLaRuta, db: SesionBD):
    """
    Devuelve el proveedor a estado `activo` y limpia el motivo de
    suspensión. Sus productos NO vuelven solos a la tienda: eso se
    decide producto por producto desde la gestión del catálogo.
    """
    return crud.reactivar(db, proveedor)
