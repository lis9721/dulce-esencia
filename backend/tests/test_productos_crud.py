"""
Pruebas del CRUD completo de /api/productos (criterios 1.3 y 9 de la matriz):
crear, listar, consultar, actualizar y eliminar, con validación (422),
conflictos (409), inexistentes (404) y permisos por rol (401/403).
"""

PRODUCTO = {
    "titulo": "Torta de Chocolate Intenso",
    "descripcion": "Bizcocho húmedo de cacao con ganache de chocolate semiamargo.",
    "imagen": "torta-chocolate.jpg",
    "precio": 85000,
    "stock": 12,
    "sku": "TOR-001",
    "familia": "tortas",
    "peso_g": 1200,
    "activo": True,
}


def _crear(cliente, headers, **cambios):
    return cliente.post("/api/productos", json={**PRODUCTO, **cambios}, headers=headers)


class TestCrear:
    def test_empleado_crea_producto_201(self, cliente, crear_usuario, token_de):
        crear_usuario("emp@example.com", rol="empleado")
        r = _crear(cliente, token_de("emp@example.com"))
        assert r.status_code == 201, r.text
        assert r.json()["id"] > 0 and r.json()["titulo"] == "Torta de Chocolate Intenso"

    def test_sin_token_401(self, cliente):
        assert cliente.post("/api/productos", json=PRODUCTO).status_code == 401

    def test_cliente_403(self, cliente, crear_usuario, token_de):
        crear_usuario("cli@example.com", rol="cliente")
        assert _crear(cliente, token_de("cli@example.com")).status_code == 403

    def test_datos_invalidos_422(self, cliente, crear_usuario, token_de):
        crear_usuario("adm@example.com", rol="admin")
        h = token_de("adm@example.com")
        assert _crear(cliente, h, precio=-5).status_code == 422
        assert _crear(cliente, h, titulo="ab").status_code == 422
        assert _crear(cliente, h, familia="inexistente").status_code == 422
        assert _crear(cliente, h, imagen="archivo.exe").status_code == 422

    def test_sku_duplicado_409(self, cliente, crear_usuario, token_de):
        crear_usuario("adm@example.com", rol="admin")
        h = token_de("adm@example.com")
        assert _crear(cliente, h).status_code == 201
        assert _crear(cliente, h, titulo="Otro nombre").status_code == 409


class TestLeer:
    def test_listado_publico_paginado(self, cliente, crear_usuario, token_de):
        crear_usuario("adm@example.com", rol="admin")
        h = token_de("adm@example.com")
        for i in range(3):
            _crear(cliente, h, titulo=f"Torta {i}", sku=f"SKU-{i}")
        r = cliente.get("/api/productos?page=1&limit=2")  # sin token: es público
        assert r.status_code == 200
        cuerpo = r.json()
        assert len(cuerpo["datos"]) == 2
        assert cuerpo["paginacion"]["total"] == 3

    def test_parametro_de_consulta_invalido_422(self, cliente):
        assert cliente.get("/api/productos?page=0").status_code == 422
        assert cliente.get("/api/productos?familia=inventada").status_code == 422

    def test_consultar_por_id_y_404(self, cliente, crear_usuario, token_de):
        crear_usuario("adm@example.com", rol="admin")
        creado = _crear(cliente, token_de("adm@example.com")).json()
        assert cliente.get(f"/api/productos/{creado['id']}").json()["sku"] == "TOR-001"
        assert cliente.get("/api/productos/999999").status_code == 404
        assert cliente.get("/api/productos/no-es-un-numero").status_code == 422

    def test_busqueda_no_trata_el_porcentaje_como_comodin(self, cliente, crear_usuario, token_de):
        crear_usuario("adm@example.com", rol="admin")
        h = token_de("adm@example.com")
        _crear(cliente, h, titulo="Torta Rosa Vintage", sku="R-1")
        assert len(cliente.get("/api/productos?buscar=rosa").json()["datos"]) == 1
        assert cliente.get("/api/productos?buscar=%25").json()["datos"] == []  # "%" literal, no "todo"


class TestActualizarYEliminar:
    def test_actualizar_put(self, cliente, crear_usuario, token_de):
        crear_usuario("emp@example.com", rol="empleado")
        h = token_de("emp@example.com")
        creado = _crear(cliente, h).json()
        r = cliente.put(f"/api/productos/{creado['id']}", json={**PRODUCTO, "precio": 199000}, headers=h)
        assert r.status_code == 200 and r.json()["precio"] == 199000
        assert cliente.put("/api/productos/999999", json=PRODUCTO, headers=h).status_code == 404

    def test_despublicar_lo_saca_del_catalogo_publico(self, cliente, crear_usuario, token_de):
        crear_usuario("emp@example.com", rol="empleado")
        h = token_de("emp@example.com")
        creado = _crear(cliente, h).json()
        r = cliente.patch(f"/api/productos/{creado['id']}/estado?activo=false", headers=h)
        assert r.status_code == 200
        assert cliente.get("/api/productos").json()["datos"] == []
        assert len(cliente.get("/api/productos/admin/todos", headers=h).json()["datos"]) == 1

    def test_solo_admin_elimina(self, cliente, crear_usuario, token_de):
        crear_usuario("emp@example.com", rol="empleado")
        crear_usuario("adm@example.com", rol="admin")
        creado = _crear(cliente, token_de("emp@example.com")).json()
        assert cliente.delete(f"/api/productos/{creado['id']}", headers=token_de("emp@example.com")).status_code == 403
        assert cliente.delete(f"/api/productos/{creado['id']}", headers=token_de("adm@example.com")).status_code == 200
        assert cliente.get(f"/api/productos/{creado['id']}").status_code == 404
        assert cliente.delete(f"/api/productos/{creado['id']}", headers=token_de("adm@example.com")).status_code == 404


def test_id_de_ruta_menor_a_1_da_422_por_Path_ge_1(cliente):
    assert cliente.get("/api/productos/0").status_code == 422
    assert cliente.get("/api/productos/-5").status_code == 422
