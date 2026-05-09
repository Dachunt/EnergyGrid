import React from 'react'

function DistrictCard({ district }) {
  return (
    <div className="district-card">
      <h3>{district.district_id || 'Distrito'}</h3>
      <p>Consumo: -- kW</p>
      <p>Capacidad: -- kW</p>
    </div>
  )
}

export default DistrictCard
