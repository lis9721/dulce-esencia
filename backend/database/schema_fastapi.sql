-- =====================================================================
-- Dulce Esencia Pastelería — Script de creación de la base de datos y tablas
-- Motor: MySQL / MariaDB (XAMPP)
-- Generado a partir de los modelos SQLAlchemy en backend/app/models/*.py
-- =====================================================================
-- Este script reemplaza la creación automática que hace SQLAlchemy
-- (Base.metadata.create_all) por un script SQL explícito, tal como pide
-- el entregable #6 del Cuarto Avance ("Script SQL de creación de la
-- base de datos y sus tablas").
--
-- Uso:
--   1. Abre phpMyAdmin (XAMPP) → pestaña "SQL".
--   2. Pega y ejecuta todo este archivo (crea la base de datos si no
--      existe, y todas las tablas dentro de ella).
--   3. El backend seguirá pudiendo arrancar normalmente: si las tablas
--      ya existen, SQLAlchemy no las vuelve a crear.
-- =====================================================================

-- ---------------------------------------------------------------------
-- NOTA DE MIGRACIÓN (solo si ya tenías la BD del catálogo anterior):
-- los valores de los ENUM `productos.familia` y `proveedores.categoria` y
-- la columna `productos.volumen_ml` (ahora `peso_g`) cambiaron. Lo más
-- simple es recrear la base (DROP DATABASE ...; volver a ejecutar este
-- script) y correr `python seed.py`. Si prefieres conservar datos,
-- migra a mano con ALTER TABLE ... MODIFY / CHANGE COLUMN.
--
-- NOTA DE MIGRACIÓN — normalización (ver docs/NORMALIZACION-BD.md):
-- si tu base ya existía con `usuarios.rol` como ENUM sin llave foránea
-- y con `facturas.cliente_id` duplicando `ventas.cliente_id`, aplica
-- esto en vez de recrear la base (respeta los datos ya guardados):
--
--   INSERT IGNORE INTO roles (nombre, descripcion) VALUES
--     ('admin',    'Control total: usuarios, productos, servicios, pedidos, cupones y mensajes.'),
--     ('empleado', 'Gestión operativa de productos, servicios, usuarios y pedidos, sin cupones.'),
--     ('cliente',  'Acceso a su propio perfil, carrito, pedidos y catálogo público.');
--
--   ALTER TABLE usuarios MODIFY COLUMN rol VARCHAR(20) NOT NULL DEFAULT 'cliente';
--   ALTER TABLE usuarios
--     ADD CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol) REFERENCES roles (nombre)
--     ON UPDATE CASCADE ON DELETE RESTRICT;
--
--   ALTER TABLE facturas DROP FOREIGN KEY fk_facturas_cliente;
--   ALTER TABLE facturas DROP COLUMN cliente_id;
-- ---------------------------------------------------------------------

CREATE DATABASE IF NOT EXISTS essentia_db_fastapi
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE essentia_db_fastapi;

-- ---------------------------------------------------------------------
-- 1. usuarios
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id                          INT AUTO_INCREMENT PRIMARY KEY,
    nombre                      VARCHAR(40)  NOT NULL,
    apellido                    VARCHAR(40)  NOT NULL,
    tipo_documento              ENUM('CC','TI','CE','PA') NOT NULL,
    numero_documento            VARCHAR(15)  NOT NULL,
    direccion                   VARCHAR(100) NOT NULL,
    telefono                    VARCHAR(15)  NOT NULL,
    correo                      VARCHAR(60)  NOT NULL,
    password_hash               VARCHAR(255) NOT NULL,
    -- VARCHAR + FK a roles.nombre (más abajo), no ENUM: un ENUM describe
    -- el mismo dominio que la tabla `roles` sin ninguna llave foránea
    -- entre ambos (redundancia/dependencia transitiva — ver
    -- docs/NORMALIZACION-BD.md). La restricción fk_usuarios_rol se agrega
    -- después de crear `roles`, más abajo en este script.
    rol                         VARCHAR(20)  NOT NULL DEFAULT 'cliente',
    activo                      BOOLEAN      NOT NULL DEFAULT TRUE,
    token_version               INT          NOT NULL DEFAULT 0,
    -- OTP de restablecimiento de contraseña (código de 6 dígitos, ver
    -- app/routes/usuarios.py): reset_otp_hash guarda el SHA-256 del
    -- código, nunca el código en texto plano.
    reset_otp_hash               VARCHAR(255) NULL,
    reset_otp_expira             DATETIME     NULL,
    reset_otp_intentos           INT          NOT NULL DEFAULT 0,
    verificado                  BOOLEAN      NOT NULL DEFAULT FALSE,
    -- OTP de verificación de correo (segundo paso del registro).
    verificacion_otp_hash        VARCHAR(255) NULL,
    verificacion_otp_expira      DATETIME     NULL,
    verificacion_otp_intentos    INT          NOT NULL DEFAULT 0,
    creado_en                   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_usuarios_correo UNIQUE (correo),
    CONSTRAINT uq_usuarios_documento UNIQUE (tipo_documento, numero_documento)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 2. roles  (usuarios.rol es FK a roles.nombre, ver más abajo: esta
--    tabla es la fuente de verdad del dominio de roles válidos. Qué
--    puede hacer cada rol lo sigue decidiendo requiere_rol() en el
--    backend; permisos/rol_permisos son datos consultables para el
--    panel admin, sincronizados a mano con esas reglas)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(20)  NOT NULL,
    descripcion VARCHAR(150) NOT NULL,
    CONSTRAINT uq_roles_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- usuarios.rol -> roles.nombre: se agrega aquí (y no en el CREATE TABLE
-- de `usuarios`) porque `roles` recién se acaba de crear. ON UPDATE
-- CASCADE: si se renombra un rol en `roles`, los usuarios que lo tienen
-- se actualizan solos. ON DELETE RESTRICT: no se puede borrar un rol
-- mientras algún usuario lo tenga asignado.
ALTER TABLE usuarios
    ADD CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol) REFERENCES roles (nombre)
    ON UPDATE CASCADE ON DELETE RESTRICT;

-- ---------------------------------------------------------------------
-- 3. permisos
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS permisos (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    clave       VARCHAR(60)  NOT NULL,
    descripcion VARCHAR(150) NOT NULL,
    CONSTRAINT uq_permisos_clave UNIQUE (clave)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 4. rol_permisos (tabla puente N:M entre roles y permisos)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rol_permisos (
    rol_id     INT NOT NULL,
    permiso_id INT NOT NULL,
    PRIMARY KEY (rol_id, permiso_id),
    CONSTRAINT fk_rol_permisos_rol
        FOREIGN KEY (rol_id) REFERENCES roles(id) ON DELETE CASCADE,
    CONSTRAINT fk_rol_permisos_permiso
        FOREIGN KEY (permiso_id) REFERENCES permisos(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 4b. proveedores  (módulo de proveedores)
--
-- Se crea ANTES que `productos` porque esa tabla la referencia con una
-- clave foránea (productos.proveedor_id -> proveedores.id).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS proveedores (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    razon_social      VARCHAR(120) NOT NULL,
    nit               VARCHAR(20)  NOT NULL,
    categoria         ENUM('materias_primas','lacteos','empaques','insumos','logistica')
                      NOT NULL DEFAULT 'materias_primas',
    contacto_nombre   VARCHAR(80)  NOT NULL,
    correo            VARCHAR(120) NOT NULL,
    telefono          VARCHAR(20)  NOT NULL,
    ciudad            VARCHAR(60)  NOT NULL,
    direccion         VARCHAR(160) NULL,
    sitio_web         VARCHAR(160) NULL,
    dias_credito      INT NOT NULL DEFAULT 0,
    cupo_credito      DECIMAL(12,2) NOT NULL DEFAULT 0,
    calificacion      DECIMAL(2,1) NULL,
    estado            ENUM('activo','suspendido') NOT NULL DEFAULT 'activo',
    motivo_suspension VARCHAR(200) NULL,
    creado_en         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en    TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_proveedores_nit          UNIQUE (nit),
    CONSTRAINT uq_proveedores_razon_social UNIQUE (razon_social),
    CONSTRAINT chk_proveedores_dias_credito CHECK (dias_credito BETWEEN 0 AND 180),
    CONSTRAINT chk_proveedores_cupo_credito CHECK (cupo_credito >= 0),
    CONSTRAINT chk_proveedores_calificacion CHECK (calificacion IS NULL OR calificacion BETWEEN 1 AND 5),
    INDEX ix_proveedores_estado (estado),
    INDEX ix_proveedores_categoria (categoria)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 5. productos
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS productos (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    titulo      VARCHAR(80)  NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    imagen      VARCHAR(120) NOT NULL,
    orden       INT NOT NULL DEFAULT 0,
    precio      DECIMAL(10,2) NOT NULL DEFAULT 0,
    stock       INT NOT NULL DEFAULT 0,
    sku         VARCHAR(30)  NULL,
    familia     ENUM('tortas','cupcakes','galletas','postres','hojaldres','panaderia')
                NOT NULL DEFAULT 'tortas',
    peso_g      INT NULL,
    activo      BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- NULL-able: el catálogo existía antes que la tabla `proveedores`.
    -- RESTRICT respalda en la base de datos el 409 que devuelve
    -- DELETE /api/proveedores/{id} cuando todavía surte productos.
    proveedor_id INT NULL,
    CONSTRAINT uq_productos_sku UNIQUE (sku),
    CONSTRAINT chk_productos_precio CHECK (precio >= 0),
    CONSTRAINT chk_productos_stock CHECK (stock >= 0),
    CONSTRAINT fk_productos_proveedor FOREIGN KEY (proveedor_id)
        REFERENCES proveedores(id) ON DELETE RESTRICT,
    INDEX ix_productos_proveedor (proveedor_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Migración para bases de datos ya creadas con una versión anterior del
-- esquema (MySQL 8 / MariaDB 10.5+ soportan IF NOT EXISTS aquí; si tu
-- versión no lo acepta, ejecuta la línea sin esa cláusula):
-- ALTER TABLE productos ADD COLUMN IF NOT EXISTS proveedor_id INT NULL,
--     ADD CONSTRAINT fk_productos_proveedor FOREIGN KEY (proveedor_id)
--     REFERENCES proveedores(id) ON DELETE RESTRICT;

-- ---------------------------------------------------------------------
-- 6. servicios
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS servicios (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    nombre            VARCHAR(80)  NOT NULL,
    descripcion       VARCHAR(255) NOT NULL,
    precio            DECIMAL(10,2) NOT NULL DEFAULT 0,
    duracion_minutos  INT NULL,
    imagen            VARCHAR(120) NULL,
    orden             INT NOT NULL DEFAULT 0,
    codigo            VARCHAR(30) NULL,
    activo            BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_servicios_codigo UNIQUE (codigo),
    CONSTRAINT chk_servicios_precio CHECK (precio >= 0),
    CONSTRAINT chk_servicios_duracion CHECK (duracion_minutos IS NULL OR duracion_minutos > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 7. carritos (uno por usuario)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS carritos (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    creado_en  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_carrito_usuario UNIQUE (usuario_id),
    CONSTRAINT fk_carritos_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 8. carrito_items
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS carrito_items (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    carrito_id  INT NOT NULL,
    producto_id INT NOT NULL,
    cantidad    INT NOT NULL DEFAULT 1,
    agregado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_carrito_producto UNIQUE (carrito_id, producto_id),
    CONSTRAINT chk_carrito_items_cantidad CHECK (cantidad > 0),
    CONSTRAINT fk_carrito_items_carrito
        FOREIGN KEY (carrito_id) REFERENCES carritos(id) ON DELETE CASCADE,
    CONSTRAINT fk_carrito_items_producto
        FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 9. cupones
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cupones (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    codigo         VARCHAR(30) NOT NULL,
    tipo           ENUM('porcentaje','monto_fijo') NOT NULL,
    valor          DECIMAL(10,2) NOT NULL,
    monto_minimo   DECIMAL(10,2) NOT NULL DEFAULT 0,
    usos_maximos   INT NULL,
    usos_actuales  INT NOT NULL DEFAULT 0,
    valido_desde   DATETIME NOT NULL,
    valido_hasta   DATETIME NOT NULL,
    activo         BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cupon_codigo UNIQUE (codigo),
    CONSTRAINT chk_cupones_valor CHECK (valor >= 0),
    CONSTRAINT chk_cupones_monto_minimo CHECK (monto_minimo >= 0),
    CONSTRAINT chk_cupones_usos_actuales CHECK (usos_actuales >= 0),
    CONSTRAINT chk_cupones_vigencia CHECK (valido_hasta >= valido_desde)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 10. pedidos
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pedidos (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id        INT NOT NULL,
    estado            ENUM('pendiente','pagado','enviado','entregado','cancelado')
                      NOT NULL DEFAULT 'pendiente',
    subtotal          DECIMAL(10,2) NOT NULL,
    descuento         DECIMAL(10,2) NOT NULL DEFAULT 0,
    cupon_codigo      VARCHAR(30) NULL,
    total             DECIMAL(10,2) NOT NULL,
    direccion_envio   VARCHAR(150) NOT NULL,
    telefono_contacto VARCHAR(15) NOT NULL,
    metodo_pago       ENUM('tarjeta','transferencia','contraentrega') NOT NULL,
    idempotency_key   VARCHAR(100) NULL,
    creado_en         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pedido_idempotencia UNIQUE (usuario_id, idempotency_key),
    CONSTRAINT chk_pedidos_subtotal CHECK (subtotal >= 0),
    CONSTRAINT chk_pedidos_descuento CHECK (descuento >= 0),
    CONSTRAINT chk_pedidos_total CHECK (total >= 0),
    CONSTRAINT chk_pedidos_subtotal_descuento CHECK (subtotal >= descuento),
    CONSTRAINT fk_pedidos_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 11. pedido_items (líneas congeladas al momento de la compra)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pedido_items (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id       INT NOT NULL,
    producto_id     INT NOT NULL,
    titulo          VARCHAR(80) NOT NULL,
    precio_unitario DECIMAL(10,2) NOT NULL,
    cantidad        INT NOT NULL,
    CONSTRAINT chk_pedido_items_cantidad CHECK (cantidad > 0),
    CONSTRAINT chk_pedido_items_precio CHECK (precio_unitario >= 0),
    CONSTRAINT fk_pedido_items_pedido
        FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
    CONSTRAINT fk_pedido_items_producto
        FOREIGN KEY (producto_id) REFERENCES productos(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 12. mensajes_contacto
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mensajes_contacto (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    nombre    VARCHAR(60) NOT NULL,
    correo    VARCHAR(60) NOT NULL,
    mensaje   TEXT NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 13. pagos (módulo de pagos — Wompi Colombia, Sandbox)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pagos (
    id                        INT AUTO_INCREMENT PRIMARY KEY,
    referencia                VARCHAR(60)  NOT NULL,
    proveedor                 VARCHAR(30)  NOT NULL DEFAULT 'wompi',
    id_transaccion_proveedor  VARCHAR(100) NULL,
    monto_centavos            BIGINT       NOT NULL,
    moneda                    VARCHAR(3)   NOT NULL DEFAULT 'COP',
    estado                    ENUM('PENDING','APPROVED','DECLINED','VOIDED','ERROR','EXPIRED') NOT NULL DEFAULT 'PENDING',
    metodo_pago               VARCHAR(30)  NULL,
    correo_cliente            VARCHAR(120) NOT NULL,
    nombre_cliente            VARCHAR(120) NULL,
    descripcion               VARCHAR(255) NULL,
    pedido_id                 INT          NULL,
    creado_por_usuario_id     INT          NULL,
    url_redireccion           VARCHAR(500) NULL,
    url_checkout              VARCHAR(500) NULL,
    respuesta_cruda           JSON         NULL,
    payload_webhook           JSON         NULL,
    idempotency_key           VARCHAR(100) NULL,
    creado_en                 TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_pagos_referencia UNIQUE (referencia),
    CONSTRAINT uq_pagos_idempotency_key UNIQUE (idempotency_key),
    CONSTRAINT fk_pagos_pedido
        FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE SET NULL,
    CONSTRAINT fk_pagos_usuario
        FOREIGN KEY (creado_por_usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_pagos_id_transaccion_proveedor ON pagos (id_transaccion_proveedor);
CREATE INDEX ix_pagos_estado ON pagos (estado);
CREATE INDEX ix_pagos_creado_en ON pagos (creado_en);

-- ---------------------------------------------------------------------
-- 14. ventas / detalle_ventas (Quinto Avance — módulo de gestión comercial)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ventas (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id   INT NOT NULL,
    vendedor_id  INT NULL,
    pedido_id    INT NULL,
    subtotal     DECIMAL(10,2) NOT NULL DEFAULT 0,
    descuento    DECIMAL(10,2) NOT NULL DEFAULT 0,
    impuestos    DECIMAL(10,2) NOT NULL DEFAULT 0,
    total        DECIMAL(10,2) NOT NULL DEFAULT 0,
    estado       ENUM('completada','anulada') NOT NULL DEFAULT 'completada',
    notas        VARCHAR(255) NULL,
    creado_en    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ventas_pedido UNIQUE (pedido_id),
    CONSTRAINT fk_ventas_cliente FOREIGN KEY (cliente_id) REFERENCES usuarios(id),
    CONSTRAINT fk_ventas_vendedor FOREIGN KEY (vendedor_id) REFERENCES usuarios(id),
    CONSTRAINT fk_ventas_pedido FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
    CONSTRAINT chk_ventas_subtotal CHECK (subtotal >= 0),
    CONSTRAINT chk_ventas_descuento CHECK (descuento >= 0),
    CONSTRAINT chk_ventas_impuestos CHECK (impuestos >= 0),
    CONSTRAINT chk_ventas_total CHECK (total >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS detalle_ventas (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    venta_id         INT NOT NULL,
    producto_id      INT NULL,
    servicio_id      INT NULL,
    nombre           VARCHAR(80) NOT NULL,
    precio_unitario  DECIMAL(10,2) NOT NULL,
    cantidad         INT NOT NULL,
    subtotal         DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_detalle_ventas_venta FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
    CONSTRAINT fk_detalle_ventas_producto FOREIGN KEY (producto_id) REFERENCES productos(id),
    CONSTRAINT fk_detalle_ventas_servicio FOREIGN KEY (servicio_id) REFERENCES servicios(id),
    CONSTRAINT chk_detalle_ventas_cantidad CHECK (cantidad > 0),
    CONSTRAINT chk_detalle_ventas_precio CHECK (precio_unitario >= 0),
    CONSTRAINT chk_detalle_ventas_producto_xor_servicio CHECK (
        (producto_id IS NOT NULL AND servicio_id IS NULL) OR
        (producto_id IS NULL AND servicio_id IS NOT NULL)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_ventas_cliente ON ventas (cliente_id);
CREATE INDEX ix_ventas_creado_en ON ventas (creado_en);

-- ---------------------------------------------------------------------
-- 15. facturas / detalle_facturas (Quinto Avance)
-- ---------------------------------------------------------------------
-- Sin columna `cliente_id`: sería una dependencia transitiva
-- (factura → venta → cliente) que duplica `ventas.cliente_id` sin
-- necesidad, ya que toda factura nace de una venta (venta_id NOT NULL
-- UNIQUE) — ver docs/NORMALIZACION-BD.md. El cliente se obtiene con un
-- JOIN a `ventas` (así lo hace la capa ORM, con un association_proxy).
CREATE TABLE IF NOT EXISTS facturas (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    numero      VARCHAR(20) NOT NULL,
    venta_id    INT NOT NULL,
    subtotal    DECIMAL(10,2) NOT NULL,
    impuestos   DECIMAL(10,2) NOT NULL DEFAULT 0,
    total       DECIMAL(10,2) NOT NULL,
    estado      ENUM('emitida','anulada') NOT NULL DEFAULT 'emitida',
    creado_en   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_facturas_numero UNIQUE (numero),
    CONSTRAINT uq_facturas_venta UNIQUE (venta_id),
    CONSTRAINT fk_facturas_venta FOREIGN KEY (venta_id) REFERENCES ventas(id),
    CONSTRAINT chk_facturas_subtotal CHECK (subtotal >= 0),
    CONSTRAINT chk_facturas_impuestos CHECK (impuestos >= 0),
    CONSTRAINT chk_facturas_total CHECK (total >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS detalle_facturas (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    factura_id       INT NOT NULL,
    nombre           VARCHAR(80) NOT NULL,
    precio_unitario  DECIMAL(10,2) NOT NULL,
    cantidad         INT NOT NULL,
    subtotal         DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_detalle_facturas_factura FOREIGN KEY (factura_id) REFERENCES facturas(id) ON DELETE CASCADE,
    CONSTRAINT chk_detalle_facturas_cantidad CHECK (cantidad > 0),
    CONSTRAINT chk_detalle_facturas_precio CHECK (precio_unitario >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 16. pqr (Quinto Avance — Peticiones, Quejas y Reclamos)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pqr (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id          INT NOT NULL,
    tipo                ENUM('peticion','queja','reclamo','sugerencia') NOT NULL DEFAULT 'peticion',
    asunto              VARCHAR(120) NOT NULL,
    descripcion         TEXT NOT NULL,
    estado              ENUM('pendiente','en_proceso','respondida','cerrada') NOT NULL DEFAULT 'pendiente',
    respuesta           TEXT NULL,
    respondido_por_id   INT NULL,
    creado_en           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_pqr_cliente FOREIGN KEY (cliente_id) REFERENCES usuarios(id),
    CONSTRAINT fk_pqr_respondido_por FOREIGN KEY (respondido_por_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_pqr_estado ON pqr (estado);

-- ---------------------------------------------------------------------
-- 17. conversaciones / mensajes (Quinto Avance — Chatbot con IA)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversaciones (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id  INT NULL,
    sesion_id   VARCHAR(64) NULL,
    creado_en   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_conversaciones_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mensajes (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    conversacion_id   INT NOT NULL,
    rol               ENUM('usuario','asistente') NOT NULL,
    contenido         TEXT NOT NULL,
    creado_en         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_mensajes_conversacion FOREIGN KEY (conversacion_id) REFERENCES conversaciones(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- Datos semilla mínimos de roles y permisos (opcional, pero recomendado
-- para que el panel de administración tenga algo que listar en
-- GET /api/roles desde el primer arranque).
-- =====================================================================
INSERT IGNORE INTO roles (nombre, descripcion) VALUES
    ('admin',    'Control total: usuarios, productos, servicios, pedidos, cupones y mensajes.'),
    ('empleado', 'Gestión operativa de productos, servicios, usuarios y pedidos, sin cupones.'),
    ('cliente',  'Acceso a su propio perfil, carrito, pedidos y catálogo público.');

INSERT IGNORE INTO permisos (clave, descripcion) VALUES
    ('usuarios.gestionar',   'Crear, editar, cambiar estado y eliminar usuarios.'),
    ('productos.gestionar',  'Crear, editar, cambiar estado y eliminar productos.'),
    ('servicios.gestionar',  'Crear, editar, cambiar estado y eliminar servicios.'),
    ('pedidos.gestionar',    'Ver y cambiar el estado de los pedidos de cualquier cliente.'),
    ('cupones.gestionar',    'Crear, editar, cambiar estado y eliminar cupones.'),
    ('contacto.gestionar',   'Ver y eliminar mensajes de contacto recibidos.'),
    ('proveedores.gestionar','Crear, editar, suspender y eliminar proveedores.');

-- admin: todos los permisos
INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles r, permisos p WHERE r.nombre = 'admin';

-- empleado: todo menos cupones
INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles r, permisos p
WHERE r.nombre = 'empleado' AND p.clave <> 'cupones.gestionar';

-- =====================================================================
-- Fin del script. Para crear tu primer usuario administrador:
--   1. Regístrate normalmente desde el formulario del frontend
--      (quedará con rol = 'cliente').
--   2. Verifica la cuenta (revisa la consola de uvicorn, ahí se
--      imprime el código OTP de verificación en desarrollo).
--   3. Ejecuta:
--        UPDATE usuarios SET rol = 'admin' WHERE correo = 'tu-correo@ejemplo.com';
-- =====================================================================
