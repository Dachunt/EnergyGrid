import React, { useState, useEffect } from 'react'
import DistrictMap from './components/DistrictMap'
import DistrictCard from './components/DistrictCard'
import AlertPanel from './components/AlertPanel'
import MetricsChart from './components/MetricsChart'
import { connectWebSocket } from './services/websocket'

// Error Boundary
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error capturado por ErrorBoundary:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            width: '100%',
            height: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#0f172a',
            color: '#ef4444',
            flexDirection: 'column',
            padding: '2rem',
          }}
        >
          <h1>Error en la aplicación</h1>
          <p>{this.state.error?.message}</p>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1.5rem',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
            }}
          >
            Recargar página
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

function AppContent() {
  const [districts, setDistricts] = useState([])
  const [alerts, setAlerts] = useState([])
  const [selectedDistrict, setSelectedDistrict] = useState(null)
  const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

  const refreshData = async () => {
    try {
      const [districtsRes, alertsRes] = await Promise.all([
        fetch(`${apiBase}/api/districts`),
        fetch(`${apiBase}/api/alerts?resolved=false`),
      ])
      if (districtsRes.ok) {
        setDistricts(await districtsRes.json())
      }
      if (alertsRes.ok) {
        setAlerts(await alertsRes.json())
      }
    } catch (err) {
      console.error('Error cargando datos:', err)
    }
  }

  useEffect(() => {
    refreshData()
    const ws = connectWebSocket((data) => {
      if (data.event === 'SOBRECARGA') {
        setAlerts((prev) => {
          const exists = prev.some((a) => a.id === data.alert_id)
          if (exists) return prev
          return [
            {
              id: data.alert_id || Date.now(),
              district_id: data.district_id,
              tipo_alerta: 'SOBRECARGA_CRITICA',
              descripcion: data.descripcion,
            },
            ...prev,
          ]
        })
      }

      if (
        data.event === 'SOBRECARGA' ||
        data.event === 'ADVERTENCIA' ||
        data.event === 'ACTUALIZACION'
      ) {
        setDistricts((prev) => {
          const idx = prev.findIndex((d) => d.district_id === data.district_id)
          const next = {
            district_id: data.district_id,
            substation_id: data.substation_id,
            consumo_kw: data.consumo_kw,
            capacidad_kw: data.capacidad_kw,
            porcentaje_uso: data.porcentaje,
            percentage: data.porcentaje,
          }
          if (idx === -1) return [...prev, next]
          const copy = [...prev]
          copy[idx] = { ...copy[idx], ...next }
          return copy
        })
      }
    }, apiBase)
    return () => ws.close()
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>EnergyGrid</h1>
        <p>Monitor de Consumo Eléctrico por Distritos</p>
      </header>
      <main className="app-main">
        <section className="map-section">
          <DistrictMap districts={districts} />
        </section>
        <aside className="sidebar">
          <AlertPanel alerts={alerts} />
          <MetricsChart selectedDistrict={selectedDistrict} />
        </aside>
      </main>
      <section className="cards-section">
        {districts.map((d) => (
          <DistrictCard 
            key={d.district_id} 
            district={d}
            isSelected={selectedDistrict === d.district_id}
            onSelect={() => setSelectedDistrict(d.district_id)}
          />
        ))}
      </section>
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  )
}

export default App
