/**
 * LineChart
 * Gráfico lineal simple, dibujado a mano en SVG — mismo criterio y
 * mismas props que BarChart.jsx (ver ese archivo para el porqué de no
 * usar una librería de gráficos).
 */
function LineChart({ data, formatoValor = (v) => v, color = "#e0774e" }) {
  const valores = data.map((d) => Number(d.value) || 0);
  const maximo = Math.max(1, ...valores);
  const alto = 22;

  if (data.length === 0) {
    return <p className="py-10 text-center text-sm text-primary/70">No hay datos para este período.</p>;
  }

  const paso = data.length > 1 ? 100 / (data.length - 1) : 0;
  const puntos = data.map((punto, indice) => {
    const x = data.length > 1 ? indice * paso : 50;
    const y = alto - (Number(punto.value) / maximo) * alto;
    return { x, y, ...punto };
  });
  const puntosAtributo = puntos.map((p) => `${p.x},${p.y}`).join(" ");
  const areaAtributo = `0,${alto} ${puntosAtributo} 100,${alto}`;

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 100 ${alto + 4}`}
        preserveAspectRatio="none"
        className="h-56 w-full min-w-[420px]"
        role="img"
        aria-label="Gráfico lineal"
      >
        <polygon points={areaAtributo} fill={color} opacity="0.12" />
        <polyline points={puntosAtributo} fill="none" stroke={color} strokeWidth="0.6" />
        {puntos.map((p) => (
          <circle key={p.label} cx={p.x} cy={p.y} r="0.9" fill={color}>
            <title>{`${p.label}: ${formatoValor(Number(p.value))}`}</title>
          </circle>
        ))}
        <line x1="0" y1={alto} x2="100" y2={alto} stroke="currentColor" strokeOpacity="0.15" strokeWidth="0.15" />
      </svg>
      <div className="mt-1 flex min-w-[420px] gap-0 text-[10px] text-primary/70">
        {data.map((punto) => (
          <div key={punto.label} style={{ width: `${100 / data.length}%` }} className="truncate px-0.5 text-center">
            {punto.label}
          </div>
        ))}
      </div>
    </div>
  );
}

export default LineChart;
