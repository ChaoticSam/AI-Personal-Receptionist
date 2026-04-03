import { Link, Navigate } from 'react-router-dom'
import {
  BotMessageSquare,
  Phone,
  Sparkles,
  ClipboardCheck,
  ArrowRight,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const highlights = [
  {
    icon: Phone,
    title: 'Answers every call',
    text: 'Your AI receptionist picks up instantly, 24/7—never miss a lead.',
  },
  {
    icon: Sparkles,
    title: 'Sounds natural',
    text: 'Warm, on-brand conversations powered by modern voice AI.',
  },
  {
    icon: ClipboardCheck,
    title: 'Captures the details',
    text: 'Logs callers, orders, and handoffs so your team stays in sync.',
  },
]

export default function Onboarding() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div style={styles.page}>
        <div style={styles.loading}>Loading…</div>
      </div>
    )
  }

  if (user) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div style={styles.page}>
      <div style={styles.glow} aria-hidden />
      <div style={styles.inner}>
        <header style={styles.header}>
          <div style={styles.logo}>
            <BotMessageSquare size={26} color="var(--color-primary)" />
            <span style={styles.logoText}>AI Receptionist</span>
          </div>
        </header>

        <main style={styles.main}>
          <p style={styles.eyebrow}>Personal AI receptionist</p>
          <h1 style={styles.headline}>
            Turn every ring into a{' '}
            <span style={styles.headlineAccent}>handled conversation</span>
          </h1>
          <p style={styles.lede}>
            Train your assistant once—it greets callers, answers common questions,
            and routes what matters to you. Sign in to configure your business and voice.
          </p>

          <div style={styles.actions}>
            <Link to="/login" style={styles.loginBtn}>
              Log in
              <ArrowRight size={18} />
            </Link>
            <Link to="/register" style={styles.secondaryBtn}>
              Create account
            </Link>
          </div>

          <ul style={styles.list}>
            {highlights.map(({ icon: Icon, title, text }) => (
              <li key={title} style={styles.item}>
                <div style={styles.itemIcon}>
                  <Icon size={18} color="var(--color-primary)" />
                </div>
                <div>
                  <div style={styles.itemTitle}>{title}</div>
                  <div style={styles.itemText}>{text}</div>
                </div>
              </li>
            ))}
          </ul>
        </main>
      </div>
    </div>
  )
}

const styles = {
  page: {
    minHeight: '100vh',
    background: 'var(--color-bg)',
    color: 'var(--color-text)',
    position: 'relative',
    overflow: 'hidden',
  },
  glow: {
    position: 'absolute',
    width: 'min(720px, 90vw)',
    height: 'min(420px, 50vh)',
    top: '-12%',
    right: '-8%',
    background:
      'radial-gradient(ellipse at center, rgba(99, 102, 241, 0.22) 0%, transparent 65%)',
    pointerEvents: 'none',
  },
  inner: {
    position: 'relative',
    maxWidth: 920,
    margin: '0 auto',
    padding: '28px 24px 56px',
  },
  header: {
    marginBottom: 48,
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  logoText: {
    fontWeight: 700,
    fontSize: 17,
    letterSpacing: '-0.02em',
  },
  main: {
    maxWidth: 560,
  },
  loading: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--color-text-muted)',
    fontSize: 14,
  },
  eyebrow: {
    fontSize: 12,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.12em',
    color: 'var(--color-primary)',
    marginBottom: 14,
  },
  headline: {
    fontSize: 'clamp(1.85rem, 4vw, 2.5rem)',
    fontWeight: 700,
    lineHeight: 1.15,
    letterSpacing: '-0.03em',
    marginBottom: 16,
  },
  headlineAccent: {
    color: 'var(--color-primary)',
  },
  lede: {
    fontSize: 16,
    lineHeight: 1.65,
    color: 'var(--color-text-muted)',
    marginBottom: 32,
  },
  actions: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 48,
  },
  loginBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    background: 'var(--color-primary)',
    color: '#fff',
    fontWeight: 600,
    fontSize: 15,
    padding: '12px 22px',
    borderRadius: 'var(--radius)',
    transition: 'background 0.15s, transform 0.15s',
  },
  secondaryBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'transparent',
    color: 'var(--color-text)',
    fontWeight: 600,
    fontSize: 15,
    padding: '12px 22px',
    borderRadius: 'var(--radius)',
    border: '1px solid var(--color-border)',
  },
  list: {
    listStyle: 'none',
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
  },
  item: {
    display: 'flex',
    gap: 14,
    alignItems: 'flex-start',
  },
  itemIcon: {
    flexShrink: 0,
    width: 40,
    height: 40,
    borderRadius: 'var(--radius-sm)',
    background: 'var(--color-primary-soft)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  itemTitle: {
    fontWeight: 600,
    fontSize: 15,
    marginBottom: 4,
  },
  itemText: {
    fontSize: 14,
    color: 'var(--color-text-muted)',
    lineHeight: 1.5,
  },
}
