"""
Router de /api/usuarios y /api/auth (login).

Migración 1 a 1 de la porción de backend-node/routes/usuarios.routes.js
correspondiente a POST /registro y POST /login (fuente de verdad).

Dos routers en este mismo archivo porque el enunciado agrupa ambas rutas
bajo "Usuarios" aunque viven bajo prefijos distintos en la API
(/api/usuarios/registro vs /api/auth/login) — igual que en Node, donde
ambas están en usuarios.routes.js pero una se monta como /api/usuarios
y la otra queda expuesta también como /api/auth/login en server.js.

Diferencias deliberadas frente a Node (ver app/auth.py, decisión de
arquitectura):
- El JWT viaja en el body de la respuesta (access_token), NUNCA en una
  cookie httpOnly: este backend usa Bearer como mecanismo PRINCIPAL de
  sesión, no como fallback. Por eso no existe aquí un equivalente a
  opcionesCookieToken()/duracionEnMs()/"recordarme": esos conceptos
  solo existen para la variante de cookie.
- La validación de forma/reglas de cada campo ya no vive en un
  middleware (validarCuerpo + validadores.js) sino en los schemas
  Pydantic (app/schemas/usuario.py, app/schemas/auth.py), que FastAPI
  aplica automáticamente al parsear el body y responde 422 (no 400)
  si algo no cumple.
- El rate limiting (limiterLogin/limiterRegistro/limiterRecuperar de
  Node) SÍ está replicado, con slowapi en vez de express-rate-limit
  (ver app/rate_limit.py) — mismas ventanas de tiempo y mismos topes de
  intentos, aplicados con @limiter.limit(...) sobre /login, /registro,
  /recuperar, /restablecer, /verificar-correo y /reenviar-verificacion.
- La verificación de correo y la recuperación de contraseña usan un
  código OTP de 6 dígitos enviado por correo (ver app/utils/otp.py),
  en vez de un enlace con un token largo: el usuario escribe el código
  a mano en el frontend (/verificar-correo, /restablecer-password).
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import crear_access_token, crear_hash, get_current_user, requiere_rol, verificar_hash
from app.config import get_settings
from app.database import get_db
from app.rate_limit import (
    LIMITE_LOGIN,
    LIMITE_RECUPERAR,
    LIMITE_REGISTRO,
    MENSAJE_LIMITE_LOGIN,
    MENSAJE_LIMITE_RECUPERAR,
    MENSAJE_LIMITE_REGISTRO,
    limiter,
)
from app.models.usuario import RolUsuario, Usuario
from app.schemas.auth import (
    LoginEntrada,
    ReenviarVerificacionEntrada,
    RecuperarEntrada,
    RestablecerEntrada,
    TokenSalida,
    VerificarCorreoEntrada,
)
from app.schemas.usuario import (
    CambiarPasswordEntrada,
    RolCambioEntrada,
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioEstadoEntrada,
    UsuarioSalida,
)
from app.repositories.usuario_repository import buscar_por_correo
from app.services.notificaciones import enviar_recuperacion_password, enviar_verificacion_cuenta
from app.utils.otp import generar_otp, hash_otp, verificar_otp
from app.utils.paginacion import construir_meta_paginacion, obtener_parametros_paginacion

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

settings = get_settings()

# Vigencia de cada código OTP. Deliberadamente más cortos que el enlace
# que reemplazan (24h / 60min): un código de 6 dígitos está pensado
# para escribirse a mano apenas llega al correo, no para guardarse y
# usarse horas después — una ventana más corta reduce la superficie de
# ataque sin afectar el uso normal.
MINUTOS_VIGENCIA_OTP_VERIFICACION = 15
MINUTOS_VIGENCIA_OTP_RECUPERACION = 10

# Máximo de intentos fallidos consecutivos contra UN MISMO código antes
# de invalidarlo y obligar a pedir uno nuevo. Necesario porque, a
# diferencia del token de enlace (32 bytes aleatorios, imposible de
# adivinar), un OTP de 6 dígitos tiene solo 10^6 combinaciones: sin
# este freno, alguien con varias peticiones podría "fuerza-brutear" un
# código antes de que expire.
MAX_INTENTOS_OTP = 5


def _consumir_otp(
    db: Session,
    usuario: Usuario | None,
    *,
    campo_hash: str,
    campo_expira: str,
    campo_intentos: str,
    codigo: str,
) -> None:
    """
    Valida un código OTP recibido contra el guardado en `usuario` (en
    los campos indicados por `campo_hash`/`campo_expira`/`campo_intentos`,
    ya sea el par de verificación de correo o el de recuperación de
    contraseña) y, si es válido, LIMPIA esos tres campos en el objeto
    (hash y expira en None, intentos en 0) sin hacer commit todavía —
    el llamador es quien decide qué más cambiar en la misma transacción
    (usuario.verificado, usuario.password_hash, etc.) antes de guardar.

    Si el código NO es válido, levanta HTTPException 400 con un mensaje
    específico:
      - Código inexistente/expirado (o correo inexistente): mensaje
        genérico, para no revelar si el correo está registrado.
      - Código incorrecto pero con intentos restantes: cuenta el
        intento fallido AHORA MISMO (commit inmediato, para que no se
        pierda aunque la petición termine en error) y avisa cuántos
        intentos quedan.
      - Código incorrecto y ya sin intentos restantes: invalida el
        código (para forzar a pedir uno nuevo) y avisa.
    """
    hash_guardado = getattr(usuario, campo_hash, None) if usuario else None
    expira = getattr(usuario, campo_expira, None) if usuario else None
    intentos = getattr(usuario, campo_intentos, 0) if usuario else 0

    sin_codigo_vigente = (
        usuario is None
        or not hash_guardado
        or not expira
        or expira.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)
    )
    if sin_codigo_vigente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código no es válido o ya expiró. Solicita uno nuevo.",
        )

    if intentos >= MAX_INTENTOS_OTP:
        setattr(usuario, campo_hash, None)
        setattr(usuario, campo_expira, None)
        setattr(usuario, campo_intentos, 0)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Superaste el número máximo de intentos con ese código. Solicita uno nuevo.",
        )

    if not verificar_otp(codigo, hash_guardado):
        nuevos_intentos = intentos + 1
        setattr(usuario, campo_intentos, nuevos_intentos)
        restantes = MAX_INTENTOS_OTP - nuevos_intentos
        if restantes <= 0:
            setattr(usuario, campo_hash, None)
            setattr(usuario, campo_expira, None)
            setattr(usuario, campo_intentos, 0)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código incorrecto. Superaste el número máximo de intentos; solicita uno nuevo.",
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Código incorrecto. Te queda(n) {restantes} intento(s) antes de que se invalide.",
        )

    # Código correcto: se limpia para que no pueda reutilizarse. El
    # commit final queda a cargo del llamador (junto con los demás
    # cambios de la operación: verificado=True, password_hash, etc.).
    setattr(usuario, campo_hash, None)
    setattr(usuario, campo_expira, None)
    setattr(usuario, campo_intentos, 0)


@router.post("/registro", response_model=None, status_code=status.HTTP_201_CREATED)
@limiter.limit(LIMITE_REGISTRO, error_message=MENSAJE_LIMITE_REGISTRO)
def registrar_usuario(
    request: Request,
    datos: UsuarioCrear,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Crea un cliente nuevo a partir de los datos del RegisterModal.
    Ruta PÚBLICA. Réplica de POST /api/usuarios/registro en
    usuarios.routes.js.

    El registro público SIEMPRE asigna el rol "cliente" — aunque
    UsuarioCrear admite un campo `rol` opcional (lo usa la creación
    desde el panel admin, fuera del alcance de esta ruta), aquí se
    ignora deliberadamente cualquier valor que llegue en ese campo y
    se fuerza "cliente" a mano, igual que en Node (que ni siquiera
    acepta `rol` en el body de /registro).

    `acepta_tratamiento_datos` es obligatorio aquí (aunque el schema lo
    admite en False por defecto, porque también lo usa la creación
    desde el panel admin): sin la aceptación explícita del titular no
    se crea la cuenta — ver docs/POLITICA-TRATAMIENTO-DATOS.md.
    """
    if not datos.acepta_tratamiento_datos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes aceptar la política de tratamiento de datos personales para registrarte.",
        )

    codigo_plano = generar_otp()
    expira = datetime.now(timezone.utc) + timedelta(minutes=MINUTOS_VIGENCIA_OTP_VERIFICACION)

    usuario = Usuario(
        nombre=datos.nombre,
        apellido=datos.apellido,
        tipo_documento=datos.tipo_documento,
        numero_documento=datos.numero_documento,
        direccion=datos.direccion,
        telefono=datos.telefono,
        correo=datos.correo,
        password_hash=crear_hash(datos.password),
        rol=RolUsuario.cliente,
        verificado=False,
        verificacion_otp_hash=hash_otp(codigo_plano),
        verificacion_otp_expira=expira,
        verificacion_otp_intentos=0,
        tratamiento_datos_aceptado_en=datetime.now(timezone.utc),
    )

    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo o documento.",
        ) from None
    db.refresh(usuario)

    # El correo con el código se envía como tarea en segundo plano
    # (BackgroundTasks): el registro responde ya y el SMTP corre
    # después. Sin SMTP_HOST configurado solo queda en el log (ver
    # app/services/notificaciones.py). En desarrollo, además, el
    # código se imprime en consola para poder probar sin bandeja de
    # entrada real.
    background_tasks.add_task(
        enviar_verificacion_cuenta, usuario.correo, usuario.nombre, codigo_plano, MINUTOS_VIGENCIA_OTP_VERIFICACION
    )
    if settings.NODE_ENV != "production":
        print(f"[Dulce Esencia] Código de verificación de correo para {usuario.correo}: {codigo_plano}")
        print(f"[Dulce Esencia] Vigente por {MINUTOS_VIGENCIA_OTP_VERIFICACION} minutos.")

    respuesta = {
        "mensaje": "Cuenta creada correctamente. Revisa tu correo y escribe el código de 6 dígitos para verificar la cuenta antes de iniciar sesión.",
        "id": usuario.id,
    }
    if settings.NODE_ENV != "production":
        respuesta["codigoVerificacion"] = codigo_plano
    return respuesta


