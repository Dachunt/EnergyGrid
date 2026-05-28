import React from 'react'

function DistrictCard({ district, isSelected, isRedistributed, onSelect, onRedistribute, onClearRedistribution }) {
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
    <div 
      className={`district-card district-card-${estado}${isSelected ? ' selected' : ''}`}
      onClick={onSelect}
      style={{
        cursor: 'pointer',
        transition: 'all 0.3s ease',
        border: isSelected ? '2px solid #3b82f6' : '2px solid transparent',
      }}
    >
      <div className="card-header">
        <h3>{district.district_id || 'Distrito'}</h3>
        <span className="status-badge">{statusLabel}</span>
        {isRedistributed && (
          <span className="redistribucion-badge">⚡ Redistribuida</span>
        )}
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
      {district.subestaciones && district.subestaciones.length > 0 && (
        <div className="card-footer">
          <small style={{ display: 'block', marginBottom: '4px', color: '#94a3b8' }}>Subestaciones:</small>
          {district.subestaciones.map(s => (
            <div key={s.substation_id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', padding: '2px 0', borderTop: '1px solid #1e293b' }}>
              <span>{s.substation_id}</span>
              <span style={{ color: s.porcentaje_uso >= 95 ? '#ef4444' : s.porcentaje_uso >= 75 ? '#eab308' : '#22c55e' }}>
                {s.consumo_kw?.toFixed(1) || '--'} / {s.capacidad_kw?.toFixed(1) || '--'} kW ({ (s.porcentaje_uso || 0).toFixed(1) }%)
              </span>
            </div>
          ))}
        </div>
      )}
      {!district.subestaciones?.length && district.district_id && (
        <div className="card-footer">
          <small style={{ color: '#64748b' }}>Sin subestaciones</small>
        </div>
      )}
      <div className="card-actions">
        {isRedistributed ? (
          <button
            className="btn-card-action btn-card-undo"
            onClick={(e) => { e.stopPropagation(); onClearRedistribution && onClearRedistribution() }}
          >
            ↩ Restaurar carga normal
          </button>
        ) : (
          <button
            className="btn-card-action btn-card-redistribute"
            onClick={(e) => { e.stopPropagation(); onRedistribute && onRedistribute() }}
          >
            ⚡ Redistribuir carga
          </button>
        )}
      </div>
    </div>
  )
}

export default DistrictCard
