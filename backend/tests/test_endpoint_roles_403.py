"""
Prueba automática de la Prioridad 6 (protección de endpoints y control
de roles): recorre la matriz de `backend/docs/matriz-acceso-roles.md` y
verifica, contra un servidor REAL corriendo (no un mock), que:

  1. Sin token  -> 401
  2. Con token de un rol NO permitido -> 403
  3. Con token de un rol permitido -> nunca 403 (puede dar 404 si el id
     de prueba no existe; eso es correcto, ver nota más abajo)

No agrega dependencias nuevas al proyecto: usa solo `unittest` y
`urllib` de la librería estándar de Python, así que corre igual con
`python -m unittest` o con `pytest` (pytest reconoce clases
`unittest.TestCase` sin configuración extra).

--------------------------------------------------------------------
Cómo correrlo
--------------------------------------------------------------------
1. Levanta el backend:  uvicorn app.main:app --reload
2. Ten tres cuentas ya creadas y verificadas, una por rol
   (ver backend/docs/guia-prueba-manual-403.md, sección 0).
3. Exporta las credenciales de esas tres cuentas:

     export TEST_ADMIN_CORREO="admin@correo.com"
     export TEST_ADMIN_PASSWORD="..."
     export TEST_EMPLEADO_CORREO="empleado@correo.com"
     export TEST_EMPLEADO_PASSWORD="..."
     export TEST_CLIENTE_CORREO="cliente@correo.com"
     export TEST_CLIENTE_PASSWORD="..."
     export BASE_URL="http://localhost:8000"   # opcional, es el default

4. Corre:  python -m unittest backend/tests/test_endpoint_roles_403.py -v
   (o, si tienes pytest instalado:  pytest backend/tests/test_endpoint_roles_403.py -v)

Si falta alguna credencial de rol, las pruebas de ESE rol se saltan
(no fallan) con un mensaje explicando qué variable exportar.
"""

from __future__ import annotations

import json
import os
import unittest
import urllib.error
import urllib.request
from dataclasses import dataclass, field

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")

# ID que casi seguro no existe, para probar el chequeo de ROL de forma
# aislada, sin depender de que exista un registro real (ver nota en
# guia-prueba-manual-403.md, sección 3).
ID_INEXISTENTE = 999999999