@auth_router.post("/login", response_model=TokenSalida)
@limiter.limit(LIMITE_LOGIN, error_message=MENSAJE_LIMITE_LOGIN)
def iniciar_sesion(request: Request, datos: LoginEntrada, db: Session = Depends(get_db)):
    """
    Verifica correo/contraseña y devuelve un JWT si son correctos.
    Ruta PÚBLICA. Réplica de POST /api/usuarios/login en
    usuarios.routes.js, expuesta aquí en /api/auth/login.

    El JWT viaja en el body (access_token), no en una cookie httpOnly
    (ver decisión de arquitectura en app/auth.py) — por eso no existe
    aquí un equivalente a "recordarme": ese concepto solo aplica a la
    duración de la cookie en la variante de Node.
    """
    error_credenciales = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Correo o contraseña incorrectos.",
    )

    # CONSULTA PREPARADA (prepared statement): el correo viaja como PARÁMETRO ligado,
    # nunca concatenado dentro del texto SQL. Ver app/repositories/usuario_repository.py
    # y docs/SEGURIDAD-SQL-INJECTION.md.
    usuario = buscar_por_correo(db, datos.correo)
    if usuario is None:
        raise error_credenciales

    if not verificar_hash(datos.password, usuario.password_hash):
        raise error_credenciales

    if not usuario.verificado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes verificar tu correo antes de iniciar sesión. Revisa el enlace que te enviamos.",
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta está inactiva. Contacta a un administrador de Dulce Esencia.",
        )

    # "tv" (token_version) queda grabado en el JWT tal como estaba la
    # cuenta en el momento del login. get_current_user() lo compara en
    # cada petición contra usuarios.token_version en la BD: si cambió
    # (cambio de contraseña, restablecimiento, o un futuro "cerrar
    # sesión en todos los dispositivos"), este JWT queda invalidado de
    # inmediato aunque todavía no haya expirado por tiempo — mismo
    # mecanismo que ya usaba Node en auth.middleware.js.
    access_token = crear_access_token(
        {"sub": usuario.correo, "role": usuario.rol, "tv": usuario.token_version}
    )

    return TokenSalida(
        access_token=access_token,
        usuario=UsuarioSalida.model_validate(usuario),
    )


