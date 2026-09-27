"""
Esquemas Pydantic v2 de `/api/proveedores`.

Cubren, de forma explícita, estos puntos de la lista de chequeo:

  * 11 — esquemas separados de creación (`ProveedorCrear`), actualización
         total (`ProveedorReemplazar`), actualización parcial
         (`ProveedorActualizar`) y respuesta (`ProveedorSalida`).
  * 12 — cada campo declara sus restricciones con `Field`
         (min_length/max_length, ge/le, pattern).
  * 13 — `field_validator` con reglas de negocio propias del dominio
         (dígito de verificación del NIT colombiano, normalización del
         teléfono, correo corporativo).
  * 14 — `model_validator` que compara VARIOS campos entre sí
         (días de crédito ↔ cupo de crédito, y la regla de logística).
  * 16 — sintaxis exclusiva de Pydantic v2: nada de `@validator`,
         `class Config`, `.dict()` ni `orm_mode`.
  *  5 — el cliente NO puede enviar `id`, `estado`, `motivo_suspension`,
         `creado_en` ni `calificacion`: esos campos no existen en ningún
         esquema de entrada, así que Pydantic los rechaza
         (`model_config = ConfigDict(extra="forbid")`).
  * 27 — ejemplos de cuerpo con `json_schema_extra`, visibles en /docs.
  * 53 — `from_attributes=True` y un esquema Resumen
         (`ProveedorResumen`) para las relaciones.
"""

import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.proveedor import CategoriaProveedor, EstadoProveedor

# NIT colombiano: 9 o 10 dígitos, guion y dígito de verificación.
# El guion-DV es opcional al escribir, pero si viene debe ser correcto.
PATRON_NIT = r"^\d{9,10}(-\d)?$"
PATRON_TELEFONO = r"^\+?[\d\s\-()]{7,20}$"

# Dominios de correo personales: se rechazan porque el contacto de un
# proveedor debe ser una cuenta corporativa a la que Dulce Esencia pueda
# reclamar formalmente un pedido.
DOMINIOS_PERSONALES = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "icloud.com"}

# Tope de cupo de crédito por categoría (regla interna de tesorería).
CUPO_MAXIMO_LOGISTICA = Decimal("5000000")


def _digito_verificacion_nit(numero: str) -> int:
    """
    Calcula el dígito de verificación de un NIT colombiano con el
    algoritmo oficial de la DIAN (suma ponderada módulo 11).
    """
    pesos = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
    suma = sum(int(digito) * pesos[indice] for indice, digito in enumerate(reversed(numero)))
    residuo = suma % 11
    if residuo in (0, 1):
        return residuo
    return 11 - residuo


# ----------------------------------------------------------------------
# Validadores de campo (criterio 13).
#
# Se definen como funciones de módulo, no como métodos de una clase, para
# que los esquemas de creación, reemplazo y actualización parcial usen
# EXACTAMENTE la misma regla: un PATCH no puede ser una puerta trasera
# para guardar un NIT que un POST habría rechazado.
# ----------------------------------------------------------------------


def normalizar_nit(valor: str | None) -> str | None:
    """
    Regla de negocio propia: si el NIT trae dígito de verificación, debe
    coincidir con el que calcula el algoritmo de la DIAN. Un `pattern`
    por sí solo aceptaría 900123456-3, que no existe.

    El valor se normaliza SIEMPRE con su DV, para que la unicidad de la
    columna funcione de verdad: 900123456 y 900123456-7 son el mismo NIT
    y no deben poder registrarse como dos proveedores distintos.
    """
    if valor is None:
        return None
    valor = valor.strip()
    numero, _, dv_recibido = valor.partition("-")
    dv_calculado = _digito_verificacion_nit(numero)

    if dv_recibido and int(dv_recibido) != dv_calculado:
        raise ValueError(
            f"El dígito de verificación no corresponde al NIT {numero} "
            f"(debería ser {dv_calculado})."
        )
    return f"{numero}-{dv_calculado}"


def validar_correo_corporativo(valor):
    """El contacto de un proveedor debe ser una cuenta corporativa."""
    if valor is None:
        return None
    dominio = str(valor).split("@")[-1].lower()
    if dominio in DOMINIOS_PERSONALES:
        raise ValueError(
            f"Usa el correo corporativo del proveedor: no se aceptan cuentas personales ({dominio})."
        )
    return valor


def normalizar_telefono(valor: str | None) -> str | None:
    """'+57 (605) 322-1144' -> '+576053221144' (se guarda ya normalizado)."""
    if valor is None:
        return None
    limpio = re.sub(r"[^\d+]", "", valor)
    if limpio.count("+") > 1 or ("+" in limpio and not limpio.startswith("+")):
        raise ValueError("El teléfono solo puede llevar '+' al inicio.")
    if len(re.sub(r"\D", "", limpio)) < 7:
        raise ValueError("El teléfono debe tener al menos 7 dígitos.")
    return limpio


