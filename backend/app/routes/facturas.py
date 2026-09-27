"""
Router de /api/facturas (Quinto Avance).

Una factura se genera SIEMPRE a partir de una venta ya registrada
(POST /api/facturas). El número de factura es correlativo, con el
formato FAC-000001.
"""

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user, requiere_rol
from app.database import get_db
from app.models.factura import DetalleFactura, EstadoFactura, Factura
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.schemas.factura import FacturaCrear, FacturaSalida
from app.utils.factura_venta import generar_pdf_factura_venta
from app.utils.paginacion import construir_meta_paginacion, obtener_parametros_paginacion
from app.utils.busqueda import CARACTER_ESCAPE, patron_contiene

router = APIRouter(prefix="/api/facturas", tags=["facturas"])


def _siguiente_numero(db: Session) -> str:
    total = db.query(Factura).count()
    return f"FAC-{total + 1:06d}"


def _cargar_factura(db: Session, factura_id: int) -> Factura | None:
    return db.query(Factura).options(joinedload(Factura.items)).filter(Factura.id == factura_id).first()


@router.post(
    "",
    response_model=FacturaSalida,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def generar_factura(datos: FacturaCrear, db: Session = Depends(get_db)):
    """Genera la factura de una venta ya registrada. Ruta PROTEGIDA: admin/empleado."""
    venta = db.query(Venta).options(joinedload(Venta.items)).filter(Venta.id == datos.venta_id).first()
    if venta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La venta indicada no existe.")

    factura_existente = db.query(Factura).filter(Factura.venta_id == venta.id).first()
    if factura_existente is not None:
        return _cargar_factura(db, factura_existente.id)

    # cliente_id ya no se pasa aquí: es un association_proxy que se lee
    # de venta.cliente_id (ver app/models/factura.py), no una columna
    # propia que haya que duplicar al crear la factura.
    factura = Factura(
        numero=_siguiente_numero(db),
        venta_id=venta.id,
        subtotal=venta.subtotal,
        impuestos=venta.impuestos,
        total=venta.total,
        estado=EstadoFactura.emitida,
    )
    db.add(factura)
    db.flush()

    for item in venta.items:
        db.add(
            DetalleFactura(
                factura_id=factura.id,
                nombre=item.nombre,
                precio_unitario=item.precio_unitario,
                cantidad=item.cantidad,
                subtotal=item.subtotal,
            )
        )

    db.commit()
    db.refresh(factura)
    return factura


@router.get("", response_model=None)
def listar_facturas(
    numero: str | None = Query(default=None),
    cliente_id: int | None = Query(default=None),
    fecha: date | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Consulta de facturas por número, cliente o fecha (requerimiento 8)."""
    pagina_final, limite_final, offset = obtener_parametros_paginacion(page, limit)

    consulta = db.query(Factura)
    if usuario.rol not in ("admin", "empleado"):
        consulta = consulta.filter(Factura.cliente_id == usuario.id)
    elif cliente_id is not None:
        consulta = consulta.filter(Factura.cliente_id == cliente_id)

    if numero:
        consulta = consulta.filter(Factura.numero.ilike(patron_contiene(numero), escape=CARACTER_ESCAPE))
    if fecha is not None:
        consulta = consulta.filter(
            Factura.creado_en >= datetime.combine(fecha, time.min), Factura.creado_en <= datetime.combine(fecha, time.max)
        )

    total = consulta.count()
    facturas = consulta.order_by(Factura.id.desc()).offset(offset).limit(limite_final).all()

    return {
        "datos": [FacturaSalida.model_validate(f) for f in facturas],
        "paginacion": construir_meta_paginacion(pagina_final, limite_final, total),
    }


@router.get("/{factura_id}", response_model=FacturaSalida)
def obtener_factura(factura_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    factura = _cargar_factura(db, factura_id)
    if factura is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada.")
    if factura.cliente_id != usuario.id and usuario.rol not in ("admin", "empleado"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para ver esta factura.")
    return factura


@router.get("/{factura_id}/pdf")
def descargar_factura_pdf(factura_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    """Descarga de la factura en PDF (requerimiento 9)."""
    factura = _cargar_factura(db, factura_id)
    if factura is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada.")
    if factura.cliente_id != usuario.id and usuario.rol not in ("admin", "empleado"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para ver esta factura.")

    cliente = db.get(Usuario, factura.cliente_id)
    buffer = generar_pdf_factura_venta(factura, cliente)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{factura.numero}.pdf"'},
    )
