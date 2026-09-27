/**
 * BarChart
 * Gráfico de barras simple, dibujado a mano en SVG (sin agregar una
 * librería de gráficos como dependencia nueva del proyecto — el
 * quinto avance solo exige "gráfico de barras", no una en particular).
 *
 * `data` es un arreglo de { label, value }. `formatoValor` (opcional)
 * formatea el número que se muestra arriba de cada barra (ej. moneda).
 */
function BarChart({ data, formatoValor = (v) => v, alto = 220, color = "#7c5cff" }) {
  const valores = data.map((d) => Number(d.value) || 0);
  const maximo = Math.max(1, ...valores);
  const anchoBarra = 100 / Math.max(data.length, 1);

  if (data.length === 0) {
    return <p className="py-10 text-center text-sm text-primary/70">No hay datos para este período.</p>;
  }

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 100 ${alto / 10 + 6}`}
        preserveAspectRatio="none"
        className="h-56 w-full min-w-[420px]"
        role="img"
        aria-label="Gráfico de barras"
      >
        {data.map((punto, indice) => {
          const valor = Number(punto.value) || 0;
          const alturaBarra = (valor / maximo) * (alto / 10);
          const x = indice * anchoBarra + anchoBarra * 0.15;
          const anchoReal = anchoBarra * 0.7;
          const y = alto / 10 + 2 - alturaBarra;
          return (
            <g key={punto.label}>
              <rect
                x={x}
                y={y}
                width={anchoReal}
                height={alturaBarra}
                rx={0.6}
                fill={color}
                opacity={0.85}
              >
                <title>{`${punto.label}: ${formatoValor(valor)}`}</title>
              </rect>
            </g>
          );
        })}
        <line x1="0" y1={alto / 10 + 2} x2="100" y2={alto / 10 + 2} stroke="currentColor" strokeOpacity="0.15" strokeWidth="0.15" />
      </svg>
      <div className="mt-1 flex min-w-[420px] gap-0 text-[10px] text-primary/70">
        {data.map((punto) => (
          <div key={punto.label} style={{ width: `${anchoBarra}%` }} className="truncate px-0.5 text-center">
            {punto.label}
          </div>
        ))}
      </div>
    </div>
  );
}

export default BarChart;
