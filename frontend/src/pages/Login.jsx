import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { BotMessageSquare, Mail, Lock, Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login, loading, error } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })

  function handleChange(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const ok = await login(form.email, form.password)
    if (ok) navigate('/dashboard')
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.logo}>
          <BotMessageSquare size={28} color="var(--color-primary)" />
          <span style={styles.logoText}>AI Receptionist</span>
        </div>

        <h2 style={styles.title}>Welcome back</h2>
        <p style={styles.subtitle}>Sign in to your account</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.field}>
            <label style={styles.label}>Email</label>
            <div style={styles.inputWrapper}>
              <Mail size={15} color="var(--color-text-muted)" style={styles.inputIcon} />
              <input
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder="you@example.com"
                style={styles.input}
                required
              />
            </div>
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Password</label>
            <div style={styles.inputWrapper}>
              <Lock size={15} color="var(--color-text-muted)" style={styles.inputIcon} />
              <input
                name="password"
                type="password"
                value={form.password}
                onChange={handleChange}
                placeholder="••••••••"
                style={styles.input}
                required
              />
            </div>
          </div>

          {error && <div style={styles.error}>{error}</div>}

          <button type="submit" style={styles.submitBtn} disabled={loading}>
            {loading
              ? <><Loader2 size={15} style={styles.spin} /> Signing in…</>
              : 'Sign In'
            }
          </button>
        </form>

        <p style={styles.footer}>
          Don't have an account?{' '}
          <Link to="/register" style={styles.link}>Create one</Link>
        </p>
      </div>
    </div>
  )
}

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--color-bg)',
    padding: 20,
  },
  card: {
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 14,
    padding: '36px 32px',
    width: '100%',
    maxWidth: 400,
  },
  logo: {
    display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28,
  },
  logoText: {
    fontWeight: 700, fontSize: 16, color: 'var(--color-text)',
  },
  title: {
    fontSize: 22, fontWeight: 700, color: 'var(--color-text)', marginBottom: 6,
  },
  subtitle: {
    fontSize: 14, color: 'var(--color-text-muted)', marginBottom: 24,
  },
  form: { display: 'flex', flexDirection: 'column', gap: 18 },
  field: { display: 'flex', flexDirection: 'column', gap: 6 },
  label: {
    fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)',
    textTransform: 'uppercase', letterSpacing: '0.04em',
  },
  inputWrapper: { position: 'relative' },
  inputIcon: {
    position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
    pointerEvents: 'none',
  },
  input: {
    width: '100%',
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)',
    color: 'var(--color-text)',
    padding: '10px 12px 10px 36px',
    outline: 'none',
    fontSize: 14,
  },
  error: {
    background: 'rgba(239,68,68,0.1)',
    border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: 'var(--radius-sm)',
    color: '#ef4444',
    padding: '10px 14px',
    fontSize: 13,
  },
  submitBtn: {
    background: 'var(--color-primary)',
    color: '#fff',
    padding: '11px',
    borderRadius: 'var(--radius-sm)',
    fontWeight: 600,
    fontSize: 14,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 4,
  },
  spin: { animation: 'spin 1s linear infinite' },
  footer: {
    textAlign: 'center', marginTop: 20, fontSize: 13, color: 'var(--color-text-muted)',
  },
  link: { color: 'var(--color-primary)', fontWeight: 600 },
}