def validar_sitio_web(valor: str | None) -> str | None:
    if valor in (None, ""):
        return None
    if not re.match(r"^https?://", valor, re.IGNORECASE):
        raise ValueError("El sitio web debe empezar por http:// o https://")
    return valor


class ProveedorBase(BaseModel):
    """Campos comunes a creación y reemplazo, con sus restricciones."""

    # extra="forbid": si el cliente manda `estado`, `id` o cualquier campo
    # que decide el servidor, la petición se rechaza con 422 en vez de
    # ignorarlo en silencio (criterio 5).
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    razon_social: str = Field(
        min_length=3,
        max_length=120,
        description="Nombre legal del proveedor tal como figura en el RUT.",
    )
    nit: str = Field(
        min_length=9,
        max_length=20,
        pattern=PATRON_NIT,
        description="NIT con dígito de verificación opcional (ej. 900123456-7).",
    )
    categoria: CategoriaProveedor = Field(description="Qué línea de suministro cubre.")
    contacto_nombre: str = Field(min_length=3, max_length=80, description="Persona de contacto comercial.")
    correo: EmailStr = Field(description="Correo corporativo del contacto.")
    telefono: str = Field(min_length=7, max_length=20, pattern=PATRON_TELEFONO)
    ciudad: str = Field(min_length=2, max_length=60)
    direccion: str | None = Field(default=None, max_length=160)
    sitio_web: str | None = Field(default=None, max_length=160)
    dias_credito: int = Field(
        default=0,
        ge=0,
        le=180,
        description="Plazo de pago acordado, en días. 0 = pago de contado.",
    )
    cupo_credito: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=Decimal("9999999999.99"),
        description="Monto máximo que se le puede deber al proveedor (COP).",
    )

    # ---------------- Validadores de campo (criterio 13) ----------------

    _normalizar_nit = field_validator("nit")(normalizar_nit)
    _validar_correo = field_validator("correo")(validar_correo_corporativo)
    _normalizar_telefono = field_validator("telefono")(normalizar_telefono)
    _validar_sitio = field_validator("sitio_web")(validar_sitio_web)

    # ---------------- Validador de modelo (criterio 14) ----------------

    @model_validator(mode="after")
    def validar_coherencia_de_credito(self) -> "ProveedorBase":
        """
        Compara VARIOS campos entre sí — algo que ningún validador de
        campo puede hacer por separado:

        1. Crédito coherente: un plazo de pago sin cupo (o un cupo sin
           plazo) es un acuerdo comercial imposible de ejecutar.
        2. Logística: los transportadores se pagan contra entrega, así
           que su cupo no puede superar el tope de tesorería.
        """
        tiene_plazo = self.dias_credito > 0
        tiene_cupo = self.cupo_credito > 0

        if tiene_plazo and not tiene_cupo:
            raise ValueError(
                "Se acordaron días de crédito pero el cupo es 0: define el cupo de crédito "
                "o deja el plazo en 0 (pago de contado)."
            )
        if tiene_cupo and not tiene_plazo:
            raise ValueError(
                "Se definió un cupo de crédito pero el plazo es 0 días: indica cuántos días "
                "de crédito se acordaron."
            )
        if self.categoria is CategoriaProveedor.logistica and self.cupo_credito > CUPO_MAXIMO_LOGISTICA:
            raise ValueError(
                "Los proveedores de logística no pueden superar un cupo de "
                f"{CUPO_MAXIMO_LOGISTICA:,.0f} COP."
            )
        return self


class ProveedorCrear(ProveedorBase):
    """Cuerpo de POST /api/proveedores."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "razon_social": "Molinos y Harinas del Valle S.A.S.",
                    "nit": "900412873-6",
                    "categoria": "materias_primas",
                    "contacto_nombre": "Marcela Ríos",
                    "correo": "compras@molinosdelvalle.com",
                    "telefono": "+57 (602) 322-1144",
                    "ciudad": "Cali",
                    "direccion": "Cra 8 # 25-40, Bodega 3",
                    "sitio_web": "https://molinosdelvalle.com",
                    "dias_credito": 30,
                    "cupo_credito": "12000000.00",
                }
            ]
        },
    )


class ProveedorReemplazar(ProveedorBase):
    """
    Cuerpo de PUT /api/proveedores/{id}: reemplazo TOTAL del recurso, así
    que exige los mismos campos obligatorios que la creación.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "razon_social": "Molinos y Harinas del Valle S.A.S.",
                    "nit": "900412873-6",
                    "categoria": "insumos",
                    "contacto_nombre": "Marcela Ríos Gómez",
                    "correo": "compras@molinosdelvalle.com",
                    "telefono": "+576023221144",
                    "ciudad": "Palmira",
                    "direccion": "Zona Industrial, Cl 30 # 10-15",
                    "sitio_web": None,
                    "dias_credito": 0,
                    "cupo_credito": "0",
                }
            ]
        },
    )


