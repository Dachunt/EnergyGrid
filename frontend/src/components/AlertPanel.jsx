import React from 'react'

function AlertPanel({ alerts }) {
  const getAlertIcon = (tipo) => {
    if (tipo.includes('SOBRECARGA') || tipo.includes('CRITICA')) return '🔴'
    if (tipo.includes('ADVERTENCIA')) return '🟠'
    return '⚠️'
  }

  const getAlertClass = (tipo) => {
    if (tipo.includes('SOBRECARGA') || tipo.includes('CRITICA')) return 'alert-critical'
    if (tipo.includes('ADVERTENCIA')) return 'alert-warning'
    return 'alert-info'
  }

  return (
    <div className="alert-panel">
      <h2>⚡ Alertas Activas</h2>
      {alerts.length === 0 && <p className="no-alerts">✅ Sin alertas activas</p>}
      <div className="alerts-list">
        {alerts.map((a) => (
          <div key={a.id} className={`alert-item ${getAlertClass(a.tipo_alerta)}`}>
            <div className="alert-header">
              <span className="alert-icon">{getAlertIcon(a.tipo_alerta)}</span>
              <strong>{a.tipo_alerta}</strong>
            </div>
            <p className="alert-description">{a.descripcion}</p>
            {a.district_id && <small className="alert-district">Distrito: {a.district_id}</small>}
          </div>
        ))}
      </div>
    </div>
  )
}

export default AlertPanel
