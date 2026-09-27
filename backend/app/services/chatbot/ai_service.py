"""
services/chatbot/ai_service.py

Envuelve la llamada al proveedor de Inteligencia Artificial que usa el
Chatbot (requerimientos 17-19 del quinto avance). Usa la API de OpenAI
(paquete `openai`, agregado a requirements.txt) por defecto, pero
cualquier proveedor con una API compatible con /v1/chat/completions
(OpenAI, Groq, OpenRouter, un modelo local vía LM Studio/Ollama, etc.)
sirve tal cual: solo hay que apuntar OPENAI_BASE_URL al endpoint de ese
proveedor en backend/.env.

La API Key NUNCA se recibe por parámetro ni se hardcodea: siempre se
lee de la variable de entorno OPENAI_API_KEY (ver app/config.py), igual
que exige el requerimiento 19 ("Gestión segura de la API Key").
"""

from openai import APIError, OpenAI

from app.config import get_settings

PROMPT_SISTEMA = """Eres el asistente virtual de Dulce Esencia Pastelería, una tienda en línea de \
tortas, cupcakes, galletas, postres y panadería artesanal, con servicios como tortas personalizadas y mesas de dulces para eventos.

Tu trabajo es:
- Responder preguntas frecuentes sobre productos, servicios, envíos, métodos de pago y el \
proceso de compra del sitio.
- Orientar al cliente en el proceso de compra (catálogo en /tienda, carrito, checkout).
- Si el cliente tiene una queja, reclamo, petición o sugerencia (PQR) que tú no puedes resolver \
directamente, indícale con claridad que puede registrarla en la sección de PQR del sitio para que \
el equipo humano la atienda, y ofrécete a resumir lo que te contó para que no tenga que \
repetirlo.
- Sé breve, cordial y concreto. Responde siempre en español.
- No inventes precios, stock ni políticas que no te hayan dado: si no tienes el dato, dile al \
cliente que lo puede confirmar en la tienda o con un asesor humano vía PQR.
"""


class ChatbotNoConfigurado(Exception):
    """Se lanza cuando falta OPENAI_API_KEY en el entorno — ver app/routes/chatbot.py."""


# Tope de espera a la IA (criterio 58 de docs/AUDITORIA-LISTA-CHEQUEO.md:
# "timeout/reintentos"). Sin esto, un proveedor lento dejaba la petición
# colgada indefinidamente en vez de degradar al chatbot local a tiempo.
TIMEOUT_SEGUNDOS = 15.0
REINTENTOS = 1


def _cliente_openai() -> OpenAI:
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        raise ChatbotNoConfigurado(
            "El chatbot con IA no está configurado: falta OPENAI_API_KEY en backend/.env."
        )
    kwargs = {"api_key": settings.OPENAI_API_KEY, "timeout": TIMEOUT_SEGUNDOS, "max_retries": REINTENTOS}
    if settings.OPENAI_BASE_URL:
        kwargs["base_url"] = settings.OPENAI_BASE_URL
    return OpenAI(**kwargs)


def generar_respuesta(historial: list[dict]) -> str:
    """
    `historial` es una lista de mensajes previos en formato
    [{"role": "user"|"assistant", "content": "..."}], ya sin el prompt
    de sistema (se agrega acá). Devuelve el texto de la respuesta del
    asistente.
    """
    settings = get_settings()
    cliente = _cliente_openai()

    mensajes = [{"role": "system", "content": PROMPT_SISTEMA}, *historial]

    try:
        respuesta = cliente.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=mensajes,
            max_tokens=400,
            temperature=0.4,
        )
    except APIError as error:
        raise ChatbotNoConfigurado(f"El servicio de IA no respondió correctamente: {error}") from error

    texto = (respuesta.choices[0].message.content or "").strip()
    if not texto:
        # Validación de la respuesta (criterio 60): un content vacío/None
        # (recorte por longitud, filtro de contenido del proveedor, etc.)
        # antes se devolvía tal cual y el usuario recibía un mensaje en
        # blanco. Al tratarlo como fallo se degrada al chatbot local, que
        # sí siempre responde algo.
        raise ChatbotNoConfigurado("El proveedor de IA devolvió una respuesta vacía.")
    return texto
