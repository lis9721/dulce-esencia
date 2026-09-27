"""
Pruebas del módulo de proveedores (criterios 62, 63, 64 y 65).

  * 62 — corren contra SQLite en memoria (fixtures de `conftest.py`),
         nunca contra la MySQL de desarrollo: `pytest` funciona sin
         XAMPP levantado.
  * 63 — la sesión y el usuario se inyectan con `dependency_overrides`
         y el propio `conftest` los limpia al terminar cada prueba.
  * 64 — hay camino correcto Y una prueba por cada error de negocio del
         dominio: 404, 409 de NIT duplicado, 409 por productos
         asociados, 409 de transición de estado inválida, 422 de reglas
         propias (DV del NIT, crédito incoherente, correo personal) y
         403 por rol.
  * 65 — el envío de correo de la tarea en segundo plano se sustituye
         por un doble (`monkeypatch`), así ninguna prueba abre un
         socket SMTP.

Correr solo este archivo:
    pytest tests/test_proveedores.py -v
"""

import pytest

from app.models.producto import FamiliaProducto, Producto

RUTA = "/api/proveedores"

PROVEEDOR_VALIDO = {
    "razon_social": "Molinos y Harinas del Valle S.A.S.",
    "nit": "900123456-8",  # DV 8 = el que calcula el algoritmo DIAN para 900123456
    "categoria": "materias_primas",
    "contacto_nombre": "Marcela Ríos",
    "correo": "compras@molinosdelvalle.com",
    "telefono": "+57 (602) 322-1144",
    "ciudad": "Palmira",
    "direccion": "Zona Industrial, Cl 30 # 10-15",
    "sitio_web": "https://molinosdelvalle.com",
    "dias_credito": 30,
    "cupo_credito": "12000000.00",
}


@pytest.fixture(autouse=True)
def _sin_correos_reales(monkeypatch):
    """
    Doble del servicio externo de correo (criterio 65): la tarea en
    segundo plano de POST /api/proveedores llama a `enviar_correo`, que
    aquí queda sustituido por una función que no hace nada.
    """
    monkeypatch.setattr("app.services.notificaciones.enviar_correo", lambda **_: False)
    monkeypatch.setattr("app.services.proveedores.enviar_correo", lambda **_: False)


@pytest.fixture()
def admin(cliente, crear_usuario, token_de):
    crear_usuario(correo="admin@test.com", rol="admin")
    return token_de("admin@test.com")


@pytest.fixture()
def empleado(cliente, crear_usuario, token_de):
    crear_usuario(correo="empleado@test.com", rol="empleado")
    return token_de("empleado@test.com")


@pytest.fixture()
def comprador(cliente, crear_usuario, token_de):
    crear_usuario(correo="comprador@test.com", rol="cliente")
    return token_de("comprador@test.com")


def crear_proveedor(cliente, cabeceras, **sobrescribir):
    cuerpo = {**PROVEEDOR_VALIDO, **sobrescribir}
    return cliente.post(RUTA, json=cuerpo, headers=cabeceras)


# ======================================================================
# Camino correcto
# ======================================================================


def test_crear_proveedor_responde_201_con_el_recurso(cliente, admin):
    respuesta = crear_proveedor(cliente, admin)

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["id"] > 0
    assert cuerpo["estado"] == "activo"          # lo decide el servidor
    assert cuerpo["telefono"] == "+576023221144"  # normalizado por el validador
    assert cuerpo["total_productos"] == 0


def test_listado_pagina_y_filtra(cliente, admin):
    crear_proveedor(cliente, admin)
    crear_proveedor(
        cliente,
        admin,
        razon_social="Lácteos y Huevos La Pradera S.A.",
        nit="800245619-2",
        categoria="lacteos",
        correo="pedidos@lacteoslapradera.com",
        ciudad="Zipaquirá",
        dias_credito=0,
        cupo_credito="0",
    )

    todos = cliente.get(f"{RUTA}?page=1&limit=10", headers=admin).json()
    assert todos["paginacion"]["total"] == 2

    solo_lacteos = cliente.get(f"{RUTA}?categoria=lacteos", headers=admin).json()
    assert [p["ciudad"] for p in solo_lacteos["datos"]] == ["Zipaquirá"]

    por_texto = cliente.get(f"{RUTA}?buscar=Molinos", headers=admin).json()
    assert por_texto["paginacion"]["total"] == 1

    por_ciudad = cliente.get(f"{RUTA}?ciudad=palmi", headers=admin).json()
    assert por_ciudad["paginacion"]["total"] == 1


