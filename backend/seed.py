"""
Poblador de la base de datos con datos realistas del dominio
(criterio 54 de la lista de chequeo).

Uso, desde la carpeta `backend/` y con el entorno virtual activo:

    python seed.py            # inserta lo que falte (idempotente)
    python seed.py --reset    # borra lo sembrado antes y vuelve a insertarlo

Qué siembra
-----------
  * 3 usuarios (admin, empleado, cliente) ya verificados y con la
    contraseña hasheada con bcrypt — nunca en texto plano.
  * 6 proveedores reales del sector pastelero (materias primas, lácteos y
    huevos, empaques, insumos de decoración, logística refrigerada), uno de
    ellos suspendido, para que el filtro por estado del panel tenga algo
    que mostrar desde el primer arranque. Los NIT llevan su dígito de
    verificación DIAN correcto (el mismo que exige el esquema Pydantic).
  * 10 productos del catálogo (tortas, cupcakes, galletas, postres,
    hojaldres y panadería), ya asignados a su proveedor. Son los mismos
    10 (mismo orden, precio y stock) que muestra el carrusel del home en
    frontend/src/data/carouselData.js.

Es IDEMPOTENTE: se puede correr varias veces sin duplicar nada, porque
cada fila se busca antes por su clave natural (correo, NIT, SKU).

Credenciales sembradas (solo para desarrollo):
    admin@dulceesencia.com / Dulce2026!
    empleado@dulceesencia.com / Dulce2026!
    cliente@dulceesencia.com / Dulce2026!
"""

import argparse
from decimal import Decimal

from sqlalchemy import select

from app.auth import crear_hash
from app.database import SessionLocal, sincronizar_esquema

# Importa el paquete app.models completo (no solo los submódulos puntuales
# de abajo) para que TODOS los modelos ORM queden registrados en el
# registro de mapeadores de SQLAlchemy antes de la primera consulta. Sin
# esto, al correr `python seed.py` de forma aislada (sin pasar por
# app.main, que sí importa routes/resenas.py y de rebote
# app.models.resena), la relationship() "Resena" de Producto no se puede
# resolver y falla con
# `InvalidRequestError: ... failed to locate a name ('Resena')`.
import app.models  # noqa: F401
from app.models.producto import FamiliaProducto, Producto
from app.models.proveedor import CategoriaProveedor, EstadoProveedor, Proveedor
from app.models.usuario import Usuario

PASSWORD_DEMO = "Dulce2026!"

USUARIOS = [
    {
        "nombre": "Valentina", "apellido": "Ospina", "correo": "admin@dulceesencia.com",
        "rol": "admin", "tipo_documento": "CC", "numero_documento": "1010101010",
        "direccion": "Cra 43A # 1-50, Medellín", "telefono": "+573001112233",
    },
    {
        "nombre": "Andrés", "apellido": "Marín", "correo": "empleado@dulceesencia.com",
        "rol": "empleado", "tipo_documento": "CC", "numero_documento": "2020202020",
        "direccion": "Cl 10 # 40-20, Medellín", "telefono": "+573004445566",
    },
    {
        "nombre": "Laura", "apellido": "Gómez", "correo": "cliente@dulceesencia.com",
        "rol": "cliente", "tipo_documento": "CC", "numero_documento": "3030303030",
        "direccion": "Cl 30 # 65-10, Medellín", "telefono": "+573007778899",
    },
]

