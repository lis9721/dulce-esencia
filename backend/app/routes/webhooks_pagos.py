"""
Router de /api/webhooks — recibe los eventos (webhooks) de los
proveedores de pago. Sin autenticación de usuario (Wompi no tiene un
JWT de esta aplicación): la seguridad la da la firma/checksum del
evento, validada dentro de PaymentService.procesar_webhook().

Responde siempre HTTP 200 salvo cuando la firma del evento es
inválida (400): según la documentación oficial de Wompi, cualquier
código distinto de 2xx hace que Wompi reintente el evento hasta 3
veces en las siguientes 24 horas — así que un evento sobre un pago que
no existe en esta base de datos, o una transición de estado que nuestra
máquina de estados no permite, se reconocen con 200 (y se registran en
el log para revisión manual) para no generar reintentos infinitos de
algo que nunca vamos a poder resolver solos.
"""

import logging

from fastapi import APIRouter, Body, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.exceptions.pagos import PagoNoEncontradoException, TransicionEstadoInvalidaException, WebhookValidacionException
from app.services.pagos.payment_service import PaymentService

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
logger = logging.getLogger("app.routes.webhooks_pagos")


@router.post("/wompi")
def webhook_wompi(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    servicio = PaymentService(db, settings)

    try:
        servicio.procesar_webhook("wompi", payload)
    except WebhookValidacionException as error:
        # Única situación en la que SÍ se rechaza el evento: si la
        # firma no es válida, no hay forma segura de confiar en nada
        # de lo demás.
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"success": False, "error": {"message": error.mensaje}})
    except PagoNoEncontradoException as error:
        logger.warning("webhook_pago_no_encontrado", extra={"detalle": error.mensaje})
    except TransicionEstadoInvalidaException as error:
        logger.warning("webhook_transicion_invalida", extra={"detalle": error.mensaje})

    return {"status": "ok"}
