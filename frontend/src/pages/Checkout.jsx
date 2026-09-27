import { useMemo, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import Input from "../components/ui/Input";
import Select from "../components/ui/Select";
import Button from "../components/ui/Button";
import Icon from "../components/ui/Icon";
import ICON_PATHS from "../components/ui/iconPaths";
import useForm from "../hooks/useForm";
import { useCart } from "../hooks/useCart";
import { useAuth } from "../hooks/useAuth";
import useDocumentTitle from "../hooks/useDocumentTitle";
import { validarDireccionEnvio, validarTelefono, validarSeleccion } from "../utils/validators";
import { formatearPrecio } from "../utils/formato";
import { crearPedido } from "../utils/api";
import { iniciarPagoConWompi } from "../utils/pagos";

const OPCIONES_METODO_PAGO = [
  { value: "tarjeta", label: "Tarjeta" },
  { value: "transferencia", label: "Transferencia" },
  { value: "contraentrega", label: "Pago contraentrega" },
];

const validadores = {
  direccionEnvio: validarDireccionEnvio,
  telefonoContacto: validarTelefono,
  metodoPago: validarSeleccion,
};

function Checkout() {
  useDocumentTitle("Checkout", "Confirma tu dirección de envío y método de pago.", "/checkout", true);

  const navigate = useNavigate();
  const { usuario } = useAuth();
  const {
    items,
    total,
    cargando: cargandoCarrito,
    recargar,
    cuponAplicado,
    totalConDescuento,
    quitarCupon,
  } = useCart();

  const { values, errors, touched, handleChange, handleBlur, validateAll } = useForm(
    {
      direccionEnvio: usuario?.direccion || "",
      telefonoContacto: usuario?.telefono || "",
      metodoPago: "",
    },
    validadores
  );
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");
  const [productoConflicto, setProductoConflicto] = useState(null);

  // Buena práctica #4 (idempotencia): UNA sola clave por visita a
  // /checkout, generada acá y reenviada en CADA intento (incluidos los
  // reintentos tras un error de red). Inicialización perezosa de
  // useState en vez de useRef: nunca se vuelve a llamar tras el primer
  // render y no necesita disparar uno nuevo, así que no hace falta el
  // setter.
  const [idempotencyKey] = useState(() => crypto.randomUUID());

  const hayProductosBloqueados = items.some(
    (item) => item.activo === 0 || item.activo === false || item.cantidad > item.stock
  );

  const handleSubmit = async (evento) => {
    evento.preventDefault();
    setError("");
    setProductoConflicto(null);
    if (!validateAll()) return;

    // El botón se deshabilita mientras `enviando` es true (ver más
    // abajo): eso ya evita el doble clic. El Idempotency-Key es la
    // segunda capa, para el caso de un reintento de red genuino
    // (el usuario cierra y reabre la pestaña, por ejemplo).
    setEnviando(true);
    try {
      const pedido = await crearPedido(
        {
          direccionEnvio: values.direccionEnvio.trim(),
          telefonoContacto: values.telefonoContacto.trim(),
          metodoPago: values.metodoPago,
          // El backend vuelve a validar el cupón contra el subtotal
          // recalculado en la misma transacción (nunca confía en el
          // descuento que ya mostramos acá) y es quien de verdad
          // incrementa `usos_actuales` al confirmar el pedido.
          ...(cuponAplicado ? { cuponCodigo: cuponAplicado.codigo } : {}),
        },
        idempotencyKey
      );
      quitarCupon(); // ya se consumió (o se descartó) junto con el carrito
      await recargar(); // el backend ya vació el carrito: esto solo refresca el estado local

      // Tarjeta: se cobra con Wompi (Web Checkout). Transferencia y
      // contraentrega no pasan por la pasarela.
      if (values.metodoPago === "tarjeta") {
        try {
          await iniciarPagoConWompi(pedido, usuario, idempotencyKey);
          return; // el navegador se va a Wompi; al volver llega a /pago/resultado
        } catch (errPago) {
          // El pedido YA existe (pendiente): se lleva al detalle, donde
          // puede reintentar el pago con el botón "Pagar con tarjeta".
          navigate(`/pedidos/${pedido.id}`, {
            replace: true,
            state: { reciénCreado: true, errorPago: errPago.message },
          });
          return;
        }
      }

      navigate(`/pedidos/${pedido.id}`, { replace: true, state: { reciénCreado: true } });
    } catch (err) {
      if (err.status === 409 && err.productoId) {
        setProductoConflicto({ mensaje: err.message, productoId: err.productoId });
      } else {
        setError(err.message);
      }
      setEnviando(false);
    }
  };

  const resumen = useMemo(() => ({ items, total }), [items, total]);

  if (!cargandoCarrito && items.length === 0) {
    return (
      <main className="mx-auto flex min-h-[60vh] max-w-xl flex-col items-center justify-center gap-4 px-4 py-10 text-center">
        <Icon path={ICON_PATHS.cart} className="h-10 w-10 text-primary/30" />
        <p className="text-primary/70">Tu carrito está vacío, no hay nada que pagar todavía.</p>
        <Link
          to="/"
          className="inline-block rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-cream transition hover:bg-primary-dark"
        >
          Ver productos
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-[60vh] max-w-3xl px-4 py-10 sm:px-6">
      <h1 className="text-2xl font-bold text-primary sm:text-3xl">Confirmar pedido</h1>
      <p className="mt-1 text-sm text-primary/70">Revisa tu envío y confirma para completar la compra.</p>

      <div className="mt-8 grid gap-8 sm:grid-cols-5">
        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4 sm:col-span-3">
          <Input
            label="Dirección de envío"
            name="direccionEnvio"
            required
            maxLength={150}
            value={values.direccionEnvio}
            onChange={handleChange}
            onBlur={handleBlur}
            error={errors.direccionEnvio}
            touched={touched.direccionEnvio}
            placeholder="Calle, número, barrio, referencias..."
          />
          <Input
            label="Teléfono de contacto"
            name="telefonoContacto"
            required
            maxLength={15}
            value={values.telefonoContacto}
            onChange={handleChange}
            onBlur={handleBlur}
            error={errors.telefonoContacto}
            touched={touched.telefonoContacto}
          />
          <Select
            label="Método de pago"
            name="metodoPago"
            required
            value={values.metodoPago}
            onChange={handleChange}
            onBlur={handleBlur}
            error={errors.metodoPago}
            touched={touched.metodoPago}
            options={OPCIONES_METODO_PAGO}
          />

          {hayProductosBloqueados && (
            <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">
              Hay productos en tu carrito sin stock suficiente.{" "}
              <Link to="/carrito" className="font-medium underline underline-offset-2">
                Ajústalos antes de continuar
              </Link>
              .
            </p>
          )}

          {productoConflicto && (
            <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">
              {productoConflicto.mensaje}{" "}
              <Link to="/carrito" className="font-medium underline underline-offset-2">
                Revisa tu carrito
              </Link>
              .
            </p>
          )}
          {error && <p className="rounded-lg bg-peligro px-3 py-2 text-sm text-peligro-fuerte">{error}</p>}

          <Button type="submit" disabled={enviando || hayProductosBloqueados} fullWidth>
            {enviando ? "Confirmando..." : `Confirmar pedido · ${formatearPrecio(totalConDescuento)}`}
          </Button>
        </form>

        <aside className="sm:col-span-2">
          <div className="rounded-2xl border border-beige/60 bg-cream p-5">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-primary/70">
              Resumen del pedido
            </h2>
            <ul className="flex flex-col gap-3">
              {resumen.items.map((item) => (
                <li key={item.productoId} className="flex justify-between gap-3 text-sm">
                  <span className="text-primary/80">
                    {item.titulo} <span className="text-primary/70">× {item.cantidad}</span>
                  </span>
                  <span className="whitespace-nowrap font-medium text-primary">
                    {formatearPrecio(item.subtotal)}
                  </span>
                </li>
              ))}
            </ul>
            {cuponAplicado && (
              <>
                <div className="mt-4 flex justify-between border-t border-beige/60 pt-3 text-sm text-primary/70">
                  <span>Subtotal</span>
                  <span>{formatearPrecio(resumen.total)}</span>
                </div>
                <div className="mt-1 flex justify-between text-sm text-exito-fuerte">
                  <span>Descuento ({cuponAplicado.codigo})</span>
                  <span>-{formatearPrecio(cuponAplicado.descuento)}</span>
                </div>
              </>
            )}
            <div
              className={`flex justify-between text-base font-bold text-primary ${
                cuponAplicado ? "mt-1 pt-1" : "mt-4 border-t border-beige/60 pt-3"
              }`}
            >
              <span>Total</span>
              <span>{formatearPrecio(totalConDescuento)}</span>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}

export default Checkout;
