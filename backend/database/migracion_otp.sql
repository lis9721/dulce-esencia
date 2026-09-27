-- ---------------------------------------------------------------------
-- Migración: verificación de correo y restablecimiento de contraseña
-- basados en OTP (código numérico de 6 dígitos), en reemplazo del
-- esquema anterior basado en enlaces con token largo.
--
-- Ejecuta esto SOLO si tu base de datos ya existía con las columnas
-- `reset_token_hash` / `reset_token_expira` /
-- `verificacion_token_hash` / `verificacion_token_expira` (esquema
-- anterior). Si vas a crear la base de datos desde cero, usa
-- schema_fastapi.sql directamente: ya incluye las columnas nuevas.
--
-- Uso:
--   mysql -u root -p essentia_db_fastapi < database/migracion_otp.sql
-- ---------------------------------------------------------------------

USE essentia_db_fastapi;

-- 1) Renombra las columnas de "token de enlace" a "hash de OTP" y
--    conserva su contenido — cualquier token pendiente de esa forma
--    de todas formas se invalida en la práctica: los tokens viejos
--    eran hex de 64 caracteres, nunca coincidirán con el hash de un
--    código de 6 dígitos, así que no hace falta vaciarlas a mano.
ALTER TABLE usuarios
    CHANGE COLUMN reset_token_hash          reset_otp_hash          VARCHAR(255) NULL,
    CHANGE COLUMN reset_token_expira        reset_otp_expira        DATETIME     NULL,
    CHANGE COLUMN verificacion_token_hash   verificacion_otp_hash   VARCHAR(255) NULL,
    CHANGE COLUMN verificacion_token_expira verificacion_otp_expira DATETIME     NULL;

-- 2) Agrega los contadores de intentos fallidos (no existían en el
--    esquema anterior, porque un token de 64 caracteres no necesitaba
--    freno de fuerza bruta por intentos: un código de 6 dígitos sí).
ALTER TABLE usuarios
    ADD COLUMN reset_otp_intentos        INT NOT NULL DEFAULT 0 AFTER reset_otp_expira,
    ADD COLUMN verificacion_otp_intentos INT NOT NULL DEFAULT 0 AFTER verificacion_otp_expira;

-- 3) Por seguridad, invalida cualquier código/enlace pendiente que
--    haya quedado a mitad de camino: mejor que un usuario con un
--    proceso interrumpido pida un código nuevo (ya en formato OTP) a
--    dejar en la base de datos un hash del esquema anterior.
UPDATE usuarios
SET reset_otp_hash = NULL, reset_otp_expira = NULL, reset_otp_intentos = 0
WHERE reset_otp_hash IS NOT NULL;

UPDATE usuarios
SET verificacion_otp_hash = NULL, verificacion_otp_expira = NULL, verificacion_otp_intentos = 0
WHERE verificacion_otp_hash IS NOT NULL AND verificado = FALSE;
