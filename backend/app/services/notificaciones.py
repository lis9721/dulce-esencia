"""
services/notificaciones.py

Envío de correos electrónicos pensado para ejecutarse como TAREA EN
SEGUNDO PLANO de FastAPI (`BackgroundTasks`), es decir: después de que
el endpoint ya respondió al cliente. Así el usuario no espera a que el
servidor SMTP conteste (un SMTP lento o caído no hace lento ni rompe
el registro, la recuperación de contraseña ni la creación de una PQR).

Reglas de diseño:
  * Las funciones reciben SOLO datos simples (str, int), nunca objetos
    ORM: cuando la tarea corre, la sesión de la base de datos del
    request ya se cerró y un objeto ORM quedaría "desconectado".
  * Nunca lanzan excepciones hacia FastAPI: un fallo de correo se
    registra en el log y ya. La operación de negocio (crear la PQR, el
    usuario...) ya se confirmó en la base de datos y no debe deshacerse
    por un problema de correo.
  * Sin SMTP_HOST configurado no se envía nada: se deja el mensaje en
    el log (modo desarrollo / pruebas).
"""

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger("app.services.notificaciones")


def enviar_correo(destino: str, asunto: str, cuerpo: str) -> bool:
    """Envía un correo de texto plano. Devuelve True si se envió por SMTP."""
    settings = get_settings()

    if not settings.SMTP_HOST:
        logger.info("correo_simulado destino=%s asunto=%s\n%s", destino, asunto, cuerpo)
        return False

    mensaje = EmailMessage()
    mensaje["From"] = settings.SMTP_FROM
    mensaje["To"] = destino
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as servidor:
            servidor.starttls()
            if settings.SMTP_USER:
                servidor.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            servidor.send_message(mensaje)
    except (smtplib.SMTPException, OSError):
        logger.exception("correo_fallido destino=%s asunto=%s", destino, asunto)
        return False

    logger.info("correo_enviado destino=%s asunto=%s", destino, asunto)
    return True


def enviar_verificacion_cuenta(correo: str, nombre: str, codigo: str, minutos_vigencia: int) -> None:
    """Envía el código OTP de 6 dígitos para confirmar la cuenta (segundo
    paso del registro). Reemplaza al enlace de verificación anterior:
    el usuario ahora escribe el código a mano en /verificar-correo."""
    enviar_correo(
        correo,
        "Tu código para verificar tu cuenta de Dulce Esencia Pastelería",
        f"Hola {nombre},\n\n"
        "Gracias por registrarte en Dulce Esencia Pastelería. Usa este código "
        f"para confirmar tu correo (vigente por {minutos_vigencia} minutos):\n\n"
        f"    {codigo}\n\n"
        "No compartas este código con nadie. Si no creaste esta cuenta, ignora este mensaje.",
    )


def enviar_recuperacion_password(correo: str, nombre: str, codigo: str, minutos_vigencia: int) -> None:
    """Envía el código OTP de 6 dígitos para restablecer la contraseña.
    Reemplaza al enlace de recuperación anterior: el usuario ahora
    escribe el código a mano en /restablecer-password."""
    enviar_correo(
        correo,
        "Tu código para restablecer tu contraseña de Dulce Esencia Pastelería",
        f"Hola {nombre},\n\n"
        "Recibimos una solicitud para restablecer tu contraseña. Usa este código "
        f"(vigente por {minutos_vigencia} minutos):\n\n"
        f"    {codigo}\n\n"
        "No compartas este código con nadie. Si no fuiste tú, ignora este mensaje: "
        "tu contraseña actual sigue funcionando.",
    )


def notificar_pqr_recibida(correo: str, nombre: str, pqr_id: int, tipo: str, asunto: str) -> None:
    enviar_correo(
        correo,
        f"Recibimos tu {tipo} (radicado #{pqr_id})",
        f"Hola {nombre},\n\n"
        f"Registramos tu {tipo} «{asunto}» con el radicado #{pqr_id}. "
        "Un asesor la revisará y te responderá lo antes posible. "
        "Puedes ver su estado en tu panel, sección PQR.\n\n"
        "Equipo Dulce Esencia Pastelería",
    )


