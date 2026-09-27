import { createContext, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import {
  obtenerCarrito,
  agregarAlCarrito,
  actualizarCantidadCarrito,
  quitarDelCarrito,
  vaciarCarrito as vaciarCarritoApi,
  fusionarCarrito,
  validarCupon,
} from "../utils/api";

const CartContext = createContext(null);

const CLAVE_LOCALSTORAGE = "essentia:carrito-invitado";

/**
 * Carrito de INVITADO (sin sesión): array de
 * { productoId, cantidad, titulo, imagen, precio, stock }.
 * Se guarda una "foto" del producto (no solo el id) para poder pintar
 * la página /carrito sin depender del backend mientras no hay sesión
 * — el plan es explícito en que "nadie obliga a loguearse solo para
 * mirar el carrito".
 */
function leerCarritoInvitado() {
  try {
    const crudo = localStorage.getItem(CLAVE_LOCALSTORAGE);
    const items = crudo ? JSON.parse(crudo) : [];
    return Array.isArray(items) ? items : [];
  } catch {
    return [];
  }
}

function guardarCarritoInvitado(items) {
  try {
    localStorage.setItem(CLAVE_LOCALSTORAGE, JSON.stringify(items));
  } catch {
    // localStorage puede fallar (modo privado del navegador, cuota
    // llena, etc.). El carrito de invitado es una comodidad, no algo
    // crítico: se ignora en silencio en vez de romper la UI por esto.
  }
}

/** Le agrega `subtotal` a cada item de invitado y devuelve también el total, con la misma forma que responde el backend. */
function construirVistaInvitado(items) {
  const conSubtotal = items.map((item) => ({
    ...item,
    subtotal: Math.round((Number(item.precio) || 0) * (Number(item.cantidad) || 0) * 100) / 100,
  }));
  const total = Math.round(conSubtotal.reduce((acc, item) => acc + item.subtotal, 0) * 100) / 100;
  return { items: conSubtotal, total };
}

/**
 * CartProvider
 * Junto con AuthProvider (ver main.jsx, que lo envuelve), le da a
 * cualquier componente acceso al estado del carrito: items, total,
 * cantidadTotal (para el badge del Header) y las acciones
 * agregar/actualizar/quitar/vaciar.
 *
 * Con sesión iniciada, la fuente de verdad es el backend (GET/POST/PUT/
 * DELETE /api/carrito). Sin sesión, vive en localStorage. La transición
 * de invitado -> logueado dispara UNA fusión automática (Flujo 1 del
 * plan de tienda), no en cada render.
 */
export function CartProvider({ children }) {
  const { isAuthenticated, cargando: cargandoSesion } = useAuth();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");
  const sesionAnterior = useRef(isAuthenticated);
  const fusionEnCurso = useRef(false);

  // Cupón aplicado (Fase 3, Flujo 6): { codigo, descuento } o null.
  // Vive acá (no en Carrito.jsx) para que Checkout.jsx, en otra página,
  // pueda leer el mismo cupón sin que el cliente tenga que volver a
  // escribirlo. `totalConDescuento` nunca se guarda como un número
  // fijo: siempre se resta `descuento` sobre el `total` ACTUAL, igual
  // que el backend recalcula todo en el momento del checkout.
  const [cuponAplicado, setCuponAplicado] = useState(null);
  const totalAnteriorParaCupon = useRef(total);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      const datos = await obtenerCarrito();
      setItems(datos.items);
      setTotal(datos.total);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  }, []);

  // Reacciona a cambios en la sesión: recién logueado -> fusiona el
  // carrito de invitado UNA sola vez; con sesión ya establecida ->
  // trae el carrito real; sin sesión -> arma la vista desde
  // localStorage.
  useEffect(() => {
    if (cargandoSesion) return; // espera a que AuthProvider resuelva quién es

    const veniaDeInvitado = !sesionAnterior.current;
    sesionAnterior.current = isAuthenticated;

    if (!isAuthenticated) {
      const { items: itemsInvitado, total: totalInvitado } = construirVistaInvitado(leerCarritoInvitado());
      setItems(itemsInvitado);
      setTotal(totalInvitado);
      return;
    }

    if (veniaDeInvitado && !fusionEnCurso.current) {
      const pendientes = leerCarritoInvitado();
      fusionEnCurso.current = true;
      setCargando(true);
      const promesa =
        pendientes.length > 0
          ? fusionarCarrito(pendientes.map(({ productoId, cantidad }) => ({ productoId, cantidad })))
          : obtenerCarrito();

      promesa
        .then((datos) => {
          setItems(datos.items);
          setTotal(datos.total);
          guardarCarritoInvitado([]);
        })
        .catch((err) => setError(err.message))
        .finally(() => {
          fusionEnCurso.current = false;
          setCargando(false);
        });
      return;
    }

    recargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- sesionAnterior/fusionEnCurso son refs, no disparan re-render y no deben ir en las dependencias.
  }, [isAuthenticated, cargandoSesion, recargar]);

  /**
   * @param {{id:number, titulo:string, imagen:string, precio:number, stock:number}} producto
   */
  const agregar = useCallback(
    async (producto, cantidad = 1) => {
      if (isAuthenticated) {
        await agregarAlCarrito(producto.id, cantidad);
        await recargar();
        return;
      }
      const actuales = leerCarritoInvitado();
      const indice = actuales.findIndex((item) => item.productoId === producto.id);
      if (indice >= 0) {
        actuales[indice] = {
          ...actuales[indice],
          cantidad: Math.min(actuales[indice].cantidad + cantidad, producto.stock),
          precio: producto.precio,
          stock: producto.stock,
        };
      } else {
        actuales.push({
          productoId: producto.id,
          cantidad: Math.min(cantidad, producto.stock),
          titulo: producto.titulo,
          imagen: producto.imagen,
          precio: producto.precio,
          stock: producto.stock,
        });
      }
      guardarCarritoInvitado(actuales);
      setItems(construirVistaInvitado(actuales).items);
      setTotal(construirVistaInvitado(actuales).total);
    },
    [isAuthenticated, recargar]
  );

  const actualizar = useCallback(
    async (productoId, cantidad) => {
      if (isAuthenticated) {
        await actualizarCantidadCarrito(productoId, cantidad);
        await recargar();
        return;
      }
      const actuales = leerCarritoInvitado().map((item) =>
        item.productoId === productoId ? { ...item, cantidad } : item
      );
      guardarCarritoInvitado(actuales);
      const vista = construirVistaInvitado(actuales);
      setItems(vista.items);
      setTotal(vista.total);
    },
    [isAuthenticated, recargar]
  );

  const quitar = useCallback(
    async (productoId) => {
      if (isAuthenticated) {
        await quitarDelCarrito(productoId);
        await recargar();
        return;
      }
      const actuales = leerCarritoInvitado().filter((item) => item.productoId !== productoId);
      guardarCarritoInvitado(actuales);
      const vista = construirVistaInvitado(actuales);
      setItems(vista.items);
      setTotal(vista.total);
    },
    [isAuthenticated, recargar]
  );

  const vaciar = useCallback(async () => {
    if (isAuthenticated) {
      await vaciarCarritoApi();
      setItems([]);
      setTotal(0);
      setCuponAplicado(null);
      return;
    }
    guardarCarritoInvitado([]);
    setItems([]);
    setTotal(0);
    setCuponAplicado(null);
  }, [isAuthenticated]);

  // Si el subtotal cambia después de aplicar un cupón (se editó una
  // cantidad, se quitó un producto, cambió el precio al recargar,
  // etc.), el descuento validado ya no es confiable — el monto mínimo
  // pudo dejar de cumplirse, por ejemplo. En vez de arrastrar un
  // descuento potencialmente inválido hasta el checkout (donde el
  // backend igual lo recalcularía distinto), se limpia acá mismo y se
  // le pide al cliente que lo vuelva a aplicar.
  useEffect(() => {
    if (cuponAplicado && total !== totalAnteriorParaCupon.current) {
      setCuponAplicado(null);
    }
    totalAnteriorParaCupon.current = total;
  }, [total, cuponAplicado]);

  /**
   * Valida el código contra el subtotal actual y, si aplica, lo deja
   * guardado como `cuponAplicado`. Lanza el mismo Error que
   * validarCupon (con el motivo del backend) si no aplica, para que
   * quien llame lo muestre en su propio formulario.
   */
  const aplicarCupon = useCallback(
    async (codigo) => {
      const respuesta = await validarCupon(codigo, total);
      setCuponAplicado({ codigo: respuesta.codigo, descuento: respuesta.descuento });
      return respuesta;
    },
    [total]
  );

  const quitarCupon = useCallback(() => setCuponAplicado(null), []);

  const totalConDescuento = useMemo(() => {
    if (!cuponAplicado) return total;
    return Math.max(0, Math.round((total - cuponAplicado.descuento) * 100) / 100);
  }, [total, cuponAplicado]);

  const cantidadTotal = useMemo(
    () => items.reduce((acumulado, item) => acumulado + Number(item.cantidad || 0), 0),
    [items]
  );

  const value = useMemo(
    () => ({
      items,
      total,
      cantidadTotal,
      cargando,
      error,
      esInvitado: !isAuthenticated,
      agregar,
      actualizar,
      quitar,
      vaciar,
      recargar,
      cuponAplicado,
      totalConDescuento,
      aplicarCupon,
      quitarCupon,
    }),
    [
      items,
      total,
      cantidadTotal,
      cargando,
      error,
      isAuthenticated,
      agregar,
      actualizar,
      quitar,
      vaciar,
      recargar,
      cuponAplicado,
      totalConDescuento,
      aplicarCupon,
      quitarCupon,
    ]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export default CartContext;
