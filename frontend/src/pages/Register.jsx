import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { BotMessageSquare, Mail, Lock, User, Building2, Phone, Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const initialForm = {
  name: '',
  email: '',
  password: '',
  business_name: '',
  business_type: '',
  phone_number: '',
  role: 'owner',
}

export default function Register() {
  const { register, loading, error } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)

  function handleChange(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const ok = await register(form)
    if (ok) navigate('/dashboard')
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.logo}>
          <BotMessageSquare size={28} color="var(--color-primary)" />
          <span style={styles.logoText}>AI Receptionist</span>
        </div>

        <h2 style={styles.title}>Create your account</h2>
        <p style={styles.subtitle}>Set up your business in minutes</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.section}>
            <p style={styles.sectionLabel}>Your Details</p>
            <div style={styles.row}>
              <Field label="Full Name" icon={User}>
                <input name="name" value={form.name} onChange={handleChange}
                  placeholder="Priya Sharma" style={styles.input} required />
              </Field>
              <Field label="Email" icon={Mail}>
                <input name="email" type="email" value={form.email} onChange={handleChange}
                  placeholder="you@example.com" style={styles.input} required />
              </Field>
            </div>
            <Field label="Password" icon={Lock}>
              <input name="password" type="password" value={form.password} onChange={handleChange}
                placeholder="Min 8 characters" style={styles.input} required minLength={8} />
            </Field>
          </div>

          <div style={styles.divider} />

          <div style={styles.section}>
            <p style={styles.sectionLabel}>Business Details</p>
            <div style={styles.row}>
              <Field label="Business Name" icon={Building2}>
                <input name="business_name" value={form.business_name} onChange={handleChange}
                  placeholder="Giftify" style={styles.input} required />
              </Field>
              <Field label="Business Type" icon={null}>
                <select name="business_type" value={form.business_type} onChange={handleChange} style={styles.input}>
                  <option value="">Select type</option>
                  <option value="gift_shop">Gift Shop</option>
                  <option value="restaurant">Restaurant</option>
                  <option value="salon">Salon</option>
                  <option value="medical">Medical Clinic</option>
                  <option value="retail">Retail Store</option>
                  <option value="other">Other</option>
                </select>
              </Field>
            </div>
            <Field label="Phone Number" icon={Phone}>
              <input name="phone_number" value={form.phone_number} onChange={handleChange}
                placeholder="+91 98765 43210" style={styles.input} required />
            </Field>
          </div>

          {error && <div style={styles.error}>{error}</div>}

          <button type="submit" style={styles.submitBtn} disabled={loading}>
            {loading
              ? <><Loader2 size={15} style={styles.spin} /> Creating account…</>
              : 'Create Account'
            }
          </button>
        </form>

        <p style={styles.footer}>
          Already have an account?{' '}
          <Link to="/login" style={styles.link}>Sign in</Link>
        </p>
      </div>
    </div>
  )
}

function Field({ label, icon: Icon, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1 }}>
      <label style={fieldStyles.label}>{label}</label>
      <div style={{ position: 'relative' }}>
        {Icon && <Icon size={15} color="var(--color-text-muted)" style={fieldStyles.icon} />}
        {children}
      </div>
    </div>
  )
}

const fieldStyles = {
  label: {
    fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)',
    textTransform: 'uppercase', letterSpacing: '0.04em',
  },
  icon: {
    position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
    pointerEvents: 'none',
  },
}

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'var(--color-bg)', padding: 20,
  },
  card: {
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 14, padding: '36px 32px',
    width: '100%', maxWidth: 520,
  },
  logo: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 },
  logoText: { fontWeight: 700, fontSize: 16, color: 'var(--color-text)' },
  title: { fontSize: 22, fontWeight: 700, color: 'var(--color-text)', marginBottom: 6 },
  subtitle: { fontSize: 14, color: 'var(--color-text-muted)', marginBottom: 24 },
  form: { display: 'flex', flexDirection: 'column', gap: 16 },
  section: { display: 'flex', flexDirection: 'column', gap: 14 },
  sectionLabel: {
    fontSize: 11, fontWeight: 700, color: 'var(--color-text-muted)',
    textTransform: 'uppercase', letterSpacing: '0.08em',
  },
  row: { display: 'flex', gap: 12 },
  divider: { height: 1, background: 'var(--color-border)', margin: '4px 0' },
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
    color: '#ef4444', padding: '10px 14px', fontSize: 13,
  },
  submitBtn: {
    background: 'var(--color-primary)', color: '#fff',
    padding: 11, borderRadius: 'var(--radius-sm)',
    fontWeight: 600, fontSize: 14,
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    marginTop: 4,
  },
  spin: { animation: 'spin 1s linear infinite' },
  footer: {
    textAlign: 'center', marginTop: 20, fontSize: 13, color: 'var(--color-text-muted)',
  },
  link: { color: 'var(--color-primary)', fontWeight: 600 },
}
