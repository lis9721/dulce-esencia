import Icon from "./Icon";

const ACENTOS = {
  primary: { chip: "bg-primary/10 text-primary", brillo: "from-primary/10" },
  accent: { chip: "bg-accent/15 text-accent-dark dark:text-accent-soft", brillo: "from-accent/15" },
  sage: { chip: "bg-exito text-exito-fuerte", brillo: "from-sage/40" },
  blush: { chip: "bg-blush/50 text-ink", brillo: "from-blush/50" },
};

/**
 * StatCard
 * Tarjeta de indicador numérico para los Dashboards (requerimientos
 * 10-11 del quinto avance: "indicadores mediante componentes visuales
 * tipo Card"). Reutilizable para cualquier número simple: total de
 * usuarios, productos, ventas, facturación, PQR, etc.
 *
 * Estilo tipo panel administrativo: chip con icono junto a la
 * etiqueta, cifra grande y un resplandor suave del color del acento
 * en la esquina. `icono` (un path de ICON_PATHS) es opcional.
 */
function StatCard({ etiqueta, valor, acento = "primary", icono }) {
  const tono = ACENTOS[acento] || ACENTOS.primary;

  return (
    <div className="relative overflow-hidden rounded-2xl border border-beige/60 bg-cream p-5">
      <div
        aria-hidden="true"
        className={`pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-gradient-to-br ${tono.brillo} to-transparent blur-2xl`}
      />
      <div className="relative flex items-center gap-3">
        {icono && (
          <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${tono.chip}`}>
            <Icon path={icono} className="h-[18px] w-[18px]" />
          </span>
        )}
        <p className="text-sm font-medium text-primary/70">{etiqueta}</p>
      </div>
      <p className="relative mt-4 font-display text-3xl font-bold tracking-tight text-primary">{valor}</p>
    </div>
  );
}

export default StatCard;