# ----------------------------------------------------------------------
# Pedidos — confirmación de compra y cambios de estado (ver
# app/routes/pedidos.py). Todas reciben datos simples (nunca un objeto
# `Pedido` de SQLAlchemy), por la misma razón explicada arriba: corren
# después de que la sesión de base de datos del request ya se cerró.
# ----------------------------------------------------------------------

_MENSAJE_POR_ESTADO = {
    "pagado": "Tu pago fue confirmado. Ya estamos preparando tu pedido.",
    "enviado": "Tu pedido salió de la pastelería y va en camino (o ya está listo para recoger en tienda).",
    "entregado": "Tu pedido fue entregado. ¡Gracias por comprar en Dulce Esencia!",
    "cancelado": "Tu pedido fue cancelado.",
}


def notificar_pedido_confirmado(
    correo: str,
    nombre: str,
    pedido_id: int,
    total: float,
    tipo_entrega: str,
    fecha_entrega_solicitada: str | None,
    franja_horaria: str | None,
) -> None:
    """Se envía al confirmar la compra (POST /api/pedidos), sin importar el método de pago elegido."""
    lineas_entrega = [f"Pedido #{pedido_id} — Total: ${total:,.0f} COP".replace(",", ".")]
    if tipo_entrega == "recoger_tienda":
        lineas_entrega.append("Entrega: recoges tu pedido en la tienda.")
    else:
        lineas_entrega.append("Entrega: a domicilio.")
    if fecha_entrega_solicitada:
        franja = f" ({franja_horaria})" if franja_horaria else ""
        lineas_entrega.append(f"Fecha solicitada: {fecha_entrega_solicitada}{franja}")

    enviar_correo(
        correo,
        f"Confirmamos tu pedido #{pedido_id} — Dulce Esencia Pastelería",
        f"Hola {nombre},\n\n"
        "¡Gracias por tu compra! Registramos tu pedido con estos datos:\n\n"
        + "\n".join(f"  - {linea}" for linea in lineas_entrega)
        + "\n\nTe avisaremos por este mismo correo cada vez que su estado cambie. "
        "Puedes ver el detalle y la factura en tu panel, sección Mis Pedidos.\n\n"
        "Equipo Dulce Esencia Pastelería",
    )


def notificar_pedido_cambio_estado(correo: str, nombre: str, pedido_id: int, estado_nuevo: str) -> None:
    """
    Se envía cada vez que un pedido cambia de estado (PATCH
    /api/pedidos/{id}/estado, o la cancelación en
    POST /api/pedidos/{id}/cancelar). No se envía para el estado
    `pendiente` — ese ya lo cubre `notificar_pedido_confirmado` al
    crear el pedido.
    """
    detalle = _MENSAJE_POR_ESTADO.get(estado_nuevo, f"Tu pedido cambió de estado a: {estado_nuevo}.")
    enviar_correo(
        correo,
        f"Actualización de tu pedido #{pedido_id} — Dulce Esencia Pastelería",
        f"Hola {nombre},\n\n{detalle}\n\n"
        "Puedes ver el detalle completo en tu panel, sección Mis Pedidos.\n\n"
        "Equipo Dulce Esencia Pastelería",
    )


def notificar_pedido_cancelado(correo: str, nombre: str, pedido_id: int, con_reembolso: bool) -> None:
    """
    Variante de `notificar_pedido_cambio_estado` para la cancelación,
    con una línea extra sobre el reembolso cuando aplicó (ver
    POST /api/pedidos/{id}/cancelar).
    """
    linea_reembolso = (
        "El pago que ya habías realizado fue reembolsado; el dinero puede tardar unos días "
        "hábiles en reflejarse según tu banco o método de pago."
        if con_reembolso
        else "Este pedido no tenía un pago aprobado asociado, así que no hay ningún cobro que reembolsar."
    )
    enviar_correo(
        correo,
        f"Cancelamos tu pedido #{pedido_id} — Dulce Esencia Pastelería",
        f"Hola {nombre},\n\nTu pedido #{pedido_id} fue cancelado. {linea_reembolso}\n\n"
        "Si no solicitaste esta cancelación, contáctanos respondiendo este correo.\n\n"
        "Equipo Dulce Esencia Pastelería",
    )