@router.post("/recuperar", response_model=None)
@limiter.limit(LIMITE_RECUPERAR, error_message=MENSAJE_LIMITE_RECUPERAR)
def recuperar_password(
    request: Request,
    datos: RecuperarEntrada,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Inicia el flujo de "olvidé mi contraseña". Réplica de POST
    /api/usuarios/recuperar en usuarios.routes.js.

    Por seguridad, la respuesta es SIEMPRE el mismo mensaje genérico
    exista o no el correo — para no revelar qué correos están
    registrados. El código se imprime en consola (no hay proveedor de
    correo configurado en este proyecto), igual que en Node.
    """
    mensaje_generico = {
        "mensaje": "Si el correo está registrado, te enviaremos un código para restablecer tu contraseña."
    }

    usuario = buscar_por_correo(db, datos.correo)
    if usuario is not None:
        codigo_plano = generar_otp()
        usuario.reset_otp_hash = hash_otp(codigo_plano)
        usuario.reset_otp_expira = datetime.now(timezone.utc) + timedelta(
            minutes=MINUTOS_VIGENCIA_OTP_RECUPERACION
        )
        usuario.reset_otp_intentos = 0
        db.commit()

        background_tasks.add_task(
            enviar_recuperacion_password,
            usuario.correo,
            usuario.nombre,
            codigo_plano,
            MINUTOS_VIGENCIA_OTP_RECUPERACION,
        )
        if settings.NODE_ENV != "production":
            print(f"[Dulce Esencia] Código de recuperación de contraseña para {usuario.correo}: {codigo_plano}")
            print(f"[Dulce Esencia] Vigente por {MINUTOS_VIGENCIA_OTP_RECUPERACION} minutos.")

    return mensaje_generico


@router.post("/restablecer", response_model=None)
@limiter.limit(LIMITE_RECUPERAR, error_message=MENSAJE_LIMITE_RECUPERAR)
def restablecer_password(request: Request, datos: RestablecerEntrada, db: Session = Depends(get_db)):
    """
    Segundo paso de "olvidé mi contraseña". Compara el código OTP
    recibido contra su hash guardado (con freno de intentos, ver
    _consumir_otp), revisa que no haya expirado, y si todo es válido
    actualiza password_hash. El código se invalida (queda en None)
    para que no pueda reutilizarse, y token_version se incrementa
    (mismo propósito que en el cambio de contraseña del perfil:
    cualquier JWT viejo deja de ser válido de inmediato).
    """
    usuario = db.query(Usuario).filter(Usuario.correo == datos.correo).first()

    _consumir_otp(
        db,
        usuario,
        campo_hash="reset_otp_hash",
        campo_expira="reset_otp_expira",
        campo_intentos="reset_otp_intentos",
        codigo=datos.codigo,
    )

    usuario.password_hash = crear_hash(datos.password_nueva)
    usuario.token_version += 1
    db.commit()

    return {"mensaje": "Contraseña restablecida correctamente. Ya puedes iniciar sesión."}


@router.post("/reenviar-verificacion", response_model=None)
@limiter.limit(LIMITE_RECUPERAR, error_message=MENSAJE_LIMITE_RECUPERAR)
def reenviar_verificacion(request: Request, datos: ReenviarVerificacionEntrada, db: Session = Depends(get_db)):
    """
    Reenvía un código de verificación de correo nuevo si el original
    expiró, se perdió o se agotaron los intentos. Mismo criterio de
    respuesta genérica que /recuperar, y solo genera un código nuevo
    si la cuenta existe y todavía no está verificada.
    """
    mensaje_generico = {
        "mensaje": "Si el correo está registrado y pendiente de verificar, te enviaremos un nuevo código."
    }

    usuario = db.query(Usuario).filter(Usuario.correo == datos.correo).first()
    if usuario is not None and not usuario.verificado:
        codigo_plano = generar_otp()
        usuario.verificacion_otp_hash = hash_otp(codigo_plano)
        usuario.verificacion_otp_expira = datetime.now(timezone.utc) + timedelta(
            minutes=MINUTOS_VIGENCIA_OTP_VERIFICACION
        )
        usuario.verificacion_otp_intentos = 0
        db.commit()

        if settings.NODE_ENV != "production":
            print(f"[Dulce Esencia] Nuevo código de verificación de correo para {usuario.correo}: {codigo_plano}")

    return mensaje_generico


@router.post("/verificar-correo", response_model=None)
@limiter.limit(LIMITE_RECUPERAR, error_message=MENSAJE_LIMITE_RECUPERAR)
def verificar_correo(request: Request, datos: VerificarCorreoEntrada, db: Session = Depends(get_db)):
    """
    Segundo paso del registro: confirma el código OTP de 6 dígitos
    enviado por POST /registro. Ruta PÚBLICA, con el mismo límite de
    peticiones por IP que /recuperar y /restablecer (además del freno
    de intentos por código de _consumir_otp): sin esto, alguien podría
    intentar muchos correos + códigos desde la misma IP sin que nada lo
    frene entre cuentas distintas.

    Compara el hash del código recibido contra el guardado (con freno
    de intentos, ver _consumir_otp), revisa que no haya expirado, y si
    es válido marca la cuenta como verificada y consume el código
    (queda en None) para que no pueda reutilizarse.
    """
    usuario = db.query(Usuario).filter(Usuario.correo == datos.correo).first()

    _consumir_otp(
        db,
        usuario,
        campo_hash="verificacion_otp_hash",
        campo_expira="verificacion_otp_expira",
        campo_intentos="verificacion_otp_intentos",
        codigo=datos.codigo,
    )

    usuario.verificado = True
    db.commit()

    return {"mensaje": "Correo verificado correctamente. Ya puedes iniciar sesión."}


# ---------------------------------------------------------------------------
# Perfil propio (cualquier usuario autenticado, sobre SU PROPIA cuenta).
# Declaradas ANTES de las rutas con "/{usuario_id}" a propósito: FastAPI
# resuelve las rutas de un router en el orden en que se declaran, y
# "/perfil" calzaría contra el patrón "/{usuario_id}" (que espera un int)
# si esas rutas quedaran primero — Pydantic respondería 422 en vez de
# ejecutar esta función.
# ---------------------------------------------------------------------------


@router.get("/perfil", response_model=UsuarioSalida)
def obtener_perfil(usuario: Usuario = Depends(get_current_user)):
    """
    Devuelve los datos del usuario autenticado. Ruta PROTEGIDA
    (cualquier rol). Esta ruta faltaba por completo en el backend
    Python; AuthContext.jsx (frontend) la necesita para saber si hay
    sesión activa al montar la app, y MiPerfil.jsx para precargar el
    formulario de edición.
    """
    return usuario


@router.put("/perfil", response_model=UsuarioSalida)
def actualizar_perfil(
    datos: UsuarioActualizar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    El propio usuario edita sus datos de contacto (nombre, apellido,
    dirección, teléfono) — nunca correo, documento, password ni rol
    desde aquí (ver docstring de UsuarioActualizar). Ruta PROTEGIDA
    (cualquier rol). Actualización parcial: solo se tocan los campos
    que de verdad vengan en el body.
    """
    datos_enviados = datos.model_dump(exclude_unset=True)
    for campo, valor in datos_enviados.items():
        setattr(usuario, campo, valor)

    db.commit()
    db.refresh(usuario)
    return usuario


@router.put("/perfil/password", response_model=None)
def cambiar_password_perfil(
    datos: CambiarPasswordEntrada,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    El propio usuario cambia su contraseña desde MiPerfil.jsx,
    confirmando la actual antes de fijar la nueva. Ruta PROTEGIDA
    (cualquier rol). Incrementa `token_version`, igual criterio que
    restablecer_password — aunque, como allí, get_current_user todavía
    no compara `token_version` del JWT contra la BD, así que un JWT ya
    emitido sigue funcionando hasta que expire por su cuenta; conectar
    esa verificación queda fuera del alcance de esta parte.
    """
    if not verificar_hash(datos.password_actual, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta.",
        )

    usuario.password_hash = crear_hash(datos.password_nueva)
    usuario.token_version += 1
    db.commit()

    return {"mensaje": "Contraseña actualizada correctamente."}


@router.post(
    "",
    response_model=UsuarioSalida,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requiere_rol("admin"))],
)
def crear_usuario(datos: UsuarioCrear, db: Session = Depends(get_db)):
    """
    Crea un usuario directamente desde el panel de administración —a
    diferencia de POST /registro (pública, siempre fuerza `cliente` y
    deja la cuenta sin verificar)—: aquí SÍ se respeta el `rol` que
    mande el admin (UsuarioCrear ya lo soporta, ver schemas/usuario.py)
    y la cuenta queda activa y verificada de inmediato, sin pasar por
    el flujo de verificación por correo — que un admin cree la cuenta
    desde el panel es en sí mismo el acto de confianza que reemplaza
    esa verificación. Ruta PROTEGIDA solo para admin. Esta ruta faltaba
    por completo: era el único hueco que le impedía a GestionUsuarios.jsx
    crear un empleado o admin nuevo.
    """
    usuario = Usuario(
        nombre=datos.nombre,
        apellido=datos.apellido,
        tipo_documento=datos.tipo_documento,
        numero_documento=datos.numero_documento,
        direccion=datos.direccion,
        telefono=datos.telefono,
        correo=datos.correo,
        password_hash=crear_hash(datos.password),
        rol=datos.rol,
        activo=True,
        verificado=True,
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo o documento.",
        ) from None
    db.refresh(usuario)
    return usuario


@router.get("", response_model=None, dependencies=[Depends(requiere_rol("admin", "empleado"))])
def listar_usuarios(
    page: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    pagina: int | None = Query(default=None, ge=1),
    limite: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """
    Lista los usuarios registrados, paginados. Ruta PROTEGIDA para
    admin y empleado. Réplica de GET /api/usuarios en
    usuarios.routes.js: acepta ?page=&limit= y también ?pagina=&limite=,
    y responde { datos, paginacion } en vez de un arreglo plano.
    """
    pagina_final, limite_final, offset = obtener_parametros_paginacion(page, limit, pagina, limite)

    total = db.query(Usuario).count()
    usuarios = (
        db.query(Usuario)
        .order_by(Usuario.creado_en.desc())
        .offset(offset)
        .limit(limite_final)
        .all()
    )

    return {
        "datos": [UsuarioSalida.model_validate(u) for u in usuarios],
        "paginacion": construir_meta_paginacion(pagina_final, limite_final, total),
    }


@router.get(
    "/{usuario_id}",
    response_model=UsuarioSalida,
    dependencies=[Depends(requiere_rol("admin", "empleado"))],
)
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """
    Detalle de un usuario por id. Ruta PROTEGIDA para admin y
    empleado. No existía como ruta separada en usuarios.routes.js
    (Node solo lista con GET /), pero la pide este avance para poder
    abrir el formulario de edición del panel admin sin depender del
    listado paginado completo.
    """
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return usuario


@router.put("/{usuario_id}/rol", response_model=UsuarioSalida)
def cambiar_rol_usuario(
    usuario_id: int,
    datos: RolCambioEntrada,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requiere_rol("admin")),
):
    """
    Cambia el rol de un usuario (cliente/empleado/admin) desde
    GestionUsuarios.jsx. Ruta PROTEGIDA solo para admin — no existía
    todavía: PUT /{usuario_id} excluye `rol` a propósito (ver
    docstring de UsuarioActualizar) precisamente porque este endpoint
    dedicado faltaba. Un admin no puede cambiar su propio rol desde
    aquí (mismo candado que en cambiar_estado_usuario), para no poder
    degradarse o quitarse el acceso de admin por accidente.
    """
    if usuario_id == usuario_actual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes cambiar el rol de tu propia cuenta.",
        )

    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    usuario.rol = datos.rol
    db.commit()
    db.refresh(usuario)
    return usuario


@router.put(
    "/{usuario_id}",
    response_model=UsuarioSalida,
    dependencies=[Depends(requiere_rol("admin"))],
)
def actualizar_usuario(usuario_id: int, datos: UsuarioActualizar, db: Session = Depends(get_db)):
    """
    Edita los datos de contacto (nombre, apellido, dirección,
    teléfono) de un usuario cualquiera. Ruta PROTEGIDA solo para admin.

    No existía en usuarios.routes.js (Node solo tenía PUT /perfil para
    que el propio usuario edite SUS datos); se agrega aquí para el
    panel de administración, reutilizando a propósito el mismo esquema
    UsuarioActualizar y las mismas restricciones de PUT /perfil: nunca
    se puede tocar correo, documento, password ni rol desde esta ruta
    (el rol tiene su propio endpoint dedicado en Node, y aquí no se
    replica todavía por no estar en el alcance pedido).
    """
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    datos_enviados = datos.model_dump(exclude_unset=True)
    for campo, valor in datos_enviados.items():
        setattr(usuario, campo, valor)

    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}/estado", response_model=None)
def cambiar_estado_usuario(
    usuario_id: int,
    datos: UsuarioEstadoEntrada,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requiere_rol("admin")),
):
    """
    Activa o desactiva un usuario (en vez de borrarlo, para conservar
    su historial). Ruta PROTEGIDA solo para admin. Réplica de PUT
    /:id/estado en usuarios.routes.js, expuesta aquí como PATCH por
    ser una actualización parcial de un solo campo.

    Un admin no puede cambiar el estado de su propia cuenta (mismo
    candado que en Node), para no poder auto-bloquearse por accidente.
    """
    if usuario_id == usuario_actual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes cambiar el estado de tu propia cuenta.",
        )

    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    usuario.activo = datos.activo
    db.commit()

    return {
        "mensaje": "Usuario activado correctamente." if datos.activo else "Usuario desactivado correctamente.",
        "activo": datos.activo,
    }


@router.delete("/{usuario_id}", response_model=None)
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requiere_rol("admin")),
):
    """
    Elimina un usuario. Ruta PROTEGIDA solo para admin. Réplica de
    DELETE /:id en usuarios.routes.js: un admin no puede eliminar su
    propia cuenta desde aquí, y si el usuario tiene pedidos asociados
    (FK en `pedidos.usuario_id`), se responde 409 en vez de dejar que
    la base de datos rechace el DELETE con un error crudo —
    equivalente a capturar ER_ROW_IS_REFERENCED_2/errno 1451 en Node.
    """
    if usuario_id == usuario_actual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propia cuenta desde aquí.",
        )

    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    db.delete(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar un usuario que tiene pedidos. Desactívalo en su lugar.",
        ) from None

    return {"mensaje": "Usuario eliminado correctamente."}
