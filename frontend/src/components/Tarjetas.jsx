import { dinero, porcentaje } from "../api.js";

export default function Tarjetas({ kpis }) {
  if (!kpis) return null;
  const faltante = kpis.diferencia_efectivo;
  const tarjetas = [
    { titulo: "Ventas", valor: dinero(kpis.ventas) },
    { titulo: "Gastos", valor: dinero(kpis.gastos) },
    { titulo: "Margen neto", valor: dinero(kpis.margen), nota: `${porcentaje(kpis.margen_pct)} de las ventas` },
    { titulo: "Diferencia de efectivo", valor: dinero(faltante), nota: `ventas menos depósitos (${porcentaje(kpis.diferencia_efectivo_pct)} de las ventas)`, alerta: Math.abs(kpis.diferencia_efectivo_pct) > 0.005 },
  ];
  return (
    <section className="tarjetas">
      {tarjetas.map((t) => (
        <article key={t.titulo} className={`tarjeta${t.alerta ? " alerta" : ""}`}>
          <h3>{t.titulo}</h3>
          <p className="valor">{t.valor}</p>
          {t.nota && <p className="nota">{t.nota}</p>}
        </article>
      ))}
    </section>
  );
}
