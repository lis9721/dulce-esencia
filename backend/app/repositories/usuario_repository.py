"""
repositories/usuario_repository.py

Acceso a datos de `usuarios` mediante CONSULTAS PREPARADAS (prepared
statements).

¿Qué es una consulta preparada?
  El texto SQL se define UNA vez con "huecos" (parámetros) y los valores
  que escribe el usuario se envían por separado, ya sea como parámetro
  ligado o "bind parameter". El motor de base de datos nunca interpreta
  esos valores como código SQL — solo como datos.

  Vulnerable (concatenación):   "... WHERE correo = '" + correo + "'"
  Con consulta preparada:       "... WHERE correo = %(correo)s"   + {"correo": correo}

  Por eso la cadena  ' OR 1=1 --  llega a la base de datos como un
  correo literal (que no existe) y NO como parte de la condición.

Equivalente en SQL "de libro" a:

    SELECT * FROM usuarios WHERE correo = ?   -- SET 1 = correo

En SQLAlchemy el "?" se escribe con `bindparam("correo")`. Nota: aquí NO
se compara la contraseña dentro del SQL (`AND clave = ?`): en Dulce Esencia
las contraseñas se guardan como hash bcrypt con sal y se verifican en
Python con `verificar_hash()` (app/auth.py). Eso es más seguro que
comparar la clave en la consulta, porque el SQL nunca toca la contraseña
en texto plano.
"""

from sqlalchemy import bindparam, select
from sqlalchemy.orm import Session

from app.models.usuario import Usuario

# Sentencia definida una sola vez (a nivel de módulo) con un parámetro
# nombrado. Los valores se pasan aparte en `db.execute(..., {...})`.
_SELECT_USUARIO_POR_CORREO = select(Usuario).where(Usuario.correo == bindparam("correo"))


def buscar_por_correo(db: Session, correo: str) -> Usuario | None:
    """Devuelve el usuario con ese correo (o None) usando un parámetro ligado."""
    return db.execute(_SELECT_USUARIO_POR_CORREO, {"correo": correo}).scalars().first()


def sql_de_busqueda_por_correo(dialecto=None) -> str:
    """
    Texto SQL de la consulta con sus marcadores de parámetro. Sirve como
    EVIDENCIA para la sustentación y para las pruebas: se ve que el
    valor del usuario nunca forma parte del texto.
    """
    return str(_SELECT_USUARIO_POR_CORREO.compile(dialect=dialecto))
