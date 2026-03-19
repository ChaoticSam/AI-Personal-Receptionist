import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('ai_receptionist_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('ai_receptionist_token')
      localStorage.removeItem('ai_receptionist_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// Auth
export const authLogin    = (data) => api.post('/auth/login', data)
export const authRegister = (data) => api.post('/auth/register', data)
export const getMe        = ()     => api.get('/auth/me')

// Dashboard
export const getDashboardStats = () => api.get('/dashboard/stats')

// Products
export const getProducts      = ()          => api.get('/products')
export const addProduct       = (data)      => api.post('/products', data)
export const updateProduct    = (id, data)  => api.patch(`/products/${id}`, data)

// Orders
export const getOrders        = ()                => api.get('/orders')
export const createOrder      = (data)            => api.post('/orders', data)
export const updateOrderStatus = (id, status)     => api.patch(`/orders/${id}/status`, { status })

// Calls
export const getCalls         = ()          => api.get('/calls')
export const logIncomingCall  = (phone, businessId, callerName) =>
  api.post('/calls/incoming', null, { params: { phone, business_id: businessId, caller_name: callerName } })

// Business
export const registerBusiness = (data)         => api.post('/business/register', data)
export const getBusiness      = (id)            => api.get(`/business/${id}`)
export const updateBusiness   = (id, data)      => api.patch(`/business/${id}`, data)

// Voice
export const getElevenLabsVoices = () => api.get('/voice/voices')

export default api
