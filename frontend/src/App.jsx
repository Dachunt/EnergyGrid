import React, { useState, useEffect, useRef } from 'react'
import DistrictMap from './components/DistrictMap'
import DistrictCard from './components/DistrictCard'
import AlertPanel from './components/AlertPanel'
import MetricsChart from './components/MetricsChart'
import { connectWebSocket } from './services/websocket'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) { return { hasError: true, error } }
  componentDidCatch(error, errorInfo) { console.error('ErrorBoundary:', error, errorInfo) }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ width:'100%', height:'100vh', display:'flex', alignItems:'center',
          justifyContent:'center', backgroundColor:'#0f172a', color:'#ef4444',
          flexDirection:'column', padding:'2rem' }}>
          <h1>Error en la aplicación</h1>
          <p>{this.state.error?.message}</p>
          <button onClick={() => window.location.reload()}
            style={{ marginTop:'1rem', padding:'0.5rem 1.5rem', backgroundColor:'#3b82f6',
              color:'white', border:'none', borderRadius:'0.5rem', cursor:'pointer' }}>
            Recargar página
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

function AppContent() {
  const [districts, setDistricts]                   = useState([])
  const [alerts, setAlerts]                         = useState([])
  const [redistribucion, setRedistribucion]         = useState(null)
  const [redistributedDistricts, setRedistributed]  = useState(new Set())
  const [selectedDistrict, setSelectedDistrict]     = useState(null)
  const [autoMode, setAutoMode]                     = useState(false)
  const [manualPanel, setManualPanel]               = useState(null) // { sourceDistrict }

  // Ref para leer autoMode dentro del callback WS sin stale closure
  const autoModeRef = useRef(false)
  useEffect(() => { autoModeRef.current = autoMode }, [autoMode])

  const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

  // ── data fetch ──────────────────────────────────────────────────────────────
  const refreshData = async () => {
    try {
      const [dRes, aRes] = await Promise.all([
        fetch(`${apiBase}/api/districts`),
        fetch(`${apiBase}/api/alerts?resolved=false`),
      ])
      if (dRes.ok) setDistricts(await dRes.json())
      if (aRes.ok) setAlerts(await aRes.json())
    } catch (err) { console.error('Error cargando datos:', err) }
  }

  // ── redistribución ──────────────────────────────────────────────────────────
  const handleRedistribute = async (fromDistrict, toDistrict) => {
    try {
      const res = await fetch(
        `${apiBase}/api/districts/${encodeURIComponent(fromDistrict)}/redistribute?to=${encodeURIComponent(toDistrict)}`,
        { method: 'POST' }
      )
      if (res.ok) {
        setRedistributed((prev) => new Set([...prev, fromDistrict]))
        setRedistribucion((prev) => prev ? { ...prev, applied: true, appliedTo: toDistrict } : prev)
        setManualPanel(null)
      }
    } catch (err) { console.error('Error redistribuyendo:', err) }
  }

  const handleClearRedistribution = async (districtId) => {
    try {
      await fetch(`${apiBase}/api/districts/${encodeURIComponent(districtId)}/redistribute`, { method: 'DELETE' })
      setRedistributed((prev) => { const n = new Set(prev); n.delete(districtId); return n })
    } catch (err) { console.error('Error eliminando redistribución:', err) }
  }

  // Abre el panel manual de redistribución para un distrito origen
  const openManualPanel = (sourceDistrict) => {
    setManualPanel({ sourceDistrict })
  }

  // ── WebSocket ───────────────────────────────────────────────────────────────
  useEffect(() => {
    refreshData()
    const ws = connectWebSocket((data) => {

      if (data.event === 'SOBRECARGA') {
        setAlerts((prev) => {
          if (prev.some((a) => a.id === data.alert_id)) return prev
          return [{ id: data.alert_id || Date.now(), district_id: data.district_id,
            tipo_alerta: 'SOBRECARGA_CRITICA', descripcion: data.descripcion }, ...prev]
        })
      }

      if (data.event === 'REDISTRIBUCION') {
        if (autoModeRef.current && data.sugerencias?.length > 0) {
          // Modo automático: aplica al mejor candidato sin intervención del usuario
          handleRedistribute(data.district_id, data.sugerencias[0].district_id)
        } else {
          // Modo manual: muestra el banner con botones
          setRedistribucion({
            district_id: data.district_id,
            sugerencias: data.sugerencias,
            timestamp: new Date().toLocaleTimeString('es-ES'),
            applied: false,
          })
          setTimeout(() => setRedistribucion(null), 30000)
        }
      }

      if (data.event === 'REDISTRIBUCION_APLICADA') {
        setRedistributed((prev) => new Set([...prev, data.from_district]))
      }

      if (data.event === 'REDISTRIBUCION_ELIMINADA') {
        setRedistributed((prev) => { const n = new Set(prev); n.delete(data.district_id); return n })
      }

      if (['SOBRECARGA', 'ADVERTENCIA', 'ACTUALIZACION'].includes(data.event)) {
        setDistricts((prev) => {
          const idx = prev.findIndex((d) => d.district_id === data.district_id)
          const next = { district_id: data.district_id, substation_id: data.substation_id,
            consumo_kw: data.consumo_kw, capacidad_kw: data.capacidad_kw,
            porcentaje_uso: data.porcentaje, percentage: data.porcentaje }
          if (idx === -1) return [...prev, next]
          const copy = [...prev]; copy[idx] = { ...copy[idx], ...next }; return copy
        })
      }
    }, apiBase)
    return () => ws.close()
  }, [])

  // Destinos disponibles para redistribución manual (excluye el origen y los ya redistribuidos)
  const availableTargets = districts.filter(
    (d) => manualPanel && d.district_id !== manualPanel.sourceDistrict
  )

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-left">
          <h1>EnergyGrid</h1>
          <p>Monitor de Consumo Eléctrico por Distritos</p>
        </div>
        <div className="header-controls">
          <span className="mode-label">Redistribución:</span>
          <div className="mode-toggle">
            <button
              className={`mode-btn${!autoMode ? ' mode-btn-active' : ''}`}
              onClick={() => setAutoMode(false)}
              title="El operador elige cuándo y hacia dónde redistribuir"
            >
              ✋ Manual
            </button>
            <button
              className={`mode-btn${autoMode ? ' mode-btn-active mode-btn-auto' : ''}`}
              onClick={() => setAutoMode(true)}
              title="El sistema redistribuye automáticamente al detectar sobrecarga >95%"
            >
              🤖 Automático
            </button>
          </div>
          {autoMode && (
            <span className="mode-status mode-status-auto">
              ● Activo — redistribuye al detectar &gt;95%
            </span>
          )}
          <a 
            href="http://localhost:8000/" 
            target="_blank" 
            rel="noopener noreferrer"
            className="btn-dashboard"
            title="Abre el dashboard de monitoreo en una nueva pestaña"
          >
            📊 Dashboard
          </a>
        </div>
      </header>

      {/* ── Banner redistribución manual (solo aparece en modo Manual) ── */}
      {redistribucion && !autoMode && (
        <div className={`redistribucion-banner${redistribucion.applied ? ' redistribucion-applied' : ''}`}>
          <span className="redistribucion-icon">{redistribucion.applied ? '✅' : '⚡'}</span>
          <div className="redistribucion-content">
            <strong>
              {redistribucion.applied
                ? `Redistribución aplicada: ${redistribucion.district_id} → ${redistribucion.appliedTo}`
                : `Sobrecarga en ${redistribucion.district_id} — Elige destino de redistribución`}
            </strong>
            {!redistribucion.applied && (
              <ul className="redistribucion-list">
                {redistribucion.sugerencias.map((s) => (
                  <li key={s.district_id}>
                    <span>{s.district_id} ({s.porcentaje_uso}% uso)</span>
                    <button className="btn-apply-redistribucion"
                      onClick={() => handleRedistribute(redistribucion.district_id, s.district_id)}>
                      Aplicar
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {redistribucion.applied && (
              <p className="redistribucion-applied-msg">
                Consumo de <strong>{redistribucion.district_id}</strong> reducido al 55%.{' '}
                <button className="btn-undo-redistribucion"
                  onClick={() => { handleClearRedistribution(redistribucion.district_id); setRedistribucion(null) }}>
                  Deshacer
                </button>
              </p>
            )}
            <small>{redistribucion.timestamp}</small>
          </div>
          <button className="btn-close-redistribucion" onClick={() => setRedistribucion(null)}>✕</button>
        </div>
      )}

      {/* ── Panel de redistribución manual iniciada desde una card ── */}
      {manualPanel && (
        <div className="redistribucion-banner manual-panel">
          <span className="redistribucion-icon">✋</span>
          <div className="redistribucion-content">
            <strong>Redistribución manual — origen: {manualPanel.sourceDistrict}</strong>
            <p style={{ fontSize:'0.85rem', color:'#cbd5e1', margin:'0.3rem 0' }}>
              Selecciona el distrito destino al que se transferirá la carga:
            </p>
            <ul className="redistribucion-list">
              {availableTargets.map((d) => (
                <li key={d.district_id}>
                  <span>
                    {d.district_id}
                    <small style={{ color:'#94a3b8', marginLeft:'0.3rem' }}>
                      ({(d.porcentaje_uso ?? d.percentage ?? 0).toFixed(1)}% uso)
                    </small>
                  </span>
                  <button className="btn-apply-redistribucion"
                    onClick={() => handleRedistribute(manualPanel.sourceDistrict, d.district_id)}>
                    Seleccionar
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <button className="btn-close-redistribucion" onClick={() => setManualPanel(null)}>✕</button>
        </div>
      )}

      <main className="app-main">
        <section className="map-section">
          <DistrictMap districts={districts} redistributedDistricts={redistributedDistricts} />
        </section>
        <aside className="sidebar">
          <AlertPanel alerts={alerts} apiBase={apiBase} onAlertResolved={(id) =>
            setAlerts((prev) => prev.filter((a) => a.id !== id))} />
          <MetricsChart selectedDistrict={selectedDistrict} />
        </aside>
      </main>

      <section className="cards-section">
        {districts.map((d) => (
          <DistrictCard
            key={d.district_id}
            district={d}
            isSelected={selectedDistrict === d.district_id}
            isRedistributed={redistributedDistricts.has(d.district_id)}
            onSelect={() => setSelectedDistrict(d.district_id)}
            onRedistribute={() => openManualPanel(d.district_id)}
            onClearRedistribution={() => handleClearRedistribution(d.district_id)}
          />
        ))}
      </section>
    </div>
  )
}

function App() {
  return <ErrorBoundary><AppContent /></ErrorBoundary>
}

export default App
