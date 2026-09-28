"""
Router de /api/chatbot (Quinto Avance — requerimientos 17-19).

POST /api/chatbot/mensaje es una ruta PÚBLICA (un visitante sin cuenta
también debe poder recibir atención inicial), pero si el visitante SÍ
tiene sesión iniciada, la conversación queda asociada a su usuario
(get_current_user_opcional). Guarda cada turno en `conversaciones` /
`mensajes` y delega la generación de la respuesta al proveedor de IA
configurado en app/services/chatbot/ai_service.py.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user_opcional
from app.database import get_db
from app.models.chatbot import Conversacion, Mensaje, RolMensaje
from app.models.pqr import PQR, EstadoPQR, TipoPQR
from app.models.usuario import Usuario
from app.schemas.chatbot import ChatbotMensajeEntrada, ChatbotMensajeSalida, ConversacionSalida, ProductoChat
from app.services.chatbot.ai_service import ChatbotNoConfigurado, generar_respuesta
from app.services.chatbot.contexto import construir_contexto
from app.services.chatbot.faq_service import (
    _normalizar,
    es_intencion_pqr,
    productos_para_tarjetas,
    responder_localmente,
    tipo_pqr_sugerido,
)
from app.services.notificaciones import notificar_pqr_recibida

# Descripción mínima que exige PQRCrear (ver app/schemas/pqr.py): un mensaje
# más corto no alcanza a formar una descripción válida, así que en ese caso
# no se intenta crear la PQR automáticamente y se deja la respuesta habitual
# que invita a ampliarlo desde el panel.
LARGO_MINIMO_DESCRIPCION_PQR = 10

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])

def _obtener_o_crear_conversacion(
    db: Session, datos: ChatbotMensajeEntrada, usuario: Usuario | None
) -> Conversacion:
    if datos.conversacion_id is not None:
        conversacion = (
            db.query(Conversacion)
            .options(joinedload(Conversacion.mensajes))
            .filter(Conversacion.id == datos.conversacion_id)
            .first()
        )
        if conversacion is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La conversación indicada no existe.")
        # Un visitante no puede seguir la conversación de otro usuario logueado.
        if conversacion.usuario_id is not None and usuario is not None and conversacion.usuario_id != usuario.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso sobre esta conversación.")
        return conversacion

    conversacion = Conversacion(
        usuario_id=usuario.id if usuario else None,
        sesion_id=datos.sesion_id or (str(uuid.uuid4()) if usuario is None else None),
    )
    db.add(conversacion)
    db.flush()
    return conversacion


def _intentar_crear_pqr_desde_chat(
    db: Session, background_tasks: BackgroundTasks, mensaje: str, usuario: Usuario | None
) -> PQR | None:
    """
    Si el mensaje suena a petición/queja/reclamo/sugerencia y hay un usuario
    con sesión iniciada, la escala de una vez creando la PQR real (en vez de
    solo decirle al cliente que vaya a hacerlo él mismo al panel) — es el
    uso que ya anunciaban los docstrings de `models/chatbot.py` y el campo
    `pqr_creada_id` de `ChatbotMensajeSalida`, pero que nunca quedó
    conectado. Un visitante sin cuenta no puede: `PQR.cliente_id` es
    obligatorio (no hay a quién asociarla), así que para ese caso se
    conserva la respuesta habitual que lo invita a iniciar sesión.
    """
    descripcion = mensaje.strip()
    if usuario is None or len(descripcion) < LARGO_MINIMO_DESCRIPCION_PQR:
        return None
    if not es_intencion_pqr(_normalizar(mensaje)):
        return None

    tipo = TipoPQR(tipo_pqr_sugerido(_normalizar(mensaje)))
    pqr = PQR(
        cliente_id=usuario.id,
        tipo=tipo,
        asunto=(descripcion[:117] + "...") if len(descripcion) > 120 else descripcion,
        descripcion=descripcion,
        estado=EstadoPQR.pendiente,
    )
    db.add(pqr)
    db.commit()
    db.refresh(pqr)

    background_tasks.add_task(
        notificar_pqr_recibida, usuario.correo, usuario.nombre, pqr.id, pqr.tipo.value, pqr.asunto
    )
    return pqr


@router.post("/mensaje", response_model=ChatbotMensajeSalida)
def enviar_mensaje(
    datos: ChatbotMensajeEntrada,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(get_current_user_opcional),
):
    """Envía un mensaje al chatbot. Responde con IA si está configurada; si no, con el chatbot local gratuito."""
    conversacion = _obtener_o_crear_conversacion(db, datos, usuario)

    mensaje_usuario = Mensaje(conversacion_id=conversacion.id, rol=RolMensaje.usuario, contenido=datos.mensaje)
    db.add(mensaje_usuario)
    db.commit()

    historial = [
        {"role": "user" if m.rol == RolMensaje.usuario else "assistant", "content": m.contenido}
        for m in conversacion.mensajes
    ]

    # Orden de respuesta: 1) proveedor de IA (si hay API key y responde);
    # 2) chatbot local gratuito basado en reglas + catálogo real. Así el
    # asistente NUNCA queda mudo ni depende de un servicio de pago.
    origen = "ia"
    try:
        # La IA recibe los datos reales de la tienda (catálogo, servicios y,
        # si hay sesión, los pedidos DE ESE usuario) para no inventar nada.
        texto_respuesta = generar_respuesta(historial, construir_contexto(db, usuario))
    except ChatbotNoConfigurado:
        origen = "local"
        texto_respuesta = responder_localmente(db, datos.mensaje, usuario)

    pqr_creada = _intentar_crear_pqr_desde_chat(db, background_tasks, datos.mensaje, usuario)
    if pqr_creada is not None:
        texto_respuesta = (
            f"Ya registré tu {pqr_creada.tipo.value} con el radicado #{pqr_creada.id}. "
            "Un asesor la revisará y te responderá pronto; también te llegará un correo de confirmación. "
            "Puedes ver su estado en tu panel, sección «PQR»."
        )

    # Tarjetas de producto para comprar desde el chat (no aplican si se acaba
    # de escalar una PQR).
    productos = [] if pqr_creada is not None else productos_para_tarjetas(db, datos.mensaje)

    mensaje_asistente = Mensaje(conversacion_id=conversacion.id, rol=RolMensaje.asistente, contenido=texto_respuesta)
    db.add(mensaje_asistente)
    db.commit()

    return ChatbotMensajeSalida(
        conversacion_id=conversacion.id,
        respuesta=texto_respuesta,
        origen=origen,
        pqr_creada_id=pqr_creada.id if pqr_creada is not None else None,
        productos=[ProductoChat.model_validate(p) for p in productos],
    )


@router.get("/conversaciones/{conversacion_id}", response_model=ConversacionSalida)
def obtener_conversacion(
    conversacion_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(get_current_user_opcional),
):
    """Historial de una conversación (para restaurar el chat al recargar la página)."""
    conversacion = (
        db.query(Conversacion)
        .options(joinedload(Conversacion.mensajes))
        .filter(Conversacion.id == conversacion_id)
        .first()
    )
    if conversacion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada.")
    if conversacion.usuario_id is not None and (usuario is None or usuario.id != conversacion.usuario_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso sobre esta conversación.")
    return conversacion
