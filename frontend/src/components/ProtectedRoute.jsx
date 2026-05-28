import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div style={{
        width: '100%', height: '100vh',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        backgroundColor: '#0f172a', color: '#94a3b8', fontSize: '1.2rem',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '40px', height: '40px', margin: '0 auto 1rem',
            border: '3px solid #334155', borderTopColor: '#22c55e',
            borderRadius: '50%', animation: 'spin 0.8s linear infinite',
          }} />
          Cargando...
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return children
}
