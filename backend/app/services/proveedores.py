"""
Servicios del módulo de proveedores: lógica que no es acceso a datos ni
manejo de HTTP.

`notificar_alta_de_proveedor` es la tarea en SEGUNDO PLANO del módulo
(criterio 61 de la lista de chequeo) y cumple las tres reglas de ese
criterio:

  1. Abre y cierra SU PROPIA sesión de base de datos. Cuando la tarea
     corre, el request ya terminó y la sesión de `get_db()` está cerrada:
     reutilizarla lanzaría `DetachedInstanceError`.
  2. Recibe datos simples (int, str), nunca objetos ORM, por la misma
     razón.
  3. Captura TODA excepción. Un fallo de correo no puede tumbar el
     proceso del servidor ni deshacer el alta, que ya está confirmada en
     la base de datos.
"""

import logging

from app.database import SessionLocal
from app.services.notificaciones import enviar_correo

logger = logging.getLogger("app.services.proveedores")


def notificar_alta_de_proveedor(proveedor_id: int, razon_social: str, correo: str) -> None:
    """
    Avisa al proveedor recién registrado y deja constancia en el log.
    Se ejecuta con `BackgroundTasks` desde POST /api/proveedores.
    """
    sesion = SessionLocal()  # sesión propia de la tarea (regla 1)
    try:
        # Se relee el proveedor para no confiar en datos que pudieron
        # cambiar entre la respuesta y la ejecución de la tarea.
        from app.crud import proveedores as crud  # import local: evita un ciclo al arrancar

        proveedor = crud.obtener_por_id(sesion, proveedor_id)

        enviado = enviar_correo(
            destino=correo,
            asunto=f"Dulce Esencia Pastelería — alta como proveedor ({razon_social})",
            cuerpo=(
                f"Hola, equipo de {proveedor.razon_social}:\n\n"
                "Quedaron registrados como proveedor de Dulce Esencia Pastelería con estas "
                "condiciones comerciales:\n"
                f"  · NIT: {proveedor.nit}\n"
                f"  · Categoría: {proveedor.categoria.value}\n"
                f"  · Plazo de pago: {proveedor.dias_credito} días\n"
                f"  · Cupo de crédito: {proveedor.cupo_credito} COP\n\n"
                "Si algún dato no corresponde, respondan este correo antes de la primera "
                "orden de compra.\n\n"
                "Área de Compras — Dulce Esencia Pastelería"
            ),
        )
        logger.info(
            "alta_proveedor_notificada id=%s correo=%s enviado_por_smtp=%s",
            proveedor_id,
            correo,
            enviado,
        )
    except Exception:  # noqa: BLE001 - regla 3: la tarea nunca propaga
        logger.exception("fallo_notificando_alta_proveedor id=%s", proveedor_id)
    finally:
        sesion.close()
