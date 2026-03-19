import { createContext, useContext, useState, useEffect } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

const TOKEN_KEY = 'ai_receptionist_token'
const USER_KEY  = 'ai_receptionist_user'

export function AuthProvider({ children }) {
  const [user, setUser]   = useState(() => {
    const stored = localStorage.getItem(USER_KEY)
    return stored ? JSON.parse(stored) : null
  })
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState(null)

  useEffect(() => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    } else {
      delete api.defaults.headers.common['Authorization']
    }
  }, [token])

  function saveSession(data) {
    localStorage.setItem(TOKEN_KEY, data.access_token)
    const userData = {
      id: data.user_id,
      name: data.name,
      email: data.email,
      role: data.role,
      business_id: data.business_id,
    }
    localStorage.setItem(USER_KEY, JSON.stringify(userData))
    setToken(data.access_token)
    setUser(userData)
  }

  async function login(email, password) {
    setLoading(true)
    setError(null)
    try {
      const res = await api.post('/auth/login', { email, password })
      saveSession(res.data)
      return true
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
      return false
    } finally {
      setLoading(false)
    }
  }

  async function register(payload) {
    setLoading(true)
    setError(null)
    try {
      const res = await api.post('/auth/register', payload)
      saveSession(res.data)
      return true
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed')
      return false
    } finally {
      setLoading(false)
    }
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, error, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