def test_patch_no_sobrescribe_con_nulos_los_campos_omitidos(cliente, admin):
    creado = crear_proveedor(cliente, admin).json()

    respuesta = cliente.patch(f"{RUTA}/{creado['id']}", json={"ciudad": "Medellín"}, headers=admin)

    assert respuesta.status_code == 200
    actualizado = respuesta.json()
    assert actualizado["ciudad"] == "Medellín"
    # Campos NO enviados: intactos, no en null (criterio 15).
    assert actualizado["sitio_web"] == creado["sitio_web"]
    assert actualizado["direccion"] == creado["direccion"]
    assert actualizado["dias_credito"] == creado["dias_credito"]


def test_put_reemplaza_el_recurso_completo(cliente, admin):
    creado = crear_proveedor(cliente, admin).json()
    cuerpo = {**PROVEEDOR_VALIDO, "ciudad": "Cartagena", "sitio_web": None,
              "dias_credito": 0, "cupo_credito": "0"}

    respuesta = cliente.put(f"{RUTA}/{creado['id']}", json=cuerpo, headers=admin)

    assert respuesta.status_code == 200
    assert respuesta.json()["ciudad"] == "Cartagena"
    assert respuesta.json()["sitio_web"] is None


def test_delete_responde_204_sin_cuerpo(cliente, admin):
    creado = crear_proveedor(cliente, admin).json()

    respuesta = cliente.delete(f"{RUTA}/{creado['id']}", headers=admin)

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    assert cliente.get(f"{RUTA}/{creado['id']}", headers=admin).status_code == 404


