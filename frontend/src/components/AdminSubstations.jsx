import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import MapPicker from './MapPicker'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const EMPTY_FORM = { id: '', nombre: '', distrito: '', capacidad_kw: '', latitud: null, longitud: null, activa: true }

export default function AdminSubstations() {
  const { token } = useAuth()
  const [substations, setSubstations] = useState([])
  const [districts, setDistricts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    try {
      const [subRes, distRes] = await Promise.all([
        fetch(`${API_BASE}/api/admin/substations`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE}/api/admin/districts`, { headers: { Authorization: `Bearer ${token}` } }),
      ])
      if (subRes.ok) {
        const data = await subRes.json()
        setSubstations(Array.isArray(data) ? data : [])
      }
      if (distRes.ok) {
        const data = await distRes.json()
        setDistricts(Array.isArray(data) ? data : [])
      }
    } catch (err) { console.error('Error fetching substations:', err) }
    finally { setLoading(false) }
  }, [token])

  useEffect(() => { fetchData() }, [fetchData])

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setError('')
    setShowModal(true)
  }

  const openEdit = (sub) => {
    setEditing(sub)
    setForm({
      id: sub.id,
      nombre: sub.nombre || '',
      distrito: sub.distrito || '',
      capacidad_kw: sub.capacidad_kw ?? '',
      latitud: sub.latitud,
      longitud: sub.longitud,
      activa: sub.activa !== false,
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
        ? `${API_BASE}/api/admin/substations/${encodeURIComponent(editing.id)}`
        : `${API_BASE}/api/admin/substations`
      const method = editing ? 'PUT' : 'POST'

      const body = editing
        ? {
            nombre: form.nombre,
            distrito: form.distrito,
            capacidad_kw: form.capacidad_kw ? parseFloat(form.capacidad_kw) : null,
            latitud: form.latitud,
            longitud: form.longitud,
            activa: form.activa,
          }
        : {
            id: form.id,
            nombre: form.nombre,
            distrito: form.distrito,
            capacidad_kw: parseFloat(form.capacidad_kw),
            latitud: form.latitud,
            longitud: form.longitud,
            activa: true,
          }

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
      fetchData()
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  const handleDelete = async (sub) => {
    if (!confirm(`�Eliminar la subestaci�n "${sub.nombre || sub.id}"?`)) return
    try {
      const res = await fetch(`${API_BASE}/api/admin/substations/${encodeURIComponent(sub.id)}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const err = await res.json()
        alert(err.detail || 'Error al eliminar')
        return
      }
      fetchData()
    } catch (err) { alert('Error al eliminar subestaci�n') }
  }

  const handleCoordsChange = ({ lat, lng }) => {
    setForm((prev) => ({ ...prev, latitud: lat, longitud: lng }))
  }

  const activeDistricts = districts.filter((d) => d.activo)

  if (loading) return <div className="admin-loading">Cargando subestaciones...</div>

  return (
    <div className="admin-table-container">
      <div className="admin-table-header">
        <h2>Gesti�n de Subestaciones</h2>
        <button className="btn-add" onClick={openCreate}>+ Agregar Subestaci�n</button>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Distrito</th>
            <th>Capacidad (kW)</th>
            <th>Latitud</th>
            <th>Longitud</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {substations.length === 0 ? (
            <tr><td colSpan={8} className="admin-empty">No hay subestaciones registradas</td></tr>
          ) : (
            substations.map((s) => (
              <tr key={s.id} className={!s.activa ? 'row-inactive' : ''}>
                <td>{s.id}</td>
                <td><strong>{s.nombre || s.id}</strong></td>
                <td>{s.distrito_nombre || s.distrito || '-'}</td>
                <td>{s.capacidad_kw ? `${s.capacidad_kw.toLocaleString()} kW` : '-'}</td>
                <td>{s.latitud ?? '-'}</td>
                <td>{s.longitud ?? '-'}</td>
                <td>
                  {s.activa ? <span className="badge-active">Activa</span> : <span className="badge-inactive">Inactiva</span>}
                </td>
                <td className="cell-actions">
                  <button className="btn-icon btn-edit" onClick={() => openEdit(s)} title="Editar">✏️</button>
                  <button className="btn-icon btn-delete" onClick={() => handleDelete(s)} title="Eliminar">🗑️</button>
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
              <h3>{editing ? 'Editar Subestaci�n' : 'Nueva Subestaci�n'}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <form onSubmit={handleSave} className="modal-form">
              {error && <div className="auth-error">{error}</div>}

              {!editing && (
                <div className="form-group">
                  <label>ID de la subestaci�n *</label>
                  <input type="text" value={form.id} onChange={(e) => setForm({ ...form, id: e.target.value })}
                    placeholder="ej: SSS003" required />
                </div>
              )}

              <div className="form-group">
                <label>Nombre *</label>
                <input type="text" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                  placeholder="Nombre de la subestaci�n" required />
              </div>

              <div className="form-group">
                <label>Distrito *</label>
                <select value={form.distrito} onChange={(e) => setForm({ ...form, distrito: e.target.value })} required>
                  <option value="">Seleccionar distrito...</option>
                  {activeDistricts.map((d) => (
                    <option key={d.id} value={d.id}>{d.nombre}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Capacidad (kW) *</label>
                <input type="number" step="0.01" min="0" value={form.capacidad_kw}
                  onChange={(e) => setForm({ ...form, capacidad_kw: e.target.value })}
                  placeholder="ej: 5000" required />
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
                  exclusionZones={substations.filter(s => s.latitud != null && s.longitud != null).map(s => ({ lat: s.latitud, lng: s.longitud, id: s.id }))}
                />
              </div>

              {editing && (
                <div className="form-group">
                  <label className="checkbox-label">
                    <input type="checkbox" checked={form.activa}
                      onChange={(e) => setForm({ ...form, activa: e.target.checked })} />
                    Subestaci�n activa
                  </label>
                </div>
              )}

              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowModal(false)}>Cancelar</button>
                <button type="submit" className="btn-save" disabled={saving}>
                  {saving ? 'Guardando...' : (editing ? 'Actualizar' : 'Crear Subestaci�n')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