def _login(correo: str, password: str) -> str | None:
    body = json.dumps({"correo": correo, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("access_token")
    except urllib.error.HTTPError:
        return None
    except urllib.error.URLError as error:
        raise RuntimeError(
            f"No se pudo conectar a {BASE_URL}. ¿Está el backend corriendo "
            f"(uvicorn app.main:app --reload)? Detalle: {error}"
        ) from error


def _token_para(rol: str) -> str | None:
    correo = os.environ.get(f"TEST_{rol.upper()}_CORREO")
    password = os.environ.get(f"TEST_{rol.upper()}_PASSWORD")
    if not correo or not password:
        return None
    return _login(correo, password)


def _request(method: str, path: str, token: str | None = None, body: dict | None = None) -> int:
    """Devuelve solo el status code — es lo único que nos interesa para estas pruebas de permisos."""
    data = json.dumps(body).encode("utf-8") if body is not None else b"{}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as error:
        return error.code


@dataclass
class Endpoint:
    metodo: str
    ruta: str
    roles_permitidos: tuple[str, ...]  # () = pública, ("*",) = cualquier rol autenticado
    body: dict = field(default_factory=dict)


# Matriz replicada de backend/docs/matriz-acceso-roles.md.
# Los endpoints con {id} usan ID_INEXISTENTE — ver nota en la sección 3
# de guia-prueba-manual-403.md sobre por qué eso sigue siendo válido
# para probar el chequeo de ROL.
ENDPOINTS_PROTEGIDOS: list[Endpoint] = [
    Endpoint("GET", "/api/usuarios", ("admin", "empleado")),
    Endpoint("GET", f"/api/usuarios/{ID_INEXISTENTE}", ("admin", "empleado")),
    Endpoint("PUT", f"/api/usuarios/{ID_INEXISTENTE}", ("admin",)),
    Endpoint("PATCH", f"/api/usuarios/{ID_INEXISTENTE}/estado", ("admin",), body={"activo": True}),
    Endpoint("DELETE", f"/api/usuarios/{ID_INEXISTENTE}", ("admin",)),
    Endpoint("GET", "/api/productos/admin/todos", ("admin", "empleado")),
    Endpoint("POST", "/api/productos", ("admin", "empleado")),
    Endpoint("PUT", f"/api/productos/{ID_INEXISTENTE}", ("admin", "empleado")),
    Endpoint("PATCH", f"/api/productos/{ID_INEXISTENTE}/estado?activo=true", ("admin", "empleado")),
    Endpoint("DELETE", f"/api/productos/{ID_INEXISTENTE}", ("admin",)),
    Endpoint("GET", "/api/servicios/admin/todos", ("admin", "empleado")),
    Endpoint("POST", "/api/servicios", ("admin", "empleado")),
    Endpoint("PUT", f"/api/servicios/{ID_INEXISTENTE}", ("admin", "empleado")),
    Endpoint("PATCH", f"/api/servicios/{ID_INEXISTENTE}/estado?activo=true", ("admin", "empleado")),
    Endpoint("DELETE", f"/api/servicios/{ID_INEXISTENTE}", ("admin",)),
    Endpoint("GET", "/api/roles", ("admin",)),
    Endpoint("GET", f"/api/roles/{ID_INEXISTENTE}", ("admin",)),
    Endpoint("GET", "/api/cupones", ("admin", "empleado")),
    Endpoint("GET", f"/api/cupones/{ID_INEXISTENTE}", ("admin", "empleado")),
    Endpoint("POST", "/api/cupones", ("admin",)),
    Endpoint("PUT", f"/api/cupones/{ID_INEXISTENTE}", ("admin",)),
    Endpoint("PATCH", f"/api/cupones/{ID_INEXISTENTE}/estado", ("admin",), body={"activo": True}),
    Endpoint("DELETE", f"/api/cupones/{ID_INEXISTENTE}", ("admin",)),
    Endpoint("PATCH", f"/api/pedidos/{ID_INEXISTENTE}/estado", ("admin", "empleado"), body={"estado": "pagado"}),
    Endpoint("GET", "/api/contacto", ("admin", "empleado")),
    Endpoint("GET", f"/api/contacto/{ID_INEXISTENTE}", ("admin", "empleado")),
    Endpoint("DELETE", f"/api/contacto/{ID_INEXISTENTE}", ("admin", "empleado")),
]

TODOS_LOS_ROLES = ("cliente", "empleado", "admin")


class PruebaProteccionEndpoints(unittest.TestCase):
    tokens: dict[str, str | None] = {}

    @classmethod
    def setUpClass(cls):
        # Esta prueba necesita un servidor REAL corriendo. Si no hay uno
        # (por ejemplo en el CI de GitHub), se SALTA en vez de fallar.
        try:
            urllib.request.urlopen(f"{BASE_URL}/", timeout=3)
        except (urllib.error.URLError, OSError):
            raise unittest.SkipTest(
                f"No hay servidor en {BASE_URL}: esta prueba es de extremo a extremo "
                "(uvicorn app.main:app). Las pruebas de roles con SQLite están en tests/test_auth.py."
            ) from None
        cls.tokens = {rol: _token_para(rol) for rol in TODOS_LOS_ROLES}

    def test_sin_token_da_401_en_todos_los_endpoints_protegidos(self):
        for ep in ENDPOINTS_PROTEGIDOS:
            with self.subTest(endpoint=f"{ep.metodo} {ep.ruta}"):
                status = _request(ep.metodo, ep.ruta, token=None, body=ep.body)
                self.assertEqual(
                    status,
                    401,
                    f"{ep.metodo} {ep.ruta} sin token debería dar 401, dio {status}.",
                )

    def test_rol_no_permitido_da_403(self):
        algun_token_disponible = False
        for ep in ENDPOINTS_PROTEGIDOS:
            for rol in TODOS_LOS_ROLES:
                if rol in ep.roles_permitidos:
                    continue  # este rol SÍ tiene permiso, no aplica aquí
                token = self.tokens.get(rol)
                if not token:
                    continue
                algun_token_disponible = True
                with self.subTest(endpoint=f"{ep.metodo} {ep.ruta}", rol=rol):
                    status = _request(ep.metodo, ep.ruta, token=token, body=ep.body)
                    self.assertEqual(
                        status,
                        403,
                        f"{ep.metodo} {ep.ruta} con rol '{rol}' (no permitido) "
                        f"debería dar 403, dio {status}.",
                    )
        if not algun_token_disponible:
            self.skipTest(
                "No hay ninguna credencial de prueba configurada. Exporta "
                "TEST_ADMIN_CORREO/TEST_ADMIN_PASSWORD (y lo mismo para "
                "EMPLEADO/CLIENTE) antes de correr este archivo — ver el "
                "docstring del módulo."
            )

    def test_rol_permitido_nunca_da_403(self):
        algun_token_disponible = False
        for ep in ENDPOINTS_PROTEGIDOS:
            for rol in ep.roles_permitidos:
                token = self.tokens.get(rol)
                if not token:
                    continue
                algun_token_disponible = True
                with self.subTest(endpoint=f"{ep.metodo} {ep.ruta}", rol=rol):
                    status = _request(ep.metodo, ep.ruta, token=token, body=ep.body)
                    self.assertNotEqual(
                        status,
                        403,
                        f"{ep.metodo} {ep.ruta} con rol '{rol}' (SÍ permitido) "
                        f"dio 403 — la ruta quedó sobre-restringida.",
                    )
        if not algun_token_disponible:
            self.skipTest(
                "No hay ninguna credencial de prueba configurada — ver el "
                "docstring del módulo."
            )


if __name__ == "__main__":
    unittest.main()
