import React, { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import AdminDistricts from './AdminDistricts'
import AdminSubstations from './AdminSubstations'

const TABS = [
  { id: 'districts', label: 'Distritos' },
  { id: 'substations', label: 'Subestaciones' },
  { id: 'users', label: 'Usuarios' },
]

export default function AdminPanel() {
  const { user, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('districts')

  if (!user) return <Navigate to="/login" replace />

  return (
    <div className="admin-page">
      <header className="admin-header">
        <div className="admin-header-left">
          <Link to="/" className="admin-back-link">← Dashboard</Link>
          <h1>Panel de Administración</h1>
        </div>
        <div className="admin-header-right">
          <a
            href="http://localhost:8000/"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-monitoring"
            title="Abre el dashboard de monitoreo en una nueva pestaña"
          >
            ⚡ Monitoring
          </a>
          <span className="admin-user">
            {user.nombre_completo || user.username}
            <small>({user.rol})</small>
          </span>
          <button onClick={logout} className="btn-logout">Cerrar Sesión</button>
        </div>
      </header>

      <nav className="admin-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`admin-tab ${activeTab === tab.id ? 'admin-tab-active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main className="admin-content">
        {activeTab === 'districts' && <AdminDistricts />}
        {activeTab === 'substations' && <AdminSubstations />}
        {activeTab === 'users' && <AdminUsers />}
      </main>
    </div>
  )
}

function AdminUsers() {
  const { token } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

  React.useEffect(() => {
    if (!token) return
    fetch(`${API_BASE}/api/admin/users`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.ok ? r.json() : [])
      .then((data) => setUsers(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [token])

  if (loading) return <div className="admin-loading">Cargando usuarios...</div>

  return (
    <div className="admin-table-container">
      <h2>Usuarios del Sistema</h2>
      <table className="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Usuario</th>
            <th>Email</th>
            <th>Nombre</th>
            <th>Rol</th>
            <th>Activo</th>
            <th>Creado</th>
          </tr>
        </thead>
        <tbody>
          {users.length === 0 ? (
            <tr><td colSpan={7} className="admin-empty">No hay usuarios registrados</td></tr>
          ) : (
            users.map((u) => (
              <tr key={u.id}>
                <td>{u.id}</td>
                <td>{u.username}</td>
                <td>{u.email}</td>
                <td>{u.nombre_completo || '-'}</td>
                <td><span className="role-badge">{u.rol}</span></td>
                <td>{u.activo ? '✓' : '✗'}</td>
                <td>{u.created_at ? new Date(u.created_at).toLocaleDateString() : '-'}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
