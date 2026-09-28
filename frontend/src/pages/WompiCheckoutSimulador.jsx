import { useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { formatearPrecio } from "../utils/formato";
import useDocumentTitle from "../hooks/useDocumentTitle";

export default function WompiCheckoutSimulador() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  const referencia = params.get("referencia") || "ESSENTIA-DEMO";
  const idTransaccion = params.get("id") || `demo_trx_${referencia}_0`;
  const montoCentavos = Number(params.get("monto")) || 0;
  const urlRetorno = params.get("url_retorno") || "/pago/resultado";

  const montoCOP = montoCentavos > 0 ? montoCentavos / 100 : 0;

  useDocumentTitle("Wompi Checkout Sandbox", "Pasarela de pagos Wompi (Modo Pruebas)", "/pago/simulador", true);

  // Estados del formulario simulado
  const [metodo, setMetodo] = useState("tarjeta");
  const [tipoResultado, setTipoResultado] = useState("aprobada"); // 'aprobada' | 'declinada'
  const [numeroTarjeta, setNumeroTarjeta] = useState("4242 4242 4242 4242");
  const [titular, setTitular] = useState("Laura Gómez");
  const [vencimiento, setVencimiento] = useState("12/28");
  const [cvc, setCvc] = useState("123");
  const [cuotas, setCuotas] = useState("1");
  const [procesando, setProcesando] = useState(false);
  const [mensajeEstado, setMensajeEstado] = useState("");

  const seleccionarTarjetaAprobada = () => {
    setTipoResultado("aprobada");
    setNumeroTarjeta("4242 4242 4242 4242");
    setCvc("123");
  };

  const seleccionarTarjetaDeclinada = () => {
    setTipoResultado("declinada");
    setNumeroTarjeta("4000 0000 0000 0002");
    setCvc("999");
  };

  const ejecutarPago = (forzarDeclinado = false) => {
    setProcesando(true);
    setMensajeEstado("Conectando con la pasarela Wompi Sandbox...");

    setTimeout(() => {
      setMensajeEstado("Validando token de seguridad y fondos...");
    }, 600);

    setTimeout(() => {
      const debeDeclinar = forzarDeclinado || tipoResultado === "declinada";
      const idFinal = debeDeclinar
        ? idTransaccion.replace("demo_trx_", "demo_declined_")
        : idTransaccion;

      const separador = urlRetorno.includes("?") ? "&" : "?";
      const destino = `${urlRetorno}${separador}id=${encodeURIComponent(idFinal)}&referencia=${encodeURIComponent(referencia)}`;

      window.location.assign(destino);
    }, 1300);
  };

  const cancelar = () => {
    navigate(-1);
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col justify-between font-sans selection:bg-[#00d09c] selection:text-slate-950">
      {/* Barra superior estilo Wompi */}
      <header className="border-b border-slate-800 bg-[#00172e] px-4 py-4 sm:px-8">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Logo Wompi estilizado */}
            <div className="flex items-center gap-1.5">
              <span className="text-2xl font-black tracking-tight text-white">
                wompi<span className="text-[#00d09c] text-3xl leading-none">.</span>
              </span>
            </div>
            <span className="rounded-full bg-amber-500/20 border border-amber-500/40 px-2.5 py-0.5 text-xs font-semibold text-amber-300">
              MODO PRUEBAS / SANDBOX
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400">
            <svg className="h-4 w-4 text-[#00d09c]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <span className="hidden sm:inline">Conexión cifrada 256 bits</span>
          </div>
        </div>
      </header>

      {/* Contenido principal */}
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8 sm:px-6">
        <div className="grid gap-8 lg:grid-cols-12">
          {/* Columna izquierda: Resumen del comercio y pedido */}
          <aside className="lg:col-span-5 flex flex-col gap-6">
            <div className="rounded-2xl border border-slate-800 bg-[#001b36] p-6 shadow-xl">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-pink-500/20 text-pink-300 font-bold text-xl border border-pink-500/30">
                  DE
                </div>
                <div>
                  <h2 className="text-base font-bold text-white">Dulce Esencia Pastelería</h2>
                  <p className="text-xs text-slate-400">Comercio verificado en Colombia</p>
                </div>
              </div>

              <hr className="my-5 border-slate-800" />

              <div className="flex flex-col gap-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Referencia:</span>
                  <span className="font-mono text-xs font-semibold text-slate-200">{referencia}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Moneda:</span>
                  <span className="font-semibold text-slate-200">COP (Pesos Colombianos)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Ambiente:</span>
                  <span className="text-amber-400 font-medium">Sandbox Bancolombia</span>
                </div>
              </div>

              <div className="mt-6 rounded-xl bg-slate-950/60 p-4 border border-slate-800/80">
                <span className="text-xs text-slate-400 block mb-1">Total a pagar:</span>
                <span className="text-3xl font-extrabold text-[#00d09c]">
                  {formatearPrecio(montoCOP)}
                </span>
              </div>
            </div>

            {/* Atajos de pruebas rápidas */}
            <div className="rounded-2xl border border-blue-900/40 bg-blue-950/20 p-5 text-xs text-slate-300">
              <p className="font-semibold text-blue-300 mb-2 flex items-center gap-1.5">
                <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Tarjetas de prueba oficiales Wompi
              </p>
              <p className="text-slate-400 mb-3 leading-relaxed">
                Selecciona una opción para autocompletar los datos y comprobar el comportamiento de la pasarela:
              </p>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={seleccionarTarjetaAprobada}
                  className={`rounded-lg px-3 py-2 text-left font-medium transition border ${
                    tipoResultado === "aprobada"
                      ? "bg-emerald-500/20 border-emerald-500 text-emerald-300"
                      : "bg-slate-800/60 border-slate-700 text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  <div className="font-bold text-xs">Aprobada (OK)</div>
                  <div className="text-[10px] text-slate-400 font-mono">4242 •••• 4242</div>
                </button>
                <button
                  type="button"
                  onClick={seleccionarTarjetaDeclinada}
                  className={`rounded-lg px-3 py-2 text-left font-medium transition border ${
                    tipoResultado === "declinada"
                      ? "bg-rose-500/20 border-rose-500 text-rose-300"
                      : "bg-slate-800/60 border-slate-700 text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  <div className="font-bold text-xs">Rechazada (Error)</div>
                  <div className="text-[10px] text-slate-400 font-mono">4000 •••• 0002</div>
                </button>
              </div>
            </div>
          </aside>

          {/* Columna derecha: Pasarela de Checkout */}
          <div className="lg:col-span-7">
            <div className="rounded-2xl border border-slate-800 bg-[#001b36] p-6 sm:p-8 shadow-xl relative overflow-hidden">
              {/* Overlay cuando está procesando */}
              {procesando && (
                <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm z-20 flex flex-col items-center justify-center p-6 text-center">
                  <div className="h-12 w-12 animate-spin rounded-full border-4 border-[#00d09c] border-t-transparent mb-4"></div>
                  <h3 className="text-lg font-bold text-white mb-1">{mensajeEstado}</h3>
                  <p className="text-xs text-slate-400">Por favor, no cierres ni recargues esta ventana.</p>
                </div>
              )}

              {/* Selector de métodos de pago */}
              <div className="flex border-b border-slate-800 pb-3 mb-6 gap-3">
                <button
                  type="button"
                  onClick={() => setMetodo("tarjeta")}
                  className={`pb-2 px-1 text-sm font-semibold transition border-b-2 ${
                    metodo === "tarjeta"
                      ? "border-[#00d09c] text-[#00d09c]"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  💳 Tarjeta Débito / Crédito
                </button>
                <button
                  type="button"
                  onClick={() => setMetodo("nequi")}
                  className={`pb-2 px-1 text-sm font-semibold transition border-b-2 ${
                    metodo === "nequi"
                      ? "border-[#00d09c] text-[#00d09c]"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  🟣 Nequi / Bancolombia
                </button>
              </div>

              {metodo === "nequi" ? (
                <div className="py-8 text-center flex flex-col items-center gap-4">
                  <div className="h-14 w-14 rounded-2xl bg-purple-900/40 border border-purple-500/30 flex items-center justify-center text-2xl font-bold text-purple-300">
                    N
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white">Pago con Nequi / Botón Bancolombia</h3>
                    <p className="text-xs text-slate-400 mt-1 max-w-sm">
                      En Sandbox de Wompi, el botón procesa la notificación en tiempo real igual que una tarjeta.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => ejecutarPago(false)}
                    disabled={procesando}
                    className="mt-2 w-full max-w-xs rounded-xl bg-[#2853fe] hover:bg-[#1f42d4] px-6 py-3 font-semibold text-white transition shadow-lg shadow-blue-900/30"
                  >
                    Confirmar con Nequi Sandbox
                  </button>
                </div>
              ) : (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    ejecutarPago(false);
                  }}
                  className="flex flex-col gap-4"
                >
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Número de tarjeta
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={numeroTarjeta}
                        onChange={(e) => setNumeroTarjeta(e.target.value)}
                        placeholder="4242 4242 4242 4242"
                        className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-4 py-2.5 font-mono text-sm text-white placeholder-slate-500 focus:border-[#00d09c] focus:outline-none focus:ring-1 focus:ring-[#00d09c]"
                        required
                      />
                      <span className="absolute right-3 top-2.5 rounded bg-blue-600/30 px-2 py-0.5 text-[10px] font-bold text-blue-300">
                        VISA
                      </span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Nombre del titular
                    </label>
                    <input
                      type="text"
                      value={titular}
                      onChange={(e) => setTitular(e.target.value)}
                      placeholder="Como figura en la tarjeta"
                      className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-[#00d09c] focus:outline-none focus:ring-1 focus:ring-[#00d09c]"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        Expiración
                      </label>
                      <input
                        type="text"
                        value={vencimiento}
                        onChange={(e) => setVencimiento(e.target.value)}
                        placeholder="MM/AA"
                        maxLength={5}
                        className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-3 py-2.5 font-mono text-sm text-center text-white placeholder-slate-500 focus:border-[#00d09c] focus:outline-none focus:ring-1 focus:ring-[#00d09c]"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        CVC / CVV
                      </label>
                      <input
                        type="password"
                        value={cvc}
                        onChange={(e) => setCvc(e.target.value)}
                        placeholder="123"
                        maxLength={4}
                        className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-3 py-2.5 font-mono text-sm text-center text-white placeholder-slate-500 focus:border-[#00d09c] focus:outline-none focus:ring-1 focus:ring-[#00d09c]"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        Cuotas
                      </label>
                      <select
                        value={cuotas}
                        onChange={(e) => setCuotas(e.target.value)}
                        className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-3 py-2.5 text-sm text-white focus:border-[#00d09c] focus:outline-none"
                      >
                        <option value="1">1 cuota</option>
                        <option value="3">3 cuotas</option>
                        <option value="6">6 cuotas</option>
                        <option value="12">12 cuotas</option>
                      </select>
                    </div>
                  </div>

                  {/* Botones de acción */}
                  <div className="mt-4 flex flex-col gap-3">
                    <button
                      type="submit"
                      disabled={procesando}
                      className="w-full rounded-xl bg-[#00d09c] hover:bg-[#00b588] py-3.5 px-4 font-bold text-slate-950 transition shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                    >
                      Pagar {formatearPrecio(montoCOP)} con Wompi
                    </button>

                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => ejecutarPago(true)}
                        disabled={procesando}
                        className="flex-1 rounded-xl border border-rose-800/80 bg-rose-950/30 hover:bg-rose-900/40 py-2.5 px-3 text-xs font-semibold text-rose-300 transition"
                      >
                        Simular fallo (Tarjeta rechazada)
                      </button>
                      <button
                        type="button"
                        onClick={cancelar}
                        disabled={procesando}
                        className="rounded-xl border border-slate-700 hover:bg-slate-800 py-2.5 px-4 text-xs font-semibold text-slate-400 transition"
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                </form>
              )}

              <p className="mt-6 text-center text-[11px] text-slate-500 leading-relaxed">
                Wompi es la pasarela de pagos de Bancolombia. Al pagar aceptas los Términos y Condiciones de Wompi Colombia.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Pie de página */}
      <footer className="border-t border-slate-800 bg-[#001224] py-3 px-4 text-center text-xs text-slate-500">
        Pasarela de pagos Wompi Sandbox — Integrada en Dulce Esencia Pastelería
      </footer>
    </div>
  );
}
