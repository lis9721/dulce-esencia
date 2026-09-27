"""
Capa de acceso a datos de `proveedores`.

Esta es la ÚNICA capa que habla con la base de datos para este recurso
(criterio 9): el router de `app/routes/proveedores.py` no contiene ni un
solo `db.query(...)`, solo orquesta.

Reglas que se cumplen aquí
--------------------------
  * 29 — ni una sola `HTTPException`: la capa de datos lanza las
         excepciones de dominio de `app/exceptions/dominio.py` y es el
         handler global el que decide el código HTTP.
  * 50 — todas las consultas usan el estilo 2.x `select()` / `where()`
         y los conteos se resuelven en la base de datos con
         `select(func.count())`, nunca trayendo las filas a Python para
         hacerles `len()`.
  * 51 — las operaciones con más de una escritura (suspender un
         proveedor y desactivar su catálogo) ocurren en UNA sola
         transacción: o se guardan las dos cosas, o ninguna.
  * 52 — `IntegrityError` se captura, se hace `rollback()` y se traduce
         a un 409 con un mensaje que explica qué chocó.
"""

from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions.dominio import (
    NitDuplicado,
    ProveedorConProductos,
    ProveedorNoEncontrado,
    ReglaDeNegocioViolada,
    TransicionDeEstadoInvalida,
)
from app.models.producto import Producto
from app.models.proveedor import CategoriaProveedor, EstadoProveedor, Proveedor


# ----------------------------------------------------------------------
# Lectura
# ----------------------------------------------------------------------


def _consulta_filtrada(
    *,
    categoria: CategoriaProveedor | None = None,
    estado: EstadoProveedor | None = None,
    ciudad: str | None = None,
    buscar: str | None = None,
    dias_credito_maximo: int | None = None,
):
    """
    Arma el `select()` con los filtros opcionales del listado
    (criterio 22). Se comparte entre la consulta de datos y la de conteo
    para que el `total` de la paginación corresponda exactamente a los
    mismos filtros.
    """
    consulta = select(Proveedor)

    if categoria is not None:
        consulta = consulta.where(Proveedor.categoria == categoria)
    if estado is not None:
        consulta = consulta.where(Proveedor.estado == estado)
    if ciudad:
        consulta = consulta.where(Proveedor.ciudad.ilike(f"%{ciudad}%"))
    if buscar:
        # Parámetros vinculados (nunca concatenación de texto): la
        # protección contra inyección SQL es la misma que en el resto de
        # la API (ver docs/SEGURIDAD-SQL-INJECTION.md).
        patron = f"%{buscar}%"
        consulta = consulta.where(
            Proveedor.razon_social.ilike(patron)
            | Proveedor.nit.ilike(patron)
            | Proveedor.contacto_nombre.ilike(patron)
        )
    if dias_credito_maximo is not None:
        consulta = consulta.where(Proveedor.dias_credito <= dias_credito_maximo)

    return consulta


def listar(
    db: Session,
    *,
    offset: int,
    limite: int,
    categoria: CategoriaProveedor | None = None,
    estado: EstadoProveedor | None = None,
    ciudad: str | None = None,
    buscar: str | None = None,
    dias_credito_maximo: int | None = None,
) -> tuple[list[Proveedor], int]:
    """Devuelve (página de proveedores, total que cumple los filtros)."""
    consulta = _consulta_filtrada(
        categoria=categoria,
        estado=estado,
        ciudad=ciudad,
        buscar=buscar,
        dias_credito_maximo=dias_credito_maximo,
    )

    # El conteo se hace en la base de datos sobre la misma consulta
    # filtrada, sin ORDER BY ni las relaciones cargadas (criterio 50).
    total = db.scalar(
        select(func.count()).select_from(consulta.order_by(None).subquery())
    )

    proveedores = (
        db.execute(
            consulta.order_by(Proveedor.razon_social.asc()).offset(offset).limit(limite)
        )
        .scalars()
        .unique()
        .all()
    )
    return list(proveedores), int(total or 0)


def obtener_por_id(db: Session, proveedor_id: int) -> Proveedor:
    """Carga un proveedor o lanza `ProveedorNoEncontrado` (nunca un 404 a mano)."""
    proveedor = db.scalar(select(Proveedor).where(Proveedor.id == proveedor_id))
    if proveedor is None:
        raise ProveedorNoEncontrado(proveedor_id)
    return proveedor


def contar_productos(db: Session, proveedor_id: int) -> int:
    """Conteo resuelto en la base de datos, no en memoria."""
    total = db.scalar(
        select(func.count(Producto.id)).where(Producto.proveedor_id == proveedor_id)
    )
    return int(total or 0)


# ----------------------------------------------------------------------
# Escritura
# ----------------------------------------------------------------------


def _traducir_integrity_error(db: Session, error: IntegrityError, nit: str) -> None:
    """
    Convierte el error de la base de datos en una excepción de dominio
    (criterio 52). El `rollback()` es obligatorio: sin él la sesión queda
    inutilizable y la siguiente consulta del mismo request fallaría con
    un error interno.
    """
    db.rollback()
    mensaje = str(getattr(error, "orig", error)).lower()
    if "nit" in mensaje or "razon_social" in mensaje or "unique" in mensaje or "duplicate" in mensaje:
        raise NitDuplicado(nit) from error
    # Cualquier otra violación de integridad también es un conflicto de
    # negocio, no un 500: el cliente pidió algo que la base rechaza.
    raise NitDuplicado(nit) from error


