/**
 * StatCard
 * Tarjeta de indicador numérico para los Dashboards (requerimientos
 * 10-11 del quinto avance: "indicadores mediante componentes visuales
 * tipo Card"). Reutilizable para cualquier número simple: total de
 * usuarios, productos, ventas, facturación, PQR, etc.
 */
function StatCard({ etiqueta, valor, acento = "primary" }) {
  const acentos = {
    primary: "bg-primary/10 text-primary",
    accent: "bg-accent/20 text-accent",
    sage: "bg-sage/30 text-primary",
    blush: "bg-blush/30 text-primary",
  };

  return (
    <div className="rounded-2xl border border-beige/60 bg-cream p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-primary/70">{etiqueta}</p>
      <p className="mt-2 text-2xl font-bold text-primary">{valor}</p>
      <span className={`mt-2 inline-block h-1.5 w-10 rounded-full ${acentos[acento] || acentos.primary}`} />
    </div>
  );
}

export default StatCard;
