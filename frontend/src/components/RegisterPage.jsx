import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function RegisterPage() {
  const { register, user } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', password: '', confirm: '', nombre_completo: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (user) navigate('/admin', { replace: true })
  }, [user, navigate])

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm) {
      setError('Las contrase�as no coinciden')
      return
    }
    if (form.password.length < 6) {
      setError('La contrase�a debe tener al menos 6 caracteres')
      return
    }
    setLoading(true)
    try {
      await register(form.username, form.email, form.password, form.nombre_completo)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <h1>EnergyGrid</h1>
          <p>Registrar Administrador</p>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="auth-error">{error}</div>}
          <div className="form-group">
            <label htmlFor="username">Usuario *</label>
            <input id="username" name="username" type="text" value={form.username}
              onChange={handleChange} placeholder="Nombre de usuario" required minLength={3} />
          </div>
          <div className="form-group">
            <label htmlFor="email">Email *</label>
            <input id="email" name="email" type="email" value={form.email}
              onChange={handleChange} placeholder="correo@ejemplo.com" required />
          </div>
          <div className="form-group">
            <label htmlFor="nombre_completo">Nombre completo</label>
            <input id="nombre_completo" name="nombre_completo" type="text" value={form.nombre_completo}
              onChange={handleChange} placeholder="Tu nombre completo" />
          </div>
          <div className="form-group">
            <label htmlFor="password">Contrase�a *</label>
            <input id="password" name="password" type="password" value={form.password}
              onChange={handleChange} placeholder="M�nimo 6 caracteres" required minLength={6} />
          </div>
          <div className="form-group">
            <label htmlFor="confirm">Confirmar contrase�a *</label>
            <input id="confirm" name="confirm" type="password" value={form.confirm}
              onChange={handleChange} placeholder="Repite la contrase�a" required />
          </div>
          <button type="submit" className="btn-auth" disabled={loading}>
            {loading ? 'Registrando...' : 'Registrarse'}
          </button>
        </form>
        <div className="auth-footer">
          <Link to="/login">Ya tengo cuenta</Link>
          <Link to="/">Volver al Dashboard</Link>
        </div>
      </div>
    </div>
  )
}