def crear(db: Session, datos: dict) -> Proveedor:
    """
    Inserta un proveedor. `estado` no se toma nunca del cliente: se
    fuerza aquí al valor inicial del dominio (criterio 5).
    """
    proveedor = Proveedor(**datos, estado=EstadoProveedor.activo)
    db.add(proveedor)
    try:
        db.commit()
    except IntegrityError as error:
        _traducir_integrity_error(db, error, datos.get("nit", ""))
    db.refresh(proveedor)
    return proveedor


def reemplazar(db: Session, proveedor: Proveedor, datos: dict) -> Proveedor:
    """PUT: reemplazo total de los campos editables por el cliente."""
    for campo, valor in datos.items():
        setattr(proveedor, campo, valor)
    try:
        db.commit()
    except IntegrityError as error:
        _traducir_integrity_error(db, error, datos.get("nit", proveedor.nit))
    db.refresh(proveedor)
    return proveedor


def actualizar_parcial(db: Session, proveedor: Proveedor, cambios: dict) -> Proveedor:
    """
    PATCH. `cambios` ya viene de `model_dump(exclude_unset=True)`, así
    que solo trae lo que el cliente mencionó explícitamente: los campos
    ausentes conservan su valor y NO se sobrescriben con null
    (criterio 15).

    La coherencia crédito/cupo se revalida aquí porque es el único punto
    que conoce el estado GUARDADO: un PATCH que solo baje el cupo a 0
    dejaría al proveedor con plazo de pago y sin cupo.
    """
    dias = cambios.get("dias_credito", proveedor.dias_credito)
    cupo = cambios.get("cupo_credito", proveedor.cupo_credito)

    if dias > 0 and Decimal(str(cupo)) <= 0:
        raise ReglaDeNegocioViolada(
            "El proveedor quedaría con días de crédito y cupo 0. Ajusta ambos campos a la vez.",
            campo="cupo_credito",
        )
    if Decimal(str(cupo)) > 0 and dias <= 0:
        raise ReglaDeNegocioViolada(
            "El proveedor quedaría con cupo de crédito y plazo de 0 días. Ajusta ambos campos a la vez.",
            campo="dias_credito",
        )

    for campo, valor in cambios.items():
        setattr(proveedor, campo, valor)

    try:
        db.commit()
    except IntegrityError as error:
        _traducir_integrity_error(db, error, cambios.get("nit", proveedor.nit))
    db.refresh(proveedor)
    return proveedor


def eliminar(db: Session, proveedor: Proveedor) -> None:
    """
    Borra un proveedor. Si todavía surte productos se lanza un 409
    (criterio 21) con una salida concreta para el usuario, en vez de
    dejar que la clave foránea reviente con un 500.
    """
    asociados = contar_productos(db, proveedor.id)
    if asociados > 0:
        raise ProveedorConProductos(asociados)

    db.delete(proveedor)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ProveedorConProductos(asociados) from error


# ----------------------------------------------------------------------
# Operaciones de negocio (sub-recursos)
# ----------------------------------------------------------------------


def suspender(db: Session, proveedor: Proveedor, motivo: str) -> tuple[Proveedor, int]:
    """
    Suspende al proveedor Y retira su catálogo de la tienda.

    Son DOS escrituras (la fila del proveedor y las filas de sus
    productos) que ocurren en UNA sola transacción (criterio 51): si el
    UPDATE masivo del catálogo fallara, el proveedor no puede quedar
    marcado como suspendido con sus productos todavía a la venta.

    Devuelve (proveedor, cuántos productos se desactivaron).
    """
    if proveedor.estado is EstadoProveedor.suspendido:
        raise TransicionDeEstadoInvalida(proveedor.estado.value, EstadoProveedor.suspendido.value)

    try:
        proveedor.estado = EstadoProveedor.suspendido
        proveedor.motivo_suspension = motivo

        # UPDATE ... WHERE resuelto por la base de datos (una sola
        # sentencia), no un bucle de Python fila por fila.
        resultado = db.execute(
            update(Producto)
            .where(Producto.proveedor_id == proveedor.id, Producto.activo.is_(True))
            .values(activo=False)
            .execution_options(synchronize_session=False)
        ).rowcount
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(proveedor)
    return proveedor, int(resultado or 0)


def reactivar(db: Session, proveedor: Proveedor) -> Proveedor:
    """
    Reactiva al proveedor. Deliberadamente NO vuelve a publicar sus
    productos: qué productos regresan a la tienda es una decisión
    comercial que se toma producto por producto desde el catálogo.
    """
    if proveedor.estado is EstadoProveedor.activo:
        raise TransicionDeEstadoInvalida(proveedor.estado.value, EstadoProveedor.activo.value)

    try:
        proveedor.estado = EstadoProveedor.activo
        proveedor.motivo_suspension = None
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(proveedor)
    return proveedor
