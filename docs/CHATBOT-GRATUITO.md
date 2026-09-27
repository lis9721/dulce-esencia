# Chat bot gratuito

Dulce Esencia tiene un asistente virtual (`POST /api/chatbot/mensaje`, widget en el frontend). **No requiere pagar nada**: funciona en dos niveles.

## Nivel 1 — Chatbot local (siempre gratis, sin internet, sin API key)
`backend/app/services/chatbot/faq_service.py`

- **Cómo funciona:** normaliza el texto (minúsculas, sin tildes) → detecta la intención por palabras clave → responde.
- **Usa datos reales:** consulta la base de datos (productos y servicios activos, con precio y aviso de "agotado"), así no inventa precios.
- **Intenciones:** saludo, catálogo por categoría (tortas, cupcakes, galletas…) o nombre, servicios, métodos de pago (tarjeta/Wompi, transferencia, contraentrega), cupones, seguimiento de pedidos, PQR, contacto; si no entiende, lo dice y ofrece el menú.
- **Cuándo se activa:** cuando **no hay `OPENAI_API_KEY`** o el proveedor de IA falla. (La respuesta trae `"origen": "local"`.)
- **Pruebas:** `tests/test_chatbot_local.py` (13 casos).

Limitación honesta: es un sistema de reglas; entiende lo previsto, no conversa libremente. Para eso está el nivel 2.

## Nivel 2 — IA generativa con capa gratuita (opcional)
`services/chatbot/ai_service.py` usa el SDK `openai` con **`OPENAI_BASE_URL` configurable**, así que sirve con cualquier proveedor compatible. Solo cambia el `.env`:

```env
# Groq (registro solo con correo; modelos abiertos como Llama)
OPENAI_API_KEY=gsk_tu_llave
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.3-70b-versatile

# Google Gemini (AI Studio)
# OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
# OPENAI_MODEL=gemini-2.0-flash

# OpenRouter (modelos con sufijo :free)
# OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Ollama: 100 % local en tu PC, sin límites ni internet (ollama.com)
# OPENAI_API_KEY=ollama
# OPENAI_BASE_URL=http://localhost:11434/v1
# OPENAI_MODEL=llama3.2
```

⚠️ **Límites y modelos disponibles cambian con frecuencia** (las fuentes que consulté no coinciden en los topes diarios de Groq). Revisa la página del proveedor antes de decidir; cuando se agote la cuota, el chatbot **no se cae**: responde el nivel 1.

> El respaldo cubre **los dos casos**: sin llave configurada, o con llave pero el proveedor falla (cuota agotada 429, sin red, error del servidor). En `ai_service.py` cualquier `APIError` del SDK se convierte en `ChatbotNoConfigurado`, y `routes/chatbot.py` responde entonces con el chatbot local (`"origen": "local"`). Lo que **no** probé: una llamada real a un proveedor de IA.
