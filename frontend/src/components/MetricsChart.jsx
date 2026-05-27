import React, { useState, useEffect } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'

function MetricsChart({ districts, selectedDistrict }) {
  const [historyData, setHistoryData] = useState([])

  // Cargar historial del distrito seleccionado
  useEffect(() => {
    if (!selectedDistrict) return

    const fetchHistory = async () => {
      try {
        const response = await fetch(`/api/districts/${selectedDistrict}/history?limit=20`)
        const data = await response.json()

        // Transformar datos para Recharts
        const chartData = data.map((item) => ({
          timestamp: new Date(item.timestamp).toLocaleTimeString('es-ES'),
          consumo: parseFloat(item.consumo_kw),
          capacidad: parseFloat(item.capacidad_kw),
          percentage: parseFloat(item.porcentaje_uso),
        }))

        setHistoryData(chartData.reverse())
      } catch (error) {
        console.error('Error cargando historial:', error)
      }
    }

    fetchHistory()
    const interval = setInterval(fetchHistory, 5000) // Actualizar cada 5 segundos

    return () => clearInterval(interval)
  }, [selectedDistrict])

  if (!selectedDistrict) {
    return (
      <div className="metrics-chart">
        <h2>Consumo Histórico</h2>
        <p style={{ color: '#cbd5e1', fontSize: '0.9rem' }}>Selecciona un distrito para ver su historial</p>
      </div>
    )
  }

  return (
    <div className="metrics-chart">
      <h2>Consumo Histórico - {selectedDistrict}</h2>
      
      {historyData.length === 0 ? (
        <p style={{ color: '#cbd5e1', fontSize: '0.9rem' }}>Cargando datos...</p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={historyData} margin={{ top: 5, right: 50, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="timestamp"
              tick={{ fill: '#cbd5e1', fontSize: 12 }}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis
              yAxisId="left"
              tick={{ fill: '#cbd5e1', fontSize: 12 }}
              label={{ value: 'kW', angle: -90, position: 'insideLeft', fill: '#cbd5e1' }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[0, 100]}
              tick={{ fill: '#f59e0b', fontSize: 12 }}
              label={{ value: '%', angle: 90, position: 'insideRight', fill: '#f59e0b' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '0.5rem',
                color: '#e2e8f0',
              }}
              labelStyle={{ color: '#cbd5e1' }}
            />
            <Legend />
            <ReferenceLine yAxisId="right" y={95} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'Crítico 95%', fill: '#ef4444', fontSize: 11 }} />
            <ReferenceLine yAxisId="right" y={75} stroke="#eab308" strokeDasharray="4 4" label={{ value: '75%', fill: '#eab308', fontSize: 11 }} />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="consumo"
              stroke="#3b82f6"
              name="Consumo (kW)"
              dot={false}
              strokeWidth={2}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="percentage"
              stroke="#f59e0b"
              name="Porcentaje (%)"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

export default MetricsChart
