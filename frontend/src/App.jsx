import React, { useState, useEffect } from 'react'
import DistrictMap from './components/DistrictMap'
import DistrictCard from './components/DistrictCard'
import AlertPanel from './components/AlertPanel'
import MetricsChart from './components/MetricsChart'
import { connectWebSocket } from './services/websocket'

function App() {
  const [districts, setDistricts] = useState([])
  const [alerts, setAlerts] = useState([])
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
          <MetricsChart />
        </aside>
      </main>
      <section className="cards-section">
        {districts.map((d) => (
          <DistrictCard key={d.id} district={d} />
        ))}
      </section>
    </div>
  )
}

export default App
