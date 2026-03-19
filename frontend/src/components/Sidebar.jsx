import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, ShoppingBag, ClipboardList,
  PhoneCall, BotMessageSquare, LogOut, Settings
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/products',  icon: ShoppingBag,     label: 'Products' },
  { to: '/orders',    icon: ClipboardList,   label: 'Orders' },
  { to: '/calls',     icon: PhoneCall,       label: 'Call History' },
  { to: '/profile',   icon: Settings,        label: 'Settings' },
]

function getInitials(name = '') {
  return name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <aside style={styles.sidebar}>
      <div style={styles.brand}>
        <BotMessageSquare size={22} color="var(--color-primary)" />
        <span style={styles.brandText}>AI Receptionist</span>
      </div>

      <nav style={styles.nav}>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => ({
              ...styles.navItem,
              ...(isActive ? styles.navItemActive : {}),
            })}
          >
            <Icon size={17} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div style={styles.userSection}>
        <div style={styles.avatar}>{getInitials(user?.name)}</div>
        <div style={styles.userInfo}>
          <div style={styles.userName}>{user?.name}</div>
          <div style={styles.userRole}>{user?.role}</div>
        </div>
        <button style={styles.logoutBtn} onClick={handleLogout} title="Sign out">
          <LogOut size={15} color="var(--color-text-muted)" />
        </button>
      </div>
    </aside>
  )
}

const styles = {
  sidebar: {
    width: 'var(--sidebar-width)',
    minWidth: 'var(--sidebar-width)',
    height: '100vh',
    background: 'var(--color-surface)',
    borderRight: '1px solid var(--color-border)',
    display: 'flex',
    flexDirection: 'column',
    position: 'sticky',
    top: 0,
  },
  brand: {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '22px 20px 18px',
    borderBottom: '1px solid var(--color-border)',
  },
  brandText: {
    fontWeight: 700, fontSize: 15, letterSpacing: '-0.2px', color: 'var(--color-text)',
  },
  nav: {
    display: 'flex', flexDirection: 'column', gap: 2,
    padding: '14px 10px', flex: 1,
  },
  navItem: {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '9px 12px', borderRadius: 'var(--radius-sm)',
    color: 'var(--color-text-muted)', fontWeight: 500,
    transition: 'background 0.15s, color 0.15s',
  },
  navItemActive: {
    background: 'var(--color-primary-soft)',
    color: 'var(--color-primary)',
  },
  userSection: {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '14px 16px',
    borderTop: '1px solid var(--color-border)',
  },
  avatar: {
    width: 32, height: 32, borderRadius: '50%',
    background: 'var(--color-primary-soft)',
    color: 'var(--color-primary)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontWeight: 700, fontSize: 12, flexShrink: 0,
  },
  userInfo: { flex: 1, overflow: 'hidden' },
  userName: {
    fontSize: 13, fontWeight: 600, color: 'var(--color-text)',
    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
  },
  userRole: {
    fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'capitalize',
  },
  logoutBtn: {
    background: 'transparent', padding: 4,
    borderRadius: 4, display: 'flex', flexShrink: 0,
    cursor: 'pointer',
  },
}
