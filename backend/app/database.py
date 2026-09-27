"""
Conexión a MySQL/MariaDB (XAMPP) vía SQLAlchemy.

Equivalente en Python a backend-node/config/db.js: crea un pool de
conexiones (pool_pre_ping evita usar conexiones muertas, igual que el
`ping()` que hacía verificarConexion() en Node) y expone una sesión por
request a través de la dependencia get_db().
"""

import enum
import ssl as ssl_module
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()


def _connect_args() -> dict:
    """
    Único punto donde se arma la configuración TLS de la conexión a MySQL.

    TiDB Cloud Starter usa certificados públicamente confiables (misma
    cadena que un navegador ya reconoce), así que basta con pedirle a
    PyMySQL un contexto SSL "de fábrica" (ssl.create_default_context())
    para obtener verificación de identidad completa — no hace falta
    descargar ni guardar ningún CA propio como secreto.

    En local (XAMPP, DB_SSL=false) se devuelve un dict vacío: sin TLS,
    como siempre. Este es el único lugar de la aplicación que decide
    esto — si en el futuro se agrega Alembic, su env.py debe importar
    esta misma función en vez de reconstruir la lógica.
    """
    if not settings.DB_SSL:
        return {}
    return {"ssl": ssl_module.create_default_context()}


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=0,
    echo=False,
    connect_args=_connect_args(),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos ORM (app/models/)."""

    pass


def get_db() -> Generator:
    """Dependencia de FastAPI: entrega una sesión y la cierra al terminar el request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verificar_conexion() -> bool:
    """
    Prueba la conexión al arrancar el servidor y avisa en consola.
    Equivalente a verificarConexion() en config/db.js.
    """
    try:
        with engine.connect() as conexion:
            conexion.execute(text("SELECT 1"))
        print(
            f'Conectado a MySQL en {settings.DB_HOST}:{settings.DB_PORT} '
            f'(base de datos "{settings.DB_NAME}")'
        )
        return True
    except Exception as error:  # noqa: BLE001 - se registra y se continúa, igual que en Node
        print(f"No se pudo conectar a MySQL/XAMPP: {error}")
        print(
            "Verifica que Apache/MySQL estén iniciados en el panel de XAMPP y que la "
            "base de datos exista (ver backend-node/database/schema.sql)."
        )
        return False


_ROLES_BASE = [
    ("admin", "Control total: usuarios, productos, servicios, pedidos, cupones y mensajes."),
    ("empleado", "Gestión operativa de productos, servicios, usuarios y pedidos, sin cupones."),
    ("cliente", "Acceso a su propio perfil, carrito, pedidos y catálogo público."),
]


def _sembrar_roles_base() -> None:
    """
    Garantiza que existan las filas base de `roles` (admin/empleado/cliente).

    Desde la normalización de `usuarios.rol` (ahora FK a `roles.nombre`,
    ver docs/NORMALIZACION-BD.md), esto ya no es solo un dato bonito para
    el panel de administración: sin estas filas, el PRIMER INSERT de un
    usuario en una base de datos nueva creada solo con create_all() (sin
    correr database/schema_fastapi.sql a mano) fallaría por violar la
    llave foránea. INSERT IGNORE hace que sea seguro llamarlo en cada
    arranque, incluso si `schema_fastapi.sql` ya sembró estas mismas filas.
    """
    with engine.begin() as conexion:
        for nombre, descripcion in _ROLES_BASE:
            conexion.execute(
                text("INSERT IGNORE INTO roles (nombre, descripcion) VALUES (:nombre, :descripcion)"),
                {"nombre": nombre, "descripcion": descripcion},
            )


def sincronizar_esquema() -> None:
    """
    Se ejecuta una vez al arrancar el servidor (ver lifespan en app/main.py) y hace
    tres cosas para que los modelos de SQLAlchemy (app/models/) y la base de datos
    física en MySQL/XAMPP nunca queden desincronizados:

    1. `Base.metadata.create_all(bind=engine)`: crea cualquier tabla que exista en
       los modelos pero todavía no en la base de datos (por ejemplo, en una
       instalación nueva donde nunca se corrió database/schema.sql a mano).

    2. `_sembrar_roles_base()`: siembra admin/empleado/cliente en `roles` si
       faltan. Necesario para que `usuarios.rol` (FK a `roles.nombre`) pueda
       aceptar el primer usuario en una base de datos recién creada.

    3. Para las tablas que SÍ existen, compara sus columnas contra el modelo y
       agrega (con ALTER TABLE ... ADD COLUMN) cualquier columna que falte. Esto
       resuelve el caso real de este proyecto: la tabla `productos` se creó antes
       de agregar `familia` y `peso_g` a app/models/producto.py, así que la
       base de datos física se quedó desactualizada aunque database/schema.sql sí
       ya las incluyera. create_all() por sí solo NO agrega columnas a una tabla
       que ya existe (solo crea tablas nuevas), por eso hace falta este paso
       adicional.

    Las columnas nuevas se agregan siempre como NULL (independientemente de si el
    modelo las define como NOT NULL) para no romper filas ya existentes en la
    tabla; si el campo debe quedar obligatorio, se ajusta manualmente después de
    revisar/completar los datos. Cualquier error al agregar una columna puntual
    se registra en consola pero no detiene el arranque del servidor.
    """
    from app import models  # noqa: F401 - registra todos los modelos en Base.metadata

    Base.metadata.create_all(bind=engine)
    _sembrar_roles_base()

    inspector = inspect(engine)
    tablas_existentes = set(inspector.get_table_names())

    for tabla in Base.metadata.sorted_tables:
        if tabla.name not in tablas_existentes:
            continue  # ya se creó completa en el create_all() de arriba

        columnas_existentes = {columna["name"] for columna in inspector.get_columns(tabla.name)}

        for columna in tabla.columns:
            if columna.name in columnas_existentes:
                continue
            try:
                tipo_sql = columna.type.compile(dialect=engine.dialect)
                with engine.begin() as conexion:
                    conexion.execute(
                        text(f"ALTER TABLE `{tabla.name}` ADD COLUMN `{columna.name}` {tipo_sql} NULL")
                    )
                print(
                    f'Columna faltante agregada automáticamente: "{tabla.name}.{columna.name}" '
                    f"({tipo_sql})."
                )

                # Si el modelo define un valor por defecto simple (número, texto o
                # enum) para esta columna, rellena con él las filas ya existentes:
                # la columna queda NULL tras el ALTER de arriba, pero si el
                # esquema de salida (Pydantic) exige el campo como obligatorio
                # (p. ej. Producto.familia), dejar NULL rompería la serialización
                # de las filas antiguas en los endpoints GET.
                valor_por_defecto = getattr(columna.default, "arg", None)
                if isinstance(valor_por_defecto, enum.Enum):
                    valor_por_defecto = valor_por_defecto.value
                if isinstance(valor_por_defecto, (int, float, str)):
                    with engine.begin() as conexion:
                        conexion.execute(
                            text(
                                f"UPDATE `{tabla.name}` SET `{columna.name}` = :valor "
                                f"WHERE `{columna.name}` IS NULL"
                            ),
                            {"valor": valor_por_defecto},
                        )
                    print(
                        f'Filas existentes de "{tabla.name}.{columna.name}" rellenadas '
                        f'con el valor por defecto del modelo: "{valor_por_defecto}".'
                    )
            except Exception as error:  # noqa: BLE001 - se registra y se continúa
                print(
                    f'No se pudo agregar la columna "{tabla.name}.{columna.name}" automáticamente: '
                    f"{error}"
                )
