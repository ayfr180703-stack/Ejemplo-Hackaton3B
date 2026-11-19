import { useState } from "react";
import { dinero } from "../api.js";

const ORDEN = ["Crítica", "Alta", "Media"];

export default function Alertas({ alertas }) {
  const [abierta, setAbierta] = useState(null);
  if (!alertas) return null;
  const cuenta = ORDEN.map((s) => [s, alertas.filter((a) => a.severidad === s).length]);
  return (
    <section className="panel">
      <h2>Alertas priorizadas</h2>
      <p className="resumen-alertas">
        {cuenta.map(([s, n]) => (
          <span key={s} className={`etiqueta ${s}`}>{s}: {n}</span>
        ))}
      </p>
      {alertas.length === 0 && <p className="nota">Sin alertas con estos filtros.</p>}
      <ul className="lista-alertas">
        {alertas.map((a, i) => (
          <li key={i} className={`alerta-fila ${a.severidad}`} onClick={() => setAbierta(abierta === i ? null : i)}>
            <div className="alerta-cabecera">
              <span className={`etiqueta ${a.severidad}`}>{a.severidad}</span>
              <strong>{a.tienda}</strong>
              <span>{a.tipo}{a.categoria ? ` · ${a.categoria}` : ""}</span>
              <span className="monto">{dinero(a.monto_en_riesgo)}</span>
            </div>
            {abierta === i && (
              <div className="alerta-detalle">
                <p><b>Por qué:</b> {a.motivo}</p>
                <p><b>Qué hacer:</b> {a.accion_sugerida}</p>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
