"""
Utilidades para el flujo de verificación de correo y restablecimiento
de contraseña basado en OTP (One-Time Password).

Un OTP aquí es siempre un código NUMÉRICO de 6 dígitos (000000-999999),
como el que usan la mayoría de bancos y apps al enviar un código por
correo o SMS. Se usa el mismo patrón en dos lugares del flujo de
autenticación (verificación de cuenta y recuperación de contraseña),
así que vive centralizado acá en vez de duplicarse en
app/routes/usuarios.py.

Reglas de seguridad:
  * El código se genera con el módulo `secrets` (aleatoriedad segura
    para criptografía), nunca con `random`.
  * Solo se guarda su hash SHA-256 en la base de datos
    (usuarios.reset_otp_hash / verificacion_otp_hash), igual que
    password_hash nunca guarda la contraseña en texto plano. El código
    en texto plano solo existe en memoria, el tiempo justo para
    mandarlo por correo.
  * Como el espacio de un código de 6 dígitos es pequeño (10^6
    posibilidades, muy distinto a los 32 bytes aleatorios del token
    de enlace que reemplaza), NO alcanza con que esté hasheado: hace
    falta además limitar los intentos de adivinarlo contra un mismo
    código (ver MAX_INTENTOS_OTP y verificar_otp() en
    app/routes/usuarios.py) y limitar cuántos códigos nuevos se pueden
    pedir por IP (ver LIMITE_RECUPERAR en app/rate_limit.py).
"""

import hashlib
import hmac
import secrets

LONGITUD_OTP = 6


def generar_otp() -> str:
    """
    Genera un código de 6 dígitos numéricos (con ceros a la izquierda
    si hace falta, ej. "004821"), usando secrets.randbelow — el
    generador de números aleatorios seguro de la librería estándar,
    apropiado para tokens/códigos de un solo uso (a diferencia del
    módulo `random`, que NO es seguro para este propósito).
    """
    numero = secrets.randbelow(10**LONGITUD_OTP)
    return str(numero).zfill(LONGITUD_OTP)


def hash_otp(codigo_plano: str) -> str:
    """SHA-256 del código OTP en texto plano. Mismo algoritmo que se
    usaba para el token de enlace (hashlib.sha256), reutilizado aquí
    porque el objetivo es el mismo: nunca guardar en la base de datos
    algo que, si se filtra, sirva tal cual para pasar la verificación."""
    return hashlib.sha256(codigo_plano.encode("utf-8")).hexdigest()


def verificar_otp(codigo_plano: str, hash_guardado: str | None) -> bool:
    """
    Compara un código recibido contra su hash guardado, en tiempo
    constante (hmac.compare_digest) para no filtrar por timing cuánto
    del hash coincide — mismo cuidado que ya aplica bcrypt.verify() en
    app/auth.py para las contraseñas, aplicado aquí a mano porque un
    hash SHA-256 no lo hace por sí solo (a diferencia de bcrypt).
    """
    if not hash_guardado:
        return False
    return hmac.compare_digest(hash_otp(codigo_plano), hash_guardado)