def test_suspension_desactiva_el_catalogo_del_proveedor(cliente, admin, db_session):
    creado = crear_proveedor(cliente, admin).json()
    db_session.add(
        Producto(
            titulo="Torta de Chocolate Intenso",
            descripcion="Bizcocho húmedo de cacao con ganache de chocolate.",
            imagen="img1.jpg",
            orden=1,
            precio=85000,
            stock=10,
            sku="TOR-001",
            familia=FamiliaProducto.tortas,
            activo=True,
            proveedor_id=creado["id"],
        )
    )
    db_session.commit()

    respuesta = cliente.post(
        f"{RUTA}/{creado['id']}/suspensiones",
        json={"motivo": "Tres entregas consecutivas fuera de plazo."},
        headers=admin,
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "suspendido"

    producto = db_session.query(Producto).filter_by(sku="TOR-001").one()
    db_session.refresh(producto)
    assert producto.activo is False  # las dos escrituras ocurrieron juntas


def test_reactivacion_limpia_el_motivo(cliente, admin):
    creado = crear_proveedor(cliente, admin).json()
    cliente.post(
        f"{RUTA}/{creado['id']}/suspensiones",
        json={"motivo": "Incumplimiento reiterado de entregas."},
        headers=admin,
    )

    respuesta = cliente.post(f"{RUTA}/{creado['id']}/reactivaciones", headers=admin)

    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "activo"
    assert respuesta.json()["motivo_suspension"] is None


# ======================================================================
# Errores de negocio del dominio
# ======================================================================


def test_proveedor_inexistente_responde_404_con_mensaje_claro(cliente, admin):
    respuesta = cliente.get(f"{RUTA}/9999", headers=admin)

    assert respuesta.status_code == 404
    cuerpo = respuesta.json()
    assert cuerpo["error"]["codigo"] == "PROVEEDOR_NO_ENCONTRADO"
    assert "9999" in cuerpo["detail"]


def test_nit_duplicado_responde_409_no_400_ni_500(cliente, admin):
    crear_proveedor(cliente, admin)

    respuesta = crear_proveedor(cliente, admin, razon_social="Otra Razón Social S.A.S.")

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["codigo"] == "PROVEEDOR_NIT_DUPLICADO"


def test_no_se_puede_eliminar_un_proveedor_con_productos(cliente, admin, db_session):
    creado = crear_proveedor(cliente, admin).json()
    db_session.add(
        Producto(
            titulo="Cupcakes de Vainilla x6",
            descripcion="Seis cupcakes de vainilla con buttercream cremoso.",
            imagen="img3.jpg",
            orden=1,
            precio=36000,
            stock=5,
            sku="CUP-001",
            familia=FamiliaProducto.cupcakes,
            proveedor_id=creado["id"],
        )
    )
    db_session.commit()

    respuesta = cliente.delete(f"{RUTA}/{creado['id']}", headers=admin)

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["codigo"] == "PROVEEDOR_CON_PRODUCTOS"


def test_suspender_dos_veces_responde_409(cliente, admin):
    creado = crear_proveedor(cliente, admin).json()
    cuerpo = {"motivo": "Retrasos reiterados en las entregas."}
    cliente.post(f"{RUTA}/{creado['id']}/suspensiones", json=cuerpo, headers=admin)

    respuesta = cliente.post(f"{RUTA}/{creado['id']}/suspensiones", json=cuerpo, headers=admin)

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["codigo"] == "PROVEEDOR_TRANSICION_INVALIDA"


def test_reactivar_un_proveedor_activo_responde_409(cliente, admin):
    creado = crear_proveedor(cliente, admin).json()

    respuesta = cliente.post(f"{RUTA}/{creado['id']}/reactivaciones", headers=admin)

    assert respuesta.status_code == 409


# ---------------------- Validación (422) ------------------------------


def test_nit_con_digito_de_verificacion_incorrecto_responde_422(cliente, admin):
    respuesta = crear_proveedor(cliente, admin, nit="900123456-3")

    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert cuerpo["error"]["codigo"] == "VALIDACION_FALLIDA"
    assert cuerpo["error"]["campos"][0]["campo"] == "nit"


def test_correo_personal_rechazado(cliente, admin):
    respuesta = crear_proveedor(cliente, admin, correo="marcela.rios@gmail.com")

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["campos"][0]["campo"] == "correo"


def test_credito_incoherente_rechazado(cliente, admin):
    """Plazo de pago sin cupo: lo detecta el model_validator (criterio 14)."""
    respuesta = crear_proveedor(cliente, admin, dias_credito=30, cupo_credito="0")

    assert respuesta.status_code == 422


def test_patch_que_dejaria_credito_incoherente_responde_422(cliente, admin):
    """La regla se evalúa contra lo YA guardado, en la capa crud."""
    creado = crear_proveedor(cliente, admin).json()  # 30 días / 12.000.000

    respuesta = cliente.patch(f"{RUTA}/{creado['id']}", json={"cupo_credito": "0"}, headers=admin)

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "REGLA_DE_NEGOCIO_VIOLADA"


def test_el_cliente_no_puede_enviar_campos_que_decide_el_servidor(cliente, admin):
    """`estado` no existe en el esquema de entrada: extra='forbid' (criterio 5)."""
    respuesta = crear_proveedor(cliente, admin)
    assert respuesta.status_code == 201

    respuesta_con_estado = cliente.post(
        RUTA,
        json={**PROVEEDOR_VALIDO, "nit": "830987654-3",
              "razon_social": "Cacao y Chocolates de Antioquia Ltda.", "estado": "suspendido"},
        headers=admin,
    )
    assert respuesta_con_estado.status_code == 422


def test_id_de_ruta_invalido_responde_422_sin_tocar_la_base(cliente, admin):
    assert cliente.get(f"{RUTA}/0", headers=admin).status_code == 422


# ------------------------ Autorización --------------------------------


def test_sin_token_responde_401_con_www_authenticate(cliente):
    respuesta = cliente.get(RUTA)

    assert respuesta.status_code == 401
    assert "WWW-Authenticate" in respuesta.headers


def test_un_cliente_no_puede_ver_proveedores(cliente, comprador):
    assert cliente.get(RUTA, headers=comprador).status_code == 403


def test_un_empleado_gestiona_pero_no_elimina(cliente, empleado):
    creado = crear_proveedor(cliente, empleado)
    assert creado.status_code == 201

    respuesta = cliente.delete(f"{RUTA}/{creado.json()['id']}", headers=empleado)
    assert respuesta.status_code == 403


# --------------------- Cabeceras de seguridad -------------------------


def test_las_respuestas_traen_cabeceras_de_seguridad(cliente, admin):
    respuesta = cliente.get(RUTA, headers=admin)

    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
    assert respuesta.headers["X-Frame-Options"] == "DENY"
    assert respuesta.headers["X-Request-ID"]
