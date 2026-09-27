"""
Paso de "migración" que corre backend/.github workflow deploy.yml ANTES
de publicar el código nuevo en Vercel (nunca después: si esto falla, el
job de deploy se detiene y no se despliega nada).

Este proyecto no usa Alembic (ver docs/DEPLOY.md — "Migraciones" para el
porqué): la sincronización de esquema vive en app.database.sincronizar_esquema()
y normalmente corre en el lifespan de la app. En Vercel eso se desactiva
(SKIP_SCHEMA_SYNC=true) para no repetirla en cada cold start, y en su
lugar se ejecuta UNA sola vez aquí, contra la base de datos real
(producción o preview, según qué variables de entorno reciba el job),
antes de que el nuevo código empiece a servir tráfico.

Uso (variables ya deben estar en el entorno del job — ver deploy.yml):
    python -m scripts.sync_schema
"""

import sys

from app.database import sincronizar_esquema, verificar_conexion


def main() -> int:
    print("Verificando conexión con la base de datos antes de sincronizar el esquema...")
    if not verificar_conexion():
        print("ABORTADO: no se pudo conectar a la base de datos. El deploy no continúa.")
        return 1

    try:
        sincronizar_esquema()
    except Exception as error:  # noqa: BLE001 - cualquier falla aquí debe abortar el deploy
        print(f"ABORTADO: la sincronización de esquema falló: {error}")
        return 1

    print("Esquema sincronizado correctamente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
