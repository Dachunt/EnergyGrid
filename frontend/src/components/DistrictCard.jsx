import React from 'react'

function DistrictCard({ district }) {
  const consumo = typeof district.consumo_kw === 'number' ? district.consumo_kw.toFixed(2) : '--'
  const capacidad = typeof district.capacidad_kw === 'number' ? district.capacidad_kw.toFixed(2) : '--'
  const porcentaje = typeof district.porcentaje_uso === 'number' ? district.porcentaje_uso.toFixed(1) : '--'
  
  // Determinar estado y color basado en porcentaje
  let estado = 'normal'
  let statusLabel = 'Normal'
  if (typeof district.porcentaje_uso === 'number') {
    if (district.porcentaje_uso >= 95) {
      estado = 'critico'
      statusLabel = '🔴 CRÍTICO'
    } else if (district.porcentaje_uso >= 90) {
      estado = 'advertencia'
      statusLabel = '🟠 ADVERTENCIA'
    } else if (district.porcentaje_uso >= 75) {
      estado = 'alto'
      statusLabel = '🟡 ALTO'
    } else {
      estado = 'normal'
      statusLabel = '🟢 NORMAL'
    }
  }

  return (
    <div className={`district-card district-card-${estado}`}>
      <div className="card-header">
        <h3>{district.district_id || 'Distrito'}</h3>
        <span className="status-badge">{statusLabel}</span>
      </div>
      <div className="card-body">
        <div className="metric-item">
          <span className="metric-label">Consumo</span>
          <span className="metric-value">{consumo} kW</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Capacidad</span>
          <span className="metric-value">{capacidad} kW</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Uso</span>
          <span className="metric-value">{porcentaje}%</span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{
            width: Math.min(typeof district.porcentaje_uso === 'number' ? district.porcentaje_uso : 0, 100) + '%'
          }}></div>
        </div>
      </div>
      {district.substation_id && (
        <div className="card-footer">
          <small>Subestación: {district.substation_id}</small>
        </div>
      )}
    </div>
  )
}

export default DistrictCard
