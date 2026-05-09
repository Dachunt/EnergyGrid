import React from 'react'

function AlertPanel({ alerts }) {
  return (
    <div className="alert-panel">
      <h2>Alertas</h2>
      {alerts.length === 0 && <p>Sin alertas activas</p>}
      {alerts.map((a) => (
        <div key={a.id} className="alert-item">
          <strong>{a.tipo_alerta}</strong>
          <p>{a.descripcion}</p>
        </div>
      ))}
    </div>
  )
}

export default AlertPanel
