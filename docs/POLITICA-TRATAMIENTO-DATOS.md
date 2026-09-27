# Política de Tratamiento de Datos Personales — Dulce Esencia Pastelería

Última actualización: ver control de versiones al final de este documento.

En cumplimiento de la **Ley 1581 de 2012** ("Ley de Habeas Data") y el
**Decreto 1377 de 2013** de Colombia, Dulce Esencia Pastelería informa
a sus clientes y usuarios cómo recolecta, usa, almacena y protege sus
datos personales al usar esta plataforma.

## 1. Responsable del tratamiento

Dulce Esencia Pastelería, a través de esta aplicación web
(`backend` FastAPI + `frontend` React), actúa como responsable del
tratamiento de los datos personales que el usuario suministra al
registrarse, comprar, contactar a soporte (PQR) o interactuar con el
chatbot.

## 2. Datos que se recolectan

Al usar la plataforma se pueden recolectar:

- **Datos de identificación**: nombre, apellido, tipo y número de documento.
- **Datos de contacto**: correo electrónico, teléfono, dirección de envío.
- **Datos de la relación comercial**: historial de pedidos, productos
  comprados, cupones usados, PQR radicadas.
- **Datos de pago**: este backend **nunca almacena** número completo de
  tarjeta, CVV ni claves — el pago se procesa directamente en el
  Web Checkout de Wompi (ver `docs/modulo-pagos-wompi.md`); solo se
  guarda el identificador de la transacción y su estado.
- **Datos técnicos mínimos** para seguridad (registro de intentos de
  inicio de sesión, para el limitador de tasa — ver `app/rate_limit.py`).

## 3. Finalidad del tratamiento

Los datos se usan exclusivamente para:

1. Crear y administrar la cuenta del usuario.
2. Procesar pedidos, pagos, facturación y entregas.
3. Responder solicitudes, quejas o reclamos (PQR).
4. Enviar notificaciones sobre el estado de sus pedidos (confirmación,
   pago, envío, entrega o cancelación).
5. Cumplir obligaciones legales y contractuales.

No se usan los datos personales para fines distintos a los aquí
descritos sin el consentimiento adicional del titular.

## 4. Derechos del titular

Como titular de los datos, el usuario tiene derecho a:

- Conocer, actualizar y rectificar sus datos personales.
- Solicitar prueba de la autorización otorgada.
- Ser informado sobre el uso dado a sus datos.
- Presentar quejas ante la Superintendencia de Industria y Comercio (SIC).
- Revocar la autorización y/o solicitar la supresión de sus datos,
  cuando no exista un deber legal o contractual que impida eliminarlos
  (por ejemplo, los registros contables de una compra ya facturada).
- Acceder gratuitamente a sus datos.

Estos derechos se pueden ejercer desde el panel del usuario (edición
de perfil) o escribiendo a través del módulo de PQR de la plataforma.

## 5. Cómo se protegen los datos

- Las contraseñas se almacenan siempre con hash (nunca en texto
  plano) — ver `app/auth.py`.
- Los datos de pago sensibles ni siquiera transitan por este backend:
  el titular los digita directamente en el Web Checkout de Wompi.
- El acceso a los datos dentro de la plataforma está restringido por
  rol (`cliente`, `empleado`, `admin`) — ver `app/auth.py::requiere_rol`.
- Las conexiones a la base de datos en producción usan TLS (ver
  `docs/DEPLOY.md`, sección "TLS hacia TiDB").

## 6. Aceptación

Al marcar la casilla de aceptación en el formulario de registro, el
titular manifiesta que ha leído esta política y autoriza el
tratamiento de sus datos personales para las finalidades descritas.
El backend registra la fecha exacta de esa aceptación
(`usuarios.tratamiento_datos_aceptado_en`) como prueba del
consentimiento — ver `app/routes/usuarios.py::registrar_usuario`.

## 7. Vigencia

Esta política aplica desde su publicación y permanecerá vigente
mientras la plataforma esté en operación. Cualquier cambio sustancial
se comunicará a los usuarios registrados.

---

**Nota para quien mantenga este proyecto**: este documento es una base
razonable para un proyecto académico/de práctica. Si el negocio llega
a operar comercialmente de verdad, se recomienda que un abogado
revise el texto final antes de publicarlo, y evaluar además la
obligación de **facturación electrónica ante la DIAN** (Resolución
DIAN vigente para el régimen del comercio electrónico), que es un
requisito legal aparte de esta política y que este proyecto todavía
no implementa.
