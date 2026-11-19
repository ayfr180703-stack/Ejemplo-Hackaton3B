import { useEffect, useState } from "react";
import { pedir } from "./api.js";
import Tarjetas from "./components/Tarjetas.jsx";
import Alertas from "./components/Alertas.jsx";

export default function App() {
  const [opciones, setOpciones] = useState({ regiones: [], tiendas: [] });
  const [filtro, setFiltro] = useState({ region: "", tienda: "", desde: "", hasta: "" });
  const [kpis, setKpis] = useState(null);
  const [alertas, setAlertas] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    pedir("/filtros").then(setOpciones).catch((e) => setError(`No se pudo conectar con la API: ${e.message}`));
  }, []);

  useEffect(() => {
    setError("");
    Promise.all([pedir("/kpis", filtro), pedir("/alertas", filtro)])
      .then(([k, a]) => { setKpis(k); setAlertas(a); })
      .catch((e) => setError(e.message));
  }, [filtro]);

  const cambiar = (campo) => (e) => setFiltro({ ...filtro, [campo]: e.target.value });

  return (
    <main>
      <header>
        <h1>Control financiero y flujo de efectivo por tienda</h1>
        <div className="filtros">
          <label>Región
            <select value={filtro.region} onChange={cambiar("region")}>
              <option value="">Todas</option>
              {opciones.regiones.map((r) => <option key={r}>{r}</option>)}
            </select>
          </label>
          <label>Tienda
            <select value={filtro.tienda} onChange={cambiar("tienda")}>
              <option value="">Todas</option>
              {opciones.tiendas.map((t) => <option key={t}>{t}</option>)}
            </select>
          </label>
          <label>Desde
            <input type="date" value={filtro.desde} min={opciones.desde} max={opciones.hasta} onChange={cambiar("desde")} />
          </label>
          <label>Hasta
            <input type="date" value={filtro.hasta} min={opciones.desde} max={opciones.hasta} onChange={cambiar("hasta")} />
          </label>
        </div>
      </header>
      {error && <p className="error">{error}</p>}
      <Tarjetas kpis={kpis} />
      <Alertas alertas={alertas} />
    </main>
  );
}