PROVEEDORES = [
    {
        "razon_social": "Molinos y Harinas del Valle S.A.S.", "nit": "900412873-6",
        "categoria": CategoriaProveedor.materias_primas, "contacto_nombre": "Marcela Ríos",
        "correo": "compras@molinosdelvalle.com", "telefono": "+576023221144",
        "ciudad": "Cali", "direccion": "Cra 8 # 25-40, Bodega 3",
        "sitio_web": "https://molinosdelvalle.com",
        "dias_credito": 30, "cupo_credito": Decimal("12000000.00"), "calificacion": Decimal("4.6"),
    },
    {
        "razon_social": "Cacao y Chocolates de Antioquia Ltda.", "nit": "890912345-9",
        "categoria": CategoriaProveedor.materias_primas, "contacto_nombre": "Julián Restrepo",
        "correo": "ventas@cacaoantioquia.co", "telefono": "+576044567890",
        "ciudad": "Medellín", "direccion": "Cl 12 Sur # 50-20",
        "sitio_web": "https://cacaoantioquia.co",
        "dias_credito": 45, "cupo_credito": Decimal("18000000.00"), "calificacion": Decimal("4.8"),
    },
    {
        "razon_social": "Lácteos y Huevos La Pradera S.A.", "nit": "800245619-2",
        "categoria": CategoriaProveedor.lacteos, "contacto_nombre": "Paola Cardona",
        "correo": "pedidos@lacteoslapradera.com", "telefono": "+576018334455",
        "ciudad": "Zipaquirá", "direccion": "Vereda El Empalme, Km 3 vía Cogua",
        "sitio_web": "https://lacteoslapradera.com",
        "dias_credito": 15, "cupo_credito": Decimal("9000000.00"), "calificacion": Decimal("4.7"),
    },
    {
        "razon_social": "Cajas y Empaques Dulce Pack S.A.S.", "nit": "901238764-1",
        "categoria": CategoriaProveedor.empaques, "contacto_nombre": "Camilo Betancur",
        "correo": "comercial@dulcepack.com", "telefono": "+576044448899",
        "ciudad": "Medellín", "direccion": "Cl 30 # 55-40, Itagüí",
        "sitio_web": None,
        "dias_credito": 0, "cupo_credito": Decimal("0"), "calificacion": Decimal("4.0"),
    },
    {
        "razon_social": "Decoraciones y Colorantes Nova S.A.S.", "nit": "900654321-0",
        "categoria": CategoriaProveedor.insumos, "contacto_nombre": "Sandra Peláez",
        "correo": "sandra.pelaez@decoracionesnova.com", "telefono": "+576046667788",
        "ciudad": "Medellín", "direccion": "Cra 50 # 12 Sur-30",
        "sitio_web": "https://decoracionesnova.com",
        "dias_credito": 30, "cupo_credito": Decimal("8000000.00"), "calificacion": Decimal("3.9"),
    },
    {
        "razon_social": "Frío Express Logística S.A.S.", "nit": "901002003-1",
        "categoria": CategoriaProveedor.logistica, "contacto_nombre": "Óscar Londoño",
        "correo": "operaciones@frioexpress.com.co", "telefono": "+576042221100",
        "ciudad": "Rionegro", "direccion": "Km 2 vía Aeropuerto JMC",
        "sitio_web": "https://frioexpress.com.co",
        "dias_credito": 15, "cupo_credito": Decimal("3000000.00"), "calificacion": Decimal("3.2"),
        # Único proveedor suspendido: así el filtro ?estado=suspendido
        # del panel muestra resultados desde el primer arranque.
        "estado": EstadoProveedor.suspendido,
        "motivo_suspension": "Tres entregas refrigeradas consecutivas fuera del plazo acordado.",
    },
]

# (título, descripción, imagen [ruta bajo /uploads, ver backend/uploads/productos], categoría, precio COP, stock, SKU, peso en gramos, NIT del proveedor)
# El orden es el id esperado (1..10) y coincide con data/carouselData.js del frontend.
NIT_MOLINOS = "900412873-6"
NIT_CACAO = "890912345-9"
NIT_LACTEOS = "800245619-2"

PRODUCTOS = [
    ("Torta de Chocolate Intenso", "Bizcocho húmedo de cacao con ganache de chocolate semiamargo y cobertura brillante.",
     "/uploads/productos/torta-chocolate-intenso.jpg", FamiliaProducto.tortas, 85000, 12, "TOR-001", 1200, NIT_CACAO),
    ("Torta de Fresas y Crema", "Bizcocho de vainilla con crema chantilly y fresas frescas en cada capa.",
     "/uploads/productos/torta-fresas-crema.jpg", FamiliaProducto.tortas, 78000, 15, "TOR-002", 1300, NIT_LACTEOS),
    ("Cupcakes de Vainilla x6", "Seis cupcakes esponjosos de vainilla con buttercream cremoso y chispas de colores.",
     "/uploads/productos/cupcakes-vainilla.jpg", FamiliaProducto.cupcakes, 36000, 30, "CUP-001", 480, NIT_LACTEOS),
    ("Cupcakes Red Velvet x6", "Seis cupcakes red velvet con frosting suave de queso crema.",
     "/uploads/productos/cupcakes-red-velvet.jpg", FamiliaProducto.cupcakes, 42000, 24, "CUP-002", 500, NIT_LACTEOS),
    ("Galletas con Chips de Chocolate x12", "Docena de galletas crujientes por fuera y suaves por dentro, con chips de chocolate.",
     "/uploads/productos/galletas-chips-chocolate.jpg", FamiliaProducto.galletas, 32000, 40, "GAL-001", 600, NIT_CACAO),
    ("Macarons Surtidos x12", "Caja de doce macarons de almendra en sabores fresa, pistacho, limón y chocolate.",
     "/uploads/productos/macarons-surtidos.jpg", FamiliaProducto.galletas, 58000, 18, "GAL-002", 240, NIT_MOLINOS),
    ("Cheesecake de Frutos Rojos", "Cheesecake horneado sobre base de galleta, con salsa de fresa y mora.",
     "/uploads/productos/cheesecake-frutos-rojos.jpg", FamiliaProducto.postres, 68000, 9, "POS-001", 1000, NIT_LACTEOS),
    ("Croissants de Mantequilla x4", "Cuatro croissants de hojaldre laminado con mantequilla, horneados cada mañana.",
     "/uploads/productos/croissants-mantequilla.jpg", FamiliaProducto.hojaldres, 24000, 35, "HOJ-001", 320, NIT_MOLINOS),
    ("Pan de Bono x10", "Diez panes de bono calientes, con queso costeño y almidón de yuca.",
     "/uploads/productos/pan-de-bono.jpg", FamiliaProducto.panaderia, 18000, 50, "PAN-001", 500, NIT_MOLINOS),
    ("Torta Tres Leches", "Bizcocho esponjoso bañado en tres leches, con crema chantilly y canela.",
     "/uploads/productos/torta-tres-leches.jpg", FamiliaProducto.tortas, 72000, 10, "TOR-003", 1500, NIT_LACTEOS),
]


