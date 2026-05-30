import React, { useEffect, useState } from 'react'

function SpikeNotification({ spikes, onDismiss }) {
  if (!spikes || spikes.length === 0) return null

  return (
    <div className="spike-notifications">
      {spikes.map((spike) => (
        <div
          key={spike.id}
          className={`spike-toast spike-toast-${spike.nivel.toLowerCase()}`}
        >
          <div className="spike-toast-header">
            <span className="spike-icon">
              {spike.nivel === 'CRITICO' ? '🔴' : spike.nivel === 'ALTO' ? '🟠' : '🟡'}
            </span>
            <strong>PICO {spike.nivel}</strong>
            <button className="spike-dismiss" onClick={() => onDismiss(spike.id)}>✕</button>
          </div>
          <p className="spike-description">{spike.descripcion}</p>
          <div className="spike-details">
            <span>📍 {spike.district_id}</span>
            <span>⚡ {spike.consumo_kw?.toFixed(1)} kW</span>
            <span>📈 +{spike.incremento_pct?.toFixed(1)}%</span>
          </div>
          <small className="spike-time">{spike.timestamp}</small>
        </div>
      ))}
    </div>
  )
}

export default SpikeNotification
