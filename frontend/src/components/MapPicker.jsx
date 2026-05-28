import React, { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const PROXIMITY_KM = 5

export default function MapPicker({ lat, lng, onCoordsChange, exclusionZones = [], height = '300px' }) {
  const mapContainer = useRef(null)
  const map = useRef(null)
  const marker = useRef(null)
  const circles = useRef([])
  const [proximityWarn, setProximityWarn] = React.useState('')

  useEffect(() => {
    if (map.current) return
    if (!mapContainer.current) return

    const initialLat = lat || 13.7942
    const initialLng = lng || -88.8965

    map.current = L.map(mapContainer.current).setView([initialLat, initialLng], 8)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map.current)

    if (lat && lng) {
      marker.current = L.marker([lat, lng])
        .addTo(map.current)
        .bindPopup(`Lat: ${lat.toFixed(6)}, Lng: ${lng.toFixed(6)}`)
        .openPopup()
    }

    map.current.on('click', (e) => {
      const { lat: clickLat, lng: clickLng } = e.latlng

      let warn = ''
      for (const z of exclusionZones) {
        const dlat = (z.lat - clickLat) * 111
        const dlng = (z.lng - clickLng) * 111 * Math.cos(clickLat * Math.PI / 180)
        const dist = Math.sqrt(dlat * dlat + dlng * dlng)
        if (dist < PROXIMITY_KM) {
          warn = `⚠ A solo ${dist.toFixed(1)} km de "${z.id || z.nombre || z.substation_id || 'otra sub'}" (mín ${PROXIMITY_KM} km)`
          break
        }
      }
      setProximityWarn(warn)

      if (marker.current) {
        marker.current.setLatLng([clickLat, clickLng])
      } else {
        marker.current = L.marker([clickLat, clickLng]).addTo(map.current)
      }

      marker.current
        .setPopupContent(`Lat: ${clickLat.toFixed(6)}, Lng: ${clickLng.toFixed(6)}`)
        .openPopup()

      if (onCoordsChange) {
        onCoordsChange({ lat: parseFloat(clickLat.toFixed(6)), lng: parseFloat(clickLng.toFixed(6)) })
      }
    })

    return () => {
      if (map.current) {
        map.current.remove()
        map.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!map.current) return
    circles.current.forEach(c => map.current.removeLayer(c))
    circles.current = exclusionZones.map(z => {
      if (z.lat == null || z.lng == null) return null
      return L.circle([z.lat, z.lng], {
        radius: PROXIMITY_KM * 1000,
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 0.08,
        weight: 1,
        dashArray: '5 5',
      }).addTo(map.current).bindTooltip(`${z.id || z.substation_id || ''} — ${PROXIMITY_KM} km`, { permanent: false })
    }).filter(Boolean)
  }, [exclusionZones])

  const isCoordSet = lat != null && lng != null

  return (
    <div className="map-picker">
      <div
        ref={mapContainer}
        style={{
          width: '100%',
          height: height,
          borderRadius: '6px',
          border: '1px solid #334155',
        }}
      />
      {proximityWarn && (
        <div style={{ color: '#ef4444', fontSize: '0.8rem', padding: '4px 0' }}>{proximityWarn}</div>
      )}
      {isCoordSet && (
        <div className="map-picker-coords">
          Lat: <strong>{lat}</strong> | Lng: <strong>{lng}</strong>
        </div>
      )}
      {!isCoordSet && (
        <div className="map-picker-hint">
          Haz clic en el mapa para seleccionar las coordenadas
        </div>
      )}
    </div>
  )
}
