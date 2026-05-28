import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import DistrictMap from './components/DistrictMap'
import DistrictCard from './components/DistrictCard'
import AlertPanel from './components/AlertPanel'
import MetricsChart from './components/MetricsChart'
import LoginPage from './components/LoginPage'
import RegisterPage from './components/RegisterPage'
import ProtectedRoute from './components/ProtectedRoute'
import AdminPanel from './components/AdminPanel'
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
          <h1>Error en la aplicaci�n</h1>
          <p>{this.state.error?.message}</p>
          <button onClick={() => window.location.reload()}
            style={{ marginTop:'1rem', padding:'0.5rem 1.5rem', backgroundColor:'#3b82f6',
              color:'white', border:'none', borderRadius:'0.5rem', cursor:'pointer' }}>
            Recargar p�gina
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
  const [manualPanel, setManualPanel]               = useState(null)
  const [wsConnected, setWsConnected]               = useState(false)
  const [lastUpdate, setLastUpdate]                 = useState(null)
  const [countdown, setCountdown]                   = useState(0)
  const [flashUpdate, setFlashUpdate]               = useState(false)
  const { user } = useAuth()

  const autoModeRef = useRef(false)
  const countdownRef = useRef(null)
  useEffect(() => { autoModeRef.current = autoMode }, [autoMode])

  const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

  const refreshData = async () => {
    try {
      const [dRes, aRes] = await Promise.all([
        fetch(`${apiBase}/api/districts`),
        fetch(`${apiBase}/api/alerts?resolved=false`),
      ])
      if (dRes.ok) setDistricts(await dRes.json())
      if (aRes.ok) setAlerts(await aRes.json())
      setLastUpdate(new Date())
      setFlashUpdate(true)
      setTimeout(() => setFlashUpdate(false), 500)
    } catch (err) { console.error('Error cargando datos:', err) }
  }

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
    } catch (err) { console.error('Error eliminando redistribuci�n:', err) }
  }

  const openManualPanel = (sourceDistrict) => {
    setManualPanel({ sourceDistrict })
  }

  const computeSummary = useCallback(() => {
    const totalConsumo = districts.reduce((s, d) => s + (d.consumo_kw || 0), 0)
    const totalCapacidad = districts.reduce((s, d) => s + (d.capacidad_kw || 0), 0)
    const totalSubs = districts.reduce((s, d) => s + (d.subestaciones?.length || 0), 0)
    const criticalDistricts = districts.filter(d => (d.porcentaje_uso || 0) >= 95).length
    const warningDistricts = districts.filter(d => {
      const p = d.porcentaje_uso || 0
      return p >= 75 && p < 95
    }).length
    return { totalConsumo, totalCapacidad, totalSubs, criticalDistricts, warningDistricts }
  }, [districts])

  const summary = computeSummary()

  useEffect(() => {
    refreshData()
    const interval = setInterval(refreshData, 15000)
    countdownRef.current = setInterval(() => {
      setCountdown(prev => (prev > 0 ? prev - 1 : 15))
    }, 1000)
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
          handleRedistribute(data.district_id, data.sugerencias[0].district_id)
        } else {
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
          if (idx === -1) return prev
          const copy = [...prev]
          const district = { ...copy[idx] }
          const subs = district.subestaciones ? [...district.subestaciones] : []
          const sIdx = subs.findIndex(s => s.substation_id === data.substation_id)
          const updatedSub = {
            substation_id: data.substation_id,
            consumo_kw: data.consumo_kw,
            capacidad_kw: data.capacidad_kw,
            porcentaje_uso: data.porcentaje,
            latitud: sIdx >= 0 ? subs[sIdx].latitud : null,
            longitud: sIdx >= 0 ? subs[sIdx].longitud : null,
          }
          if (sIdx >= 0) subs[sIdx] = { ...subs[sIdx], ...updatedSub }
          else subs.push(updatedSub)
          const totalConsumo = subs.reduce((sum, s) => sum + (s.consumo_kw || 0), 0)
          const totalCapacidad = subs.reduce((sum, s) => sum + (s.capacidad_kw || 0), 0)
          district.subestaciones = subs
          district.consumo_kw = totalConsumo
          district.capacidad_kw = totalCapacidad
          district.porcentaje_uso = totalCapacidad > 0 ? (totalConsumo / totalCapacidad * 100) : 0
          copy[idx] = district
          return copy
        })
      }
    }, apiBase, setWsConnected)
    return () => { ws.close(); clearInterval(interval); clearInterval(countdownRef.current) }
  }, [])

  const availableTargets = districts.filter(
    (d) => manualPanel && d.district_id !== manualPanel.sourceDistrict
  )

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1>⚡ EnergyGrid</h1>
          <p>Monitor de Consumo Eléctrico por Distritos</p>
        </div>
        <div className="header-stats">
          <div className="header-stat-item">
            <span className="header-stat-label">Consumo</span>
            <span className="header-stat-value">{summary.totalConsumo.toFixed(0)} kW</span>
          </div>
          <div className="header-stat-item">
            <span className="header-stat-label">Capacidad</span>
            <span className="header-stat-value">{summary.totalCapacidad.toFixed(0)} kW</span>
          </div>
          <div className="header-stat-item">
            <span className="header-stat-label">Uso Global</span>
            <span className={`header-stat-value ${summary.totalCapacidad > 0 && (summary.totalConsumo / summary.totalCapacidad * 100) >= 75 ? 'stat-warning' : ''}`}>
              {summary.totalCapacidad > 0 ? (summary.totalConsumo / summary.totalCapacidad * 100).toFixed(1) : 0}%
            </span>
          </div>
          <div className="header-stat-item">
            <span className="header-stat-label">Subestaciones</span>
            <span className="header-stat-value">{summary.totalSubs}</span>
          </div>
          {summary.criticalDistricts > 0 && (
            <div className="header-stat-item stat-critical-item">
              <span className="header-stat-label">Críticos</span>
              <span className="header-stat-value stat-critical">{summary.criticalDistricts}</span>
            </div>
          )}
          {summary.warningDistricts > 0 && (
            <div className="header-stat-item stat-warning-item">
              <span className="header-stat-label">En Alerta</span>
              <span className="header-stat-value stat-warning">{summary.warningDistricts}</span>
            </div>
          )}
        </div>
        <div className="header-controls">
          <div className="connection-status" title={wsConnected ? 'Conectado en tiempo real' : 'Desconectado - usando polling'}>
            <span className={`status-dot ${wsConnected ? 'status-dot-connected' : 'status-dot-disconnected'}`} />
            <span className="status-label">{wsConnected ? 'Tiempo real' : 'Polling'}</span>
          </div>
          {lastUpdate && (
            <div className="last-update-info" title="Última actualización de datos">
              <span className="update-label">Actualizado:</span>
              <span className="update-time">{lastUpdate.toLocaleTimeString('es-ES')}</span>
              <span className="update-countdown">{countdown}s</span>
            </div>
          )}
          <span className="mode-label">Redistribución:</span>
          <div className="mode-toggle">
            <button
              className={`mode-btn${!autoMode ? ' mode-btn-active' : ''}`}
              onClick={() => setAutoMode(false)}
              title="El operador elige cuándo y hacia dónde redistribuir"
            > Manual</button>
            <button
              className={`mode-btn${autoMode ? ' mode-btn-active mode-btn-auto' : ''}`}
              onClick={() => setAutoMode(true)}
              title="El sistema redistribuye automáticamente al detectar sobrecarga >95%"
            > Automático</button>
          </div>
          {autoMode && (
            <span className="mode-status mode-status-auto">● Activo</span>
          )}
          {user ? (
            <>
              <Link to="/admin" className="btn-admin-header">⚙ Admin</Link>
              <span className="user-badge-header">{user.username}</span>
            </>
          ) : (
            <Link to="/login" className="btn-login-header">🔐 Ingresar</Link>
          )}
        </div>
      </header>

      {redistribucion && !autoMode && (
        <div className={`redistribucion-banner${redistribucion.applied ? ' redistribucion-applied' : ''}`}>
          <span className="redistribucion-icon">{redistribucion.applied ? '✅' : '⚡'}</span>
          <div className="redistribucion-content">
            <strong>
              {redistribucion.applied
                ? `Redistribuci�n aplicada: ${redistribucion.district_id} → ${redistribucion.appliedTo}`
                : `Sobrecarga en ${redistribucion.district_id} — Elige destino de redistribuci�n`}
            </strong>
            {!redistribucion.applied && (
              <ul className="redistribucion-list">
                {redistribucion.sugerencias.map((s) => (
                  <li key={s.district_id}>
                    <span>{s.district_id} ({s.porcentaje_uso}% uso)</span>
                    <button className="btn-apply-redistribucion"
                      onClick={() => handleRedistribute(redistribucion.district_id, s.district_id)}>Aplicar</button>
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

      {manualPanel && (
        <div className="redistribucion-banner manual-panel">
          <span className="redistribucion-icon">✋</span>
          <div className="redistribucion-content">
            <strong>Redistribuci�n manual — origen: {manualPanel.sourceDistrict}</strong>
            <p style={{ fontSize:'0.85rem', color:'#cbd5e1', margin:'0.3rem 0' }}>
              Selecciona el distrito destino al que se transferir� la carga:
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
                    onClick={() => handleRedistribute(manualPanel.sourceDistrict, d.district_id)}>Seleccionar</button>
                </li>
              ))}
            </ul>
          </div>
          <button className="btn-close-redistribucion" onClick={() => setManualPanel(null)}>✕</button>
        </div>
      )}

      <main className={`app-main ${flashUpdate ? 'app-main-flash' : ''}`}>
        <section className="map-section">
          <DistrictMap districts={districts} redistributedDistricts={redistributedDistricts} onSelectDistrict={setSelectedDistrict} />
        </section>
        <aside className="sidebar">
          <AlertPanel alerts={alerts} apiBase={apiBase} onAlertResolved={(id) =>
            setAlerts((prev) => prev.filter((a) => a.id !== id))} />
          <MetricsChart selectedDistrict={selectedDistrict} apiBase={apiBase} />
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
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<AppContent />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/admin" element={<ProtectedRoute><AdminPanel /></ProtectedRoute>} />
        <Route path="/admin/*" element={<ProtectedRoute><AdminPanel /></ProtectedRoute>} />
      </Routes>
    </ErrorBoundary>
  )
}

export default App