def sembrar_usuarios(sesion) -> int:
    creados = 0
    for datos in USUARIOS:
        existente = sesion.scalar(select(Usuario).where(Usuario.correo == datos["correo"]))
        if existente:
            continue
        sesion.add(
            Usuario(
                **datos,
                password_hash=crear_hash(PASSWORD_DEMO),
                verificado=True,
                activo=True,
            )
        )
        creados += 1
    sesion.commit()
    return creados


def sembrar_proveedores(sesion) -> int:
    creados = 0
    for datos in PROVEEDORES:
        existente = sesion.scalar(select(Proveedor).where(Proveedor.nit == datos["nit"]))
        if existente:
            continue
        sesion.add(Proveedor(**datos))
        creados += 1
    sesion.commit()
    return creados


def sembrar_productos(sesion) -> int:
    creados = 0
    for orden, (titulo, descripcion, imagen, familia, precio, stock, sku, peso, nit) in enumerate(
        PRODUCTOS, start=1
    ):
        if sesion.scalar(select(Producto).where(Producto.sku == sku)):
            continue
        proveedor = sesion.scalar(select(Proveedor).where(Proveedor.nit == nit))
        sesion.add(
            Producto(
                titulo=titulo,
                descripcion=descripcion,
                imagen=imagen,
                orden=orden,
                precio=precio,
                stock=stock,
                sku=sku,
                familia=familia,
                peso_g=peso,
                activo=True,
                proveedor_id=proveedor.id if proveedor else None,
            )
        )
        creados += 1
    sesion.commit()
    return creados


def limpiar(sesion) -> None:
    """Borra SOLO lo sembrado por este script, en orden inverso a las FK."""
    skus = [fila[6] for fila in PRODUCTOS]
    nits = [fila["nit"] for fila in PROVEEDORES]
    correos = [fila["correo"] for fila in USUARIOS]

    for producto in sesion.scalars(select(Producto).where(Producto.sku.in_(skus))):
        sesion.delete(producto)
    sesion.commit()

    for proveedor in sesion.scalars(select(Proveedor).where(Proveedor.nit.in_(nits))):
        sesion.delete(proveedor)
    for usuario in sesion.scalars(select(Usuario).where(Usuario.correo.in_(correos))):
        sesion.delete(usuario)
    sesion.commit()
    print("Datos de ejemplo anteriores eliminados.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Puebla la base de datos de Dulce Esencia Pastelería con datos de ejemplo.")
    parser.add_argument("--reset", action="store_true", help="Borra lo sembrado antes y vuelve a insertarlo.")
    argumentos = parser.parse_args()

    # Asegura que las tablas existan antes de insertar (mismo paso que
    # ejecuta el servidor al arrancar).
    sincronizar_esquema()

    sesion = SessionLocal()
    try:
        if argumentos.reset:
            limpiar(sesion)

        usuarios = sembrar_usuarios(sesion)
        proveedores = sembrar_proveedores(sesion)
        productos = sembrar_productos(sesion)

        print(
            f"Listo. Usuarios nuevos: {usuarios} · Proveedores nuevos: {proveedores} · "
            f"Productos nuevos: {productos}"
        )
        print(f'Ingreso de prueba: admin@dulceesencia.com / {PASSWORD_DEMO}')
    finally:
        sesion.close()


if __name__ == "__main__":
    main()
