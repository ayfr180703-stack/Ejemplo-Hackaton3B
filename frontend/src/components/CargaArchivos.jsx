import { useState } from "react";
import { cargarArchivos } from "../api.js";

const TIPOS = ["tiendas", "ventas", "gastos", "depositos"];

export default function CargaArchivos({ alCargar }) {
  const [archivos, setArchivos] = useState({});
  const [estado, setEstado] = useState(null);
  const [cargando, setCargando] = useState(false);
  const completo = TIPOS.every((t) => archivos[t]);

  async function enviar() {
    setCargando(true);
    setEstado(null);
    try {
      const r = await cargarArchivos(archivos);
      setEstado({ ok: true, ...r });
      alCargar();
    } catch (e) {
      setEstado({ ok: false, mensaje: e.message });
    } finally {
      setCargando(false);
    }
  }

  return (
    <section className="panel">
      <h2>Cargar archivos nuevos (CSV o Excel)</h2>
      <div className="filtros">
        {TIPOS.map((t) => (
          <label key={t}>{t}
            <input type="file" accept=".csv,.txt,.xlsx" onChange={(e) => setArchivos({ ...archivos, [t]: e.target.files[0] })} />
          </label>
        ))}
      </div>
      <button disabled={!completo || cargando} onClick={enviar}>{cargando ? "Cargando…" : "Cargar y recalcular"}</button>
      {estado && !estado.ok && <p className="error">{estado.mensaje}</p>}
      {estado?.ok && (
        <div className="alerta-detalle">
          <p><b>Listo.</b> Filas cargadas: {TIPOS.map((t) => `${t} ${estado.filas[t]}`).join(" · ")}</p>
          {TIPOS.flatMap((t) => (estado.bitacora[t] || []).filter((b) => !b.includes("fila(s) de entrada")).map((b, i) => <p key={t + i} className="nota">{t}: {b}</p>))}
          {estado.problemas?.length > 0 && <p className="nota"><b>Problemas de datos:</b> {estado.problemas.join(" | ")}</p>}
        </div>
      )}
    </section>
  );
}
