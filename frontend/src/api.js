// Toda cifra sale de la API; aquí no se calcula nada.
// En desarrollo (npm run dev) la API está en el puerto 8000. En la versión compilada, la API sirve
// también la interfaz, así que se usa la misma dirección (sin configurar nada).
export const API = (import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")).replace(/\/$/, "");

function consulta(parametros) {
  const q = new URLSearchParams();
  Object.entries(parametros || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.set(k, v);
  });
  const texto = q.toString();
  return texto ? `?${texto}` : "";
}

export async function pedir(ruta, parametros) {
  const r = await fetch(`${API}${ruta}${consulta(parametros)}`);
  if (!r.ok) {
    let detalle = r.statusText;
    try { detalle = (await r.json()).detail || detalle; } catch { /* sin cuerpo */ }
    throw new Error(`${r.status}: ${detalle}`);
  }
  return r.json();
}

export async function cargarArchivos(archivos) {
  const f = new FormData();
  ["tiendas", "ventas", "gastos", "depositos"].forEach((n) => f.append(n, archivos[n]));
  const r = await fetch(`${API}/cargar-csv`, { method: "POST", body: f });
  const cuerpo = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(cuerpo.detail || `Error ${r.status}`);
  return cuerpo;
}

export const dinero = (x) =>
  new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 }).format(x ?? 0);
export const porcentaje = (x) => `${(100 * (x ?? 0)).toFixed(1)}%`;
