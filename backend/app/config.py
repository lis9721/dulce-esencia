"""
Configuración central de la aplicación.

Lee las variables de entorno desde el .env PROPIO de este backend
Python (backend/.env), independiente del .env del backend Node
(backend-node/.env): nombres de variable propios (SECRET_KEY,
ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES) en vez de reutilizar
JWT_SECRET/JWT_EXPIRES_IN de Node. Igual que validarEnv.js en Node,
falla ruidosamente al arrancar si SECRET_KEY falta o es insegura, en
vez de arrancar y firmar tokens con un secreto adivinable.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Mismos valores placeholder que el backend Node rechazaba en
# validarEnv.js para JWT_SECRET — aplican igual aquí para SECRET_KEY.
SECRETOS_PLACEHOLDER = {"your_secret_key_here", "clave_de_desarrollo", "changeme", "secret"}
LONGITUD_MINIMA_SECRETO = 32


class Settings(BaseSettings):
    """Variables de entorno de la aplicación (ver .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Base de datos (MySQL/MariaDB vía XAMPP en local; TiDB Serverless en Vercel) ---
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_NAME: str = "essentia_db"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    # TiDB Cloud Starter exige TLS. En local (XAMPP) se deja en False;
    # en Vercel (producción y preview) se define DB_SSL=true. Ver
    # docs/DEPLOY.md y el connect_args centralizado en app/database.py.
    DB_SSL: bool = False
    # En Vercel, la creación/alteración de tablas NO debe correr en cada
    # cold start de la función (agrega latencia y repite ALTER TABLE en
    # cada instancia nueva). Se deja en False solo para desarrollo local;
    # en producción se pone en True y el "sync" de esquema corre una única
    # vez desde el workflow de deploy (backend/scripts/sync_schema.py),
    # antes de publicar el código nuevo — ver docs/DEPLOY.md.
    SKIP_SCHEMA_SYNC: bool = False

    # --- Autenticación (nombres propios de este backend, NO los de Node) ---
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8h, mismo valor que JWT_EXPIRES_IN=8h en Node

    # --- Servidor / CORS ---
    NODE_ENV: str = "development"
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGIN: str = ""  # lista separada por comas, solo se usa en producción
    APP_URL: str = "http://localhost:8000"

    # --- Módulo de pagos (Wompi Colombia — Sandbox por defecto) ---
    # "sandbox" o "production". Ver docs/modulo-pagos-wompi.md para el
    # paso a paso de cómo pasar de uno a otro.
    PAYMENT_ENV: str = "sandbox"
    WOMPI_SANDBOX_MOCK: bool = False
    WOMPI_PUBLIC_KEY: str = ""
    WOMPI_PRIVATE_KEY: str = ""
    # Secreto de eventos (para validar webhooks) y secreto de
    # integridad (para firmar la creación de pagos) — son DOS secretos
    # distintos en el dashboard de Wompi ("Secretos para integración
    # técnica"), nunca el mismo valor.
    WOMPI_EVENTS_SECRET: str = ""
    WOMPI_INTEGRITY_SECRET: str = ""
    WOMPI_API_URL: str = "https://sandbox.wompi.co/v1"
    WOMPI_CHECKOUT_URL: str = "https://checkout.wompi.co/p/"
    # Minutos de validez del link de Web Checkout que se le manda al
    # cliente (parámetro opcional `expiration-time` de Wompi). Evita
    # que un link viejo (p. ej. copiado de un correo antiguo, o de una
    # pestaña que quedó abierta días) se pueda seguir usando para pagar
    # un pedido que quizás ya cambió de precio o de estado. 0 lo
    # desactiva (el link no expira nunca del lado de Wompi).
    WOMPI_CHECKOUT_EXPIRACION_MINUTOS: int = 60

    # --- Chatbot con Inteligencia Artificial (Quinto Avance) ---
    # Se lee SIEMPRE de la variable de entorno — nunca se hardcodea ni
    # se recibe por parámetro (requerimiento 19: gestión segura de la
    # API Key). Si queda vacía, /api/chatbot/mensaje responde 503 en
    # vez de arrancar el servidor sin poder ofrecer el resto de la API
    # (mismo criterio que las variables WOMPI_*, ver validar_env()).
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    # Solo se define si se usa un proveedor compatible con la API de
    # OpenAI distinto de OpenAI mismo (Groq, OpenRouter, un modelo
    # local, etc.). Vacío = usa el endpoint oficial de OpenAI.
    OPENAI_BASE_URL: str = ""

    # --- Correo saliente (SMTP) para las tareas en segundo plano ---
    # Opcional. Si SMTP_HOST queda vacío, app/services/notificaciones.py
    # NO falla: solo deja el mensaje en el log del servidor (útil en
    # desarrollo y en las pruebas). Gmail, Brevo, Mailtrap, etc. sirven
    # tal cual: solo cambian host/puerto/credenciales.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "Dulce Esencia Pastelería <no-responder@dulceesencia.local>"

    @property
    def database_url(self) -> str:
        """URL de conexión SQLAlchemy usando el driver PyMySQL."""
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def origenes_permitidos(self) -> list[str]:
        """Réplica exacta de la lógica de origenesPermitidos en server.js."""
        if self.NODE_ENV == "production":
            return [o.strip() for o in self.CORS_ORIGIN.split(",") if o.strip()]
        return [self.FRONTEND_URL]


def validar_env(settings: "Settings") -> None:
    """
    Corta el arranque si falta SECRET_KEY o sigue siendo el valor de
    ejemplo del .env.example — mismo criterio que validarEnv.js en Node,
    aplicado a la variable propia de este backend.

    Las variables WOMPI_* NO se validan aquí a propósito: no son
    obligatorias para que el resto de la API (usuarios, productos,
    pedidos, etc.) arranque. Si faltan, el error solo aparece al
    intentar usar el módulo de pagos (ver
    WompiProvider._validar_credenciales en
    app/services/pagos/wompi_provider.py), con un mensaje explícito de
    qué variable falta.
    """
    errores: list[str] = []

    if not settings.SECRET_KEY:
        errores.append("SECRET_KEY no está definida en el .env.")
    elif settings.SECRET_KEY in SECRETOS_PLACEHOLDER:
        errores.append(
            "SECRET_KEY sigue siendo el valor de ejemplo. Genera una propia, por ejemplo con:\n"
            "    python -c \"import secrets; print(secrets.token_hex(48))\""
        )
    elif len(settings.SECRET_KEY) < LONGITUD_MINIMA_SECRETO:
        errores.append(
            f"SECRET_KEY es demasiado corta ({len(settings.SECRET_KEY)} caracteres). "
            f"Debe tener al menos {LONGITUD_MINIMA_SECRETO}."
        )

    if errores:
        mensaje = "\n".join(f"  - {e}" for e in errores)
        raise RuntimeError(
            "No se puede arrancar el servidor — configuración insegura o incompleta:\n\n"
            f"{mensaje}\n\nRevisa backend/.env antes de volver a intentarlo."
        )


@lru_cache
def get_settings() -> Settings:
    """Instancia cacheada de Settings, para usar como dependencia de FastAPI."""
    return Settings()
