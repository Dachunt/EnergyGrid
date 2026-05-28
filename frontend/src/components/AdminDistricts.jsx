import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import MapPicker from './MapPicker'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const EMPTY_FORM = { id: '', nombre: '', descripcion: '', latitud: null, longitud: null }

export default function AdminDistricts() {
  const { token } = useAuth()
  const [districts, setDistricts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const fetchDistricts = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/admin/districts`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setDistricts(Array.isArray(data) ? data : [])
      }
    } catch (err) { console.error('Error fetching districts:', err) }
    finally { setLoading(false) }
  }, [token])

  useEffect(() => { fetchDistricts() }, [fetchDistricts])

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setError('')
    setShowModal(true)
  }

  const openEdit = (district) => {
    setEditing(district)
    setForm({
      id: district.id,
      nombre: district.nombre,
      descripcion: district.descripcion || '',
      latitud: district.latitud,
      longitud: district.longitud,
      activo: district.activo !== false,
    })
    setError('')
    setShowModal(true)
  }

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const url = editing
        ? `${API_BASE}/api/admin/districts/${encodeURIComponent(editing.id)}`
        : `${API_BASE}/api/admin/districts`
      const method = editing ? 'PUT' : 'POST'

      const body = editing
        ? { nombre: form.nombre, descripcion: form.descripcion, latitud: form.latitud, longitud: form.longitud, activo: form.activo }
        : form

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Error al guardar')
      }

      setShowModal(false)
      fetchDistricts()
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  const handleDelete = async (district) => {
    if (!confirm(`�Desactivar el distrito "${district.nombre}"?`)) return
    try {
      const res = await fetch(`${API_BASE}/api/admin/districts/${encodeURIComponent(district.id)}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const err = await res.json()
        alert(err.detail || 'Error al desactivar')
        return
      }
      fetchDistricts()
    } catch (err) { alert('Error al desactivar distrito') }
  }

  const handleCoordsChange = ({ lat, lng }) => {
    setForm((prev) => ({ ...prev, latitud: lat, longitud: lng }))
  }

  if (loading) return <div className="admin-loading">Cargando distritos...</div>

  return (
    <div className="admin-table-container">
      <div className="admin-table-header">
        <h2>Gesti�n de Distritos</h2>
        <button className="btn-add" onClick={openCreate}>+ Agregar Distrito</button>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Descripci�n</th>
            <th>Latitud</th>
            <th>Longitud</th>
            <th>Activo</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {districts.length === 0 ? (
            <tr><td colSpan={7} className="admin-empty">No hay distritos registrados</td></tr>
          ) : (
            districts.map((d) => (
              <tr key={d.id} className={!d.activo ? 'row-inactive' : ''}>
                <td>{d.id}</td>
                <td><strong>{d.nombre}</strong></td>
                <td className="cell-desc">{d.descripcion || '-'}</td>
                <td>{d.latitud ?? '-'}</td>
                <td>{d.longitud ?? '-'}</td>
                <td>{d.activo ? <span className="badge-active">Activo</span> : <span className="badge-inactive">Inactivo</span>}</td>
                <td className="cell-actions">
                  <button className="btn-icon btn-edit" onClick={() => openEdit(d)} title="Editar">✏️</button>
                  {d.activo ? (
                    <button className="btn-icon btn-delete" onClick={() => handleDelete(d)} title="Desactivar">🗑️</button>
                  ) : (
                    <button className="btn-icon btn-activate" onClick={() => {
                      fetch(`${API_BASE}/api/admin/districts/${encodeURIComponent(d.id)}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                        body: JSON.stringify({ activo: true }),
                      }).then((r) => { if (r.ok) fetchDistricts() })
                    }} title="Reactivar">✅</button>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editing ? 'Editar Distrito' : 'Nuevo Distrito'}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <form onSubmit={handleSave} className="modal-form">
              {error && <div className="auth-error">{error}</div>}

              {!editing && (
                <div className="form-group">
                  <label>ID del distrito *</label>
                  <input type="text" value={form.id} onChange={(e) => setForm({ ...form, id: e.target.value })}
                    placeholder="ej: San Miguel" required />
                </div>
              )}

              <div className="form-group">
                <label>Nombre *</label>
                <input type="text" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                  placeholder="Nombre del distrito" required />
              </div>

              <div className="form-group">
                <label>Descripci�n</label>
                <textarea value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
                  placeholder="Descripci�n opcional" rows={2} />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Latitud</label>
                  <input type="number" step="any" value={form.latitud ?? ''}
                    onChange={(e) => setForm({ ...form, latitud: e.target.value ? parseFloat(e.target.value) : null })}
                    placeholder="13.6929" />
                </div>
                <div className="form-group">
                  <label>Longitud</label>
                  <input type="number" step="any" value={form.longitud ?? ''}
                    onChange={(e) => setForm({ ...form, longitud: e.target.value ? parseFloat(e.target.value) : null })}
                    placeholder="-89.2182" />
                </div>
              </div>

              <div className="form-group">
                <label>Seleccionar ubicaci�n en el mapa</label>
                <MapPicker
                  lat={form.latitud}
                  lng={form.longitud}
                  onCoordsChange={handleCoordsChange}
                />
              </div>

              {editing && (
                <div className="form-group">
                  <label className="checkbox-label">
                    <input type="checkbox" checked={form.activo}
                      onChange={(e) => setForm({ ...form, activo: e.target.checked })} />
                    Distrito activo
                  </label>
                </div>
              )}

              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowModal(false)}>Cancelar</button>
                <button type="submit" className="btn-save" disabled={saving}>
                  {saving ? 'Guardando...' : (editing ? 'Actualizar' : 'Crear Distrito')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
