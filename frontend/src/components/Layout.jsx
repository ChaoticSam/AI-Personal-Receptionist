import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'

const pageTitles = {
  '/dashboard': 'Dashboard',
  '/products':  'Products',
  '/orders':    'Orders',
  '/calls':     'Call History',
}

export default function Layout() {
  const location = useLocation()
  const title = pageTitles[location.pathname] ?? 'AI Receptionist'

  return (
    <div style={styles.shell}>
      <Sidebar />
      <div style={styles.main}>
        <header style={styles.header}>
          <h1 style={styles.pageTitle}>{title}</h1>
        </header>
        <main style={styles.content}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

const styles = {
  shell: {
    display: 'flex',
    minHeight: '100vh',
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'auto',
  },
  header: {
    padding: '20px 28px 16px',
    borderBottom: '1px solid var(--color-border)',
    background: 'var(--color-surface)',
    position: 'sticky',
    top: 0,
    zIndex: 10,
  },
  pageTitle: {
    fontSize: 18,
    fontWeight: 700,
    color: 'var(--color-text)',
  },
  content: {
    padding: '28px',
    flex: 1,
  },
}
