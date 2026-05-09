import React, { useState, useEffect } from 'react'
import DistrictMap from './components/DistrictMap'
import DistrictCard from './components/DistrictCard'
import AlertPanel from './components/AlertPanel'
import MetricsChart from './components/MetricsChart'
import { connectWebSocket } from './services/websocket'

function App() {
  const [districts, setDistricts] = useState([])
  const [alerts, setAlerts] = useState([])

  useEffect(() => {
    const ws = connectWebSocket((data) => {
      console.log('WS message:', data)
    })
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
