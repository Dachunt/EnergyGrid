import React, { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Datos de los distritos en El Salvador (coordenadas aproximadas)
const DISTRICTS_GEO = {
  'San Salvador': {
    lat: 13.6929,
    lng: -89.2182,
    substations: ['SSS001', 'SSS002'],
  },
  'Antiguo Cuscatlán': {
    lat: 13.7114,
    lng: -89.2964,
    substations: ['SAN001'],
  },
  'Santa Tecla': {
    lat: 13.6816,
    lng: -89.2833,
    substations: ['STC001'],
  },
  'Soyapango': {
    lat: 13.6667,
    lng: -89.1833,
    substations: ['SAL001'],
  },
}

function getStatusColor(percentage) {
  if (percentage >= 95) return '#ef4444' // Rojo - crítico
  if (percentage >= 90) return '#f97316' // Naranja - advertencia
  if (percentage >= 75) return '#eab308' // Amarillo - alto
  return '#22c55e' // Verde - normal
}

function DistrictMap({ districts }) {
  const mapContainer = useRef(null)
  const map = useRef(null)
  const markers = useRef({})

  // Inicializar mapa
  useEffect(() => {
    if (map.current) return

    // Crear mapa centrado en El Salvador
    map.current = L.map(mapContainer.current).setView([13.7942, -88.8965], 9)

    // Agregar tile layer (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map.current)

    // Crear marcadores para cada distrito
    Object.entries(DISTRICTS_GEO).forEach(([districtName, geoData]) => {
      const marker = L.circleMarker([geoData.lat, geoData.lng], {
        radius: 25,
        fillColor: '#22c55e',
        color: '#000',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8,
      })
        .addTo(map.current)
        .bindPopup(districtName)

      markers.current[districtName] = marker
    })
  }, [])

  // Actualizar colores de marcadores cuando cambian los distritos
  useEffect(() => {
    if (!map.current) return

    districts.forEach((district) => {
      const marker = markers.current[district.district_id]
      if (marker) {
        const color = getStatusColor(district.percentage)
        marker.setStyle({
          fillColor: color,
        })

        // Actualizar popup con información
        const info = `
          <div style="font-size: 12px; text-align: center;">
            <strong>${district.district_id}</strong><br/>
            ${district.consumo_kw} kW / ${district.capacidad_kw} kW<br/>
            ${district.percentage.toFixed(1)}%
          </div>
        `
        marker.setPopupContent(info)
      }
    })
  }, [districts])

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
