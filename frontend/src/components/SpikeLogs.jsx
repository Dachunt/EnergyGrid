import { useState, useEffect } from "react";

export default function SpikeLogs({ apiBase }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${apiBase}/api/logs/spikes`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.spikes || []);
      }
    } catch (err) {
      console.error("Error cargando logs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 10000);
    return () => clearInterval(interval);
  }, []);

  const nivelColor = (nivel) => {
    if (nivel === "CRITICO") return "#ef4444";
    if (nivel === "ALTO") return "#f97316";
    return "#eab308";
  };

  return (
    <div style={{
      background: "#1e293b",
      borderRadius: "0.75rem",
      padding: "1.25rem",
      marginTop: "1rem",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
        <span style={{ fontSize: "1.2rem" }}>📋</span>
        <h3 style={{ color: "#f1f5f9", margin: 0, fontSize: "1rem", fontWeight: 600 }}>
          Historial de Picos de Energía
        </h3>
        <button onClick={fetchLogs} style={{
          marginLeft: "auto", background: "#334155", color: "#94a3b8",
          border: "none", borderRadius: "0.4rem", padding: "0.25rem 0.75rem",
          cursor: "pointer", fontSize: "0.75rem"
        }}>↻ Actualizar</button>
      </div>

      {loading ? (
        <p style={{ color: "#64748b", fontSize: "0.85rem" }}>Cargando logs...</p>
      ) : logs.length === 0 ? (
        <p style={{ color: "#64748b", fontSize: "0.85rem" }}>✅ Sin picos registrados hoy</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", maxHeight: "400px", overflowY: "auto" }}>
          {logs.map((spike, i) => (
            <div key={i} style={{
              background: "#0f172a",
              borderRadius: "0.5rem",
              padding: "0.75rem 1rem",
              borderLeft: `4px solid ${nivelColor(spike.nivel)}`,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem" }}>
                <span style={{ color: nivelColor(spike.nivel), fontWeight: 700, fontSize: "0.85rem" }}>
                  ⚡ PICO {spike.nivel}
                </span>
                <span style={{ color: "#64748b", fontSize: "0.75rem" }}>
                  {new Date(spike.timestamp).toLocaleString("es-SV")}
                </span>
              </div>
              <div style={{ color: "#cbd5e1", fontSize: "0.82rem", lineHeight: "1.6" }}>
                <div>📍 <b>Distrito:</b> {spike.district_id} — <b>Subestación:</b> {spike.substation_id}</div>
                <div>⚡ <b>Consumo:</b> {spike.consumo_actual_kw?.toFixed(2)} kW &nbsp;|&nbsp;
                  <b>Promedio:</b> {spike.promedio_referencia_kw?.toFixed(2)} kW</div>
                <div>📈 <b>Incremento:</b> +{spike.incremento_porcentual?.toFixed(2)}%</div>
                <div>🔀 <b>Redistribución:</b> {spike.redistribucion || "—"}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
