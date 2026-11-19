import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { dinero, pedir } from "../../api.js";

const COLORES = { Pesimista: "#b3261e", Base: "#1f3a5f", Optimista: "#2e7d32" };
const millones = (v) => `${(v / 1e6).toFixed(1)} M`;

export default function FlujoAcumulado({ tiendas, version }) {
  const [tienda, setTienda] = useState("");
  const [inversion, setInversion] = useState(5500000);
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!tienda && tiendas.length) setTienda(tiendas[tiendas.length - 1]);
  }, [tiendas, tienda]);

  useEffect(() => {
    if (!tienda) return;
    setError("");
    pedir(`/proyecciones/${tienda}/escenarios`, { meses: 48, inversion_inicial: inversion || 0 })
      .then(setDatos)
      .catch((e) => setError(e.message));
  }, [tienda, inversion, version]);

  const nombres = datos ? Object.keys(datos.escenarios) : [];
  const curva = datos
    ? datos.escenarios.Base.curva.map((f, i) => {
        const fila = { mes_n: f.mes_n };
        nombres.forEach((n) => { fila[n] = datos.escenarios[n].curva[i].flujo_acumulado; });
        return fila;
      })
    : [];
  const base = datos?.escenarios.Base.resumen;

  return (
    <section className="panel">
      <h2>Flujo acumulado de una tienda nueva (punto de equilibrio)</h2>
      <div className="filtros">
        <label>Tienda
          <select value={tienda} onChange={(e) => setTienda(e.target.value)}>
            {tiendas.map((t) => <option key={t}>{t}</option>)}
          </select>
        </label>
        <label>Inversión inicial (pesos)
          <input type="number" min="0" step="100000" value={inversion} onChange={(e) => setInversion(Number(e.target.value))} />
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      {base && (
        <p className="nota">
          Escenario base: el flujo mensual se vuelve positivo en el mes {base.mes_equilibrio ?? "—"};{" "}
          {base.mes_recuperacion ? `la inversión se recupera en el mes ${base.mes_recuperacion}` : "la inversión no se recupera dentro del periodo mostrado"};
          necesidad máxima de efectivo {dinero(base.necesidad_maxima_de_efectivo)}.
        </p>
      )}
      <div style={{ width: "100%", height: 320 }}>
        <ResponsiveContainer>
          <LineChart data={curva}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="mes_n" fontSize={11} label={{ value: "mes de operación", position: "insideBottom", offset: -2, fontSize: 11 }} />
            <YAxis tickFormatter={millones} fontSize={11} />
            <Tooltip formatter={(v) => dinero(v)} labelFormatter={(m) => `Mes ${m}`} />
            <Legend />
            <ReferenceLine y={0} stroke="#666" />
            {base?.mes_equilibrio && (
              <ReferenceLine x={base.mes_equilibrio} stroke="#2e7d32" strokeDasharray="4 4"
                label={{ value: `Equilibrio mes ${base.mes_equilibrio}`, fontSize: 11, fill: "#2e7d32" }} />
            )}
            {nombres.map((n) => <Line key={n} type="monotone" dataKey={n} name={n} stroke={COLORES[n]} dot={false} strokeWidth={n === "Base" ? 3 : 1.5} />)}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