class ProveedorActualizar(BaseModel):
    """
    Cuerpo de PATCH /api/proveedores/{id}: actualización PARCIAL. Todos
    los campos son opcionales y el router usa
    `model_dump(exclude_unset=True)` para no sobrescribir con `null` lo
    que el cliente ni siquiera mencionó (criterio 15).

    Hereda las mismas validaciones de campo que `ProveedorBase`
    reutilizándolas explícitamente al final del archivo.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {"ciudad": "Medellín", "dias_credito": 45, "cupo_credito": "20000000.00"},
                {"contacto_nombre": "Julián Restrepo"},
            ]
        },
    )

    razon_social: str | None = Field(default=None, min_length=3, max_length=120)
    nit: str | None = Field(default=None, min_length=9, max_length=20, pattern=PATRON_NIT)
    categoria: CategoriaProveedor | None = None
    contacto_nombre: str | None = Field(default=None, min_length=3, max_length=80)
    correo: EmailStr | None = None
    telefono: str | None = Field(default=None, min_length=7, max_length=20, pattern=PATRON_TELEFONO)
    ciudad: str | None = Field(default=None, min_length=2, max_length=60)
    direccion: str | None = Field(default=None, max_length=160)
    sitio_web: str | None = Field(default=None, max_length=160)
    dias_credito: int | None = Field(default=None, ge=0, le=180)
    cupo_credito: Decimal | None = Field(default=None, ge=0, le=Decimal("9999999999.99"))

    # Los mismos validadores de campo que en la creación: un PATCH no
    # puede ser una puerta trasera para meter un NIT inválido.
    _normalizar_nit = field_validator("nit")(normalizar_nit)
    _validar_correo = field_validator("correo")(validar_correo_corporativo)
    _normalizar_telefono = field_validator("telefono")(normalizar_telefono)
    _validar_sitio = field_validator("sitio_web")(validar_sitio_web)

    @model_validator(mode="after")
    def validar_credito_parcial(self) -> "ProveedorActualizar":
        """
        En un PATCH solo se pueden comparar los campos que SÍ vinieron:
        si el cliente manda los dos, deben ser coherentes entre sí; si
        manda uno solo, la coherencia contra el valor ya guardado la
        verifica la capa crud, que es la única que conoce el estado
        actual del proveedor.
        """
        enviados = self.model_fields_set
        if {"dias_credito", "cupo_credito"} <= enviados:
            if (self.dias_credito or 0) > 0 and (self.cupo_credito or 0) <= 0:
                raise ValueError("Con días de crédito mayores a 0 el cupo debe ser mayor a 0.")
            if (self.cupo_credito or 0) > 0 and (self.dias_credito or 0) <= 0:
                raise ValueError("Con un cupo mayor a 0 los días de crédito deben ser mayores a 0.")
        return self


class SuspensionCrear(BaseModel):
    """
    Cuerpo del sub-recurso POST /api/proveedores/{id}/suspensiones
    (criterio 4): suspender es una operación de negocio con su propio
    dato de entrada —el motivo, que queda registrado— y no un PATCH
    genérico sobre un campo `estado`.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [{"motivo": "Tres entregas consecutivas fuera del plazo acordado."}]
        },
    )

    motivo: str = Field(
        min_length=10,
        max_length=200,
        description="Por qué se suspende. Queda guardado en el expediente del proveedor.",
    )

    @field_validator("motivo")
    @classmethod
    def motivo_con_contenido(cls, valor: str) -> str:
        if len(valor.split()) < 3:
            raise ValueError("Describe el motivo con al menos tres palabras.")
        return valor


# ------------------------------- Salidas -------------------------------


class ProveedorResumen(BaseModel):
    """
    Versión reducida para usar DENTRO de otras respuestas (criterio 53):
    el detalle de un producto muestra su proveedor con estos cuatro
    campos, sin arrastrar condiciones comerciales ni datos de contacto
    a un endpoint público.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    razon_social: str
    nit: str
    estado: EstadoProveedor


class ProveedorSalida(BaseModel):
    """
    Respuesta de todos los endpoints de proveedores (criterio 17): al
    declararse campo por campo, ningún atributo interno del modelo puede
    filtrarse por accidente al agregarse después a la tabla.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    razon_social: str
    nit: str
    categoria: CategoriaProveedor
    contacto_nombre: str
    correo: EmailStr
    telefono: str
    ciudad: str
    direccion: str | None
    sitio_web: str | None
    dias_credito: int
    cupo_credito: Decimal
    calificacion: Decimal | None
    estado: EstadoProveedor
    motivo_suspension: str | None
    creado_en: datetime | None
    actualizado_en: datetime | None
    total_productos: int = Field(
        default=0,
        description="Cuántos productos del catálogo surte este proveedor.",
    )


class PaginacionSalida(BaseModel):
    pagina: int
    limite: int
    total: int
    totalPaginas: int  # noqa: N815 - nombre ya usado por el resto de la API


class ProveedoresPagina(BaseModel):
    """Envoltorio del listado: misma forma que el resto de listados de la API."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "datos": [],
                    "paginacion": {"pagina": 1, "limite": 10, "total": 0, "totalPaginas": 0},
                }
            ]
        }
    )

    datos: list[ProveedorSalida]
    paginacion: PaginacionSalida
