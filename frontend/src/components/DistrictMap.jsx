import React, { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix para los iconos de leaflet en Vite
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const DISTRICTS_GEO = {
  'San Salvador':       { lat: 13.6929, lng: -89.2182 },
  'Antiguo Cuscatlan':  { lat: 13.7114, lng: -89.2964 },
  'Santa Tecla':         { lat: 13.6816, lng: -89.2833 },
  'Soyapango':           { lat: 13.6667, lng: -89.1833 },
}

function getStatusColor(percentage) {
  if (percentage >= 95) return '#ef4444' // Rojo - crítico
  if (percentage >= 90) return '#f97316' // Naranja - advertencia
  if (percentage >= 75) return '#eab308' // Amarillo - alto
  return '#22c55e' // Verde - normal
}

function DistrictMap({ districts, redistributedDistricts = new Set(), onSelectDistrict }) {
  const mapContainer = useRef(null)
  const map = useRef(null)
  const markers = useRef({})
  const [mapError, setMapError] = useState(null)

  // Inicializar mapa
  useEffect(() => {
    try {
      if (map.current) return
      if (!mapContainer.current) return

      // Crear mapa centrado en El Salvador
      map.current = L.map(mapContainer.current).setView([13.7942, -88.8965], 9)

      // Agregar tile layer (OpenStreetMap)
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map.current)

    } catch (error) {
      console.error('Error inicializando mapa:', error)
      setMapError(error.message)
    }
  }, [])

  function getCoord(district, field) {
    return district[field] || (DISTRICTS_GEO[district.district_id] && DISTRICTS_GEO[district.district_id][field === 'latitud' || field === 'lat' ? 'lat' : 'lng'])
  }

  useEffect(() => {
    if (!map.current) return

    const seen = new Set()

    districts.forEach((district) => {
      const distId = district.district_id
      if (seen.has(distId)) return
      seen.add(distId)

      const dLat = getCoord(district, 'latitud') || getCoord(district, 'lat')
      const dLng = getCoord(district, 'longitud') || getCoord(district, 'lng')
      if (!dLat || !dLng) return

      const isRedistributed = redistributedDistricts.has(distId)
      const pct = district.porcentaje_uso || 0
      const color = getStatusColor(pct)

      let marker = markers.current[distId]
      if (!marker) {
        marker = L.circleMarker([dLat, dLng], {
          radius: 25, fillColor: color, color: '#000', weight: 2, opacity: 1, fillOpacity: 0.8,
        })
          .addTo(map.current)
          .on('click', () => { if (onSelectDistrict) onSelectDistrict(distId) })
        markers.current[distId] = marker
      }

      marker.setStyle({
        fillColor: color,
        color: isRedistributed ? '#3b82f6' : '#000',
        weight: isRedistributed ? 4 : 2,
        dashArray: isRedistributed ? '6 3' : null,
      })

      let subsHtml = ''
      if (district.subestaciones && district.subestaciones.length > 0) {
        subsHtml = '<hr style="margin:4px 0;border-color:#334155"/>' +
          district.subestaciones.map(s =>
            `<div style="font-size:11px;display:flex;justify-content:space-between;gap:6px">
              <span>${s.substation_id}</span>
              <span>${s.consumo_kw?.toFixed(1)||'--'} / ${s.capacidad_kw?.toFixed(1)||'--'} kW (${(s.porcentaje_uso||0).toFixed(1)}%)</span>
            </div>`
          ).join('')
      }

      marker.setPopupContent(`
        <div style="font-size:12px;text-align:center">
          <strong>${distId}</strong><br/>
          ${district.consumo_kw?.toFixed(2)||'--'} kW / ${district.capacidad_kw?.toFixed(2)||'--'} kW &nbsp; ${pct.toFixed(1)}%
          ${isRedistributed ? '<br/><span style="color:#3b82f6;font-weight:bold">⚡ Redistribuida</span>' : ''}
          ${subsHtml}
        </div>
      `)

      // substation markers
      if (district.subestaciones) {
        district.subestaciones.forEach(s => {
          const sLat = s.latitud, sLng = s.longitud
          if (!sLat || !sLng) return
          const sId = s.substation_id
          let sMarker = markers.current[sId]
          if (!sMarker) {
            sMarker = L.circleMarker([sLat, sLng], {
              radius: 10, fillColor: '#64748b', color: '#1e293b', weight: 2, opacity: 1, fillOpacity: 0.9,
            })
              .addTo(map.current)
              .bindPopup(`
                <div style="font-size:11px;text-align:center">
                  <strong>${sId}</strong><br/>
                  ${s.consumo_kw?.toFixed(1)||'--'} / ${s.capacidad_kw?.toFixed(1)||'--'} kW<br/>
                  ${(s.porcentaje_uso||0).toFixed(1)}%
                </div>
              `)
            markers.current[sId] = sMarker
          }
          const sColor = getStatusColor(s.porcentaje_uso || 0)
          sMarker.setStyle({ fillColor: sColor })
          sMarker.setPopupContent(`
            <div style="font-size:11px;text-align:center">
              <strong>${sId}</strong><br/>
              ${s.consumo_kw?.toFixed(1)||'--'} / ${s.capacidad_kw?.toFixed(1)||'--'} kW<br/>
              ${(s.porcentaje_uso||0).toFixed(1)}%
            </div>
          `)
        })
      }
    })
  }, [districts, redistributedDistricts])

  if (mapError) {
    return (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#0f172a',
          color: '#ef4444',
          padding: '2rem',
          textAlign: 'center',
          borderRadius: '0.5rem',
        }}
      >
        <div>
          <h3>Error cargando mapa</h3>
          <p>{mapError}</p>
        </div>
      </div>
    )
  }

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: '0.5rem',
        overflow: 'hidden',
      }}
    >
      <div style={{ padding: '1rem', backgroundColor: '#1e293b', borderBottom: '1px solid #334155' }}>
        <h2 style={{ margin: '0', color: '#fff', fontSize: '1.3rem' }}>Mapa de Distritos</h2>
        <p style={{ margin: '0.25rem 0 0 0', color: '#cbd5e1', fontSize: '0.9rem' }}>
          Haz clic en los marcadores para ver detalles
        </p>
      </div>
      <div
        ref={mapContainer}
        style={{
          flex: 1,
          width: '100%',
          minHeight: '400px',
          backgroundColor: '#0f172a',
        }}
      />
      <div style={{ padding: '0.75rem', backgroundColor: '#0f172a', borderTop: '1px solid #334155', fontSize: '0.85rem', color: '#cbd5e1' }}>
        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#22c55e' }} />
            <span>Normal (&lt;75%)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#eab308' }} />
            <span>Alto (75-90%)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#f97316' }} />
            <span>Advertencia (90-95%)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#ef4444' }} />
            <span>Crítico (≥95%)</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DistrictMap
