"""
Firma de integridad (para crear transacciones/Web Checkout) y checksum
de eventos (para validar webhooks) de Wompi.

Implementados EXACTAMENTE como los describe la documentación oficial
vigente de Wompi Colombia:
  - Firma de integridad: https://docs.wompi.co/docs/colombia/widget-checkout-web/
  - Checksum de eventos:  https://docs.wompi.co/docs/colombia/eventos/

No se inventa ningún formato: si la documentación oficial cambia, este
es el único archivo que hay que actualizar.
"""

import hashlib
from typing import Any


def generar_firma_integridad(
    *,
    referencia: str,
    monto_centavos: int,
    moneda: str,
    secreto_integridad: str,
    fecha_expiracion: str | None = None,
) -> str:
    """
    SHA256("<referencia><monto_centavos><moneda><secreto_integridad>"),
    en ese orden exacto. Es la firma que exige Wompi tanto para el Web
    Checkout (parámetro `signature:integrity`) como para crear una
    transacción por API (campo `signature`).

    Si se usa el parámetro opcional `expiration-time` (fecha_expiracion,
    en formato ISO 8601 UTC con milisegundos, p. ej.
    "2023-06-09T20:28:50.000Z"), la documentación oficial exige
    insertarlo ANTES del secreto de integridad:
    "<referencia><monto_centavos><moneda><fecha_expiracion><secreto_integridad>".
    Si `fecha_expiracion` es None, la fórmula es exactamente la de
    siempre (sin ese segmento) — no rompe nada de lo ya integrado.
    """
    cadena = f"{referencia}{monto_centavos}{moneda}"
    if fecha_expiracion:
        cadena += fecha_expiracion
    cadena += secreto_integridad
    return hashlib.sha256(cadena.encode("utf-8")).hexdigest()


def _extraer_valor_por_ruta(datos: dict[str, Any], ruta: str) -> Any:
    """
    `ruta` es del estilo "transaction.id" o "transaction.amount_in_cents"
    (tal como vienen en `signature.properties`): navega el dict
    `data` del evento siguiendo cada segmento separado por ".".
    """
    valor: Any = datos
    for segmento in ruta.split("."):
        if not isinstance(valor, dict) or segmento not in valor:
            raise KeyError(f"La propiedad '{ruta}' no existe en el evento (falló en '{segmento}').")
        valor = valor[segmento]
    return valor


def calcular_checksum_evento(
    *, data: dict[str, Any], propiedades: list[str], timestamp: int, secreto_eventos: str
) -> str:
    """
    Reconstruye el checksum de un evento de Wompi:

      1. Concatena, EN EL ORDEN dado por `propiedades`, el valor de
         cada propiedad (extraído de `data` navegando su ruta con
         puntos, p. ej. "transaction.id").
      2. Concatena el `timestamp` del evento.
      3. Concatena el secreto de eventos del comercio
         (WOMPI_EVENTS_SECRET).
      4. Aplica SHA256 y retorna el resultado en hexadecimal.

    Nunca se asume una lista fija de propiedades: siempre se usa la
    que trae el propio evento en `signature.properties`, tal como
    exige la documentación oficial.
    """
    cadena = "".join(str(_extraer_valor_por_ruta(data, propiedad)) for propiedad in propiedades)
    cadena += f"{timestamp}{secreto_eventos}"
    return hashlib.sha256(cadena.encode("utf-8")).hexdigest()
