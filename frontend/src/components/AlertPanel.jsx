import React, { useEffect, useRef } from 'react'

const ALERT_SOUND_FREQ = 880

function playAlertBeep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.frequency.value = ALERT_SOUND_FREQ
    osc.type = 'square'
    gain.gain.setValueAtTime(0.15, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4)
    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.4)
  } catch (_) {}
}

function AlertPanel({ alerts, apiBase, onAlertResolved }) {
  const prevCriticalCount = useRef(0)

  const criticalAlerts = alerts.filter(
    (a) => a.tipo_alerta.includes('SOBRECARGA') || a.tipo_alerta.includes('CRITICA')
  )

  useEffect(() => {
    if (criticalAlerts.length > prevCriticalCount.current) {
      playAlertBeep()
    }
    prevCriticalCount.current = criticalAlerts.length
  }, [criticalAlerts.length])

  const handleResolve = async (alertId) => {
    try {
      const res = await fetch(`${apiBase}/api/alerts/${alertId}/resolve`, { method: 'PATCH' })
      if (res.ok && onAlertResolved) {
        onAlertResolved(alertId)
      }
    } catch (err) {
      console.error('Error resolviendo alerta:', err)
    }
  }

  const getAlertIcon = (tipo) => {
    if (tipo.includes('SOBRECARGA') || tipo.includes('CRITICA')) return '🔴'
    if (tipo.includes('ADVERTENCIA')) return '🟠'
    return '⚠️'
  }

  const getAlertClass = (tipo) => {
    if (tipo.includes('SOBRECARGA') || tipo.includes('CRITICA')) return 'alert-critical alert-blink'
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
              <button
                className="btn-resolve"
                onClick={() => handleResolve(a.id)}
                title="Marcar como resuelta"
              >
                ✓ Resolver
              </button>
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
