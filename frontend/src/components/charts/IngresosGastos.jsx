import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { dinero, pedir } from "../../api.js";

const millones = (v) => `${(v / 1e6).toFixed(1)} M`;

export default function IngresosGastos({ filtro, version }) {
  const [filas, setFilas] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    pedir("/consolidado", { nivel: "total", ...filtro })
      .then((d) => setFilas(d.map((f) => ({ ...f, mes: f.periodo.slice(0, 7) }))))
      .catch((e) => setError(e.message));
  }, [filtro, version]);

  return (
    <section className="panel">
      <h2>Ingresos contra gastos por mes</h2>
      {error && <p className="error">{error}</p>}
      <div style={{ width: "100%", height: 300 }}>
        <ResponsiveContainer>
          <BarChart data={filas || []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="mes" fontSize={11} />
            <YAxis tickFormatter={millones} fontSize={11} />
            <Tooltip formatter={(v) => dinero(v)} />
            <Legend />
            <Bar dataKey="ingresos" name="Ingresos" fill="#1f3a5f" />
            <Bar dataKey="gastos" name="Gastos" fill="#c76a00" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
