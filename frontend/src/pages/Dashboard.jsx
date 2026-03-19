import { useState, useEffect } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar
} from 'recharts'
import { PhoneCall, ShoppingBag, ClipboardList, Users, Loader2 } from 'lucide-react'
import { getDashboardStats } from '../services/api'

const STAT_CONFIG = [
  { key: 'total_calls',     label: 'Total Calls',     icon: PhoneCall,     color: '#6366f1' },
  { key: 'total_orders',    label: 'Orders Placed',   icon: ClipboardList, color: '#22c55e' },
  { key: 'total_products',  label: 'Products Listed', icon: ShoppingBag,   color: '#f59e0b' },
  { key: 'total_customers', label: 'Customers',       icon: Users,         color: '#ec4899' },
]

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getDashboardStats()
      .then(res => setStats(res.data))
      .catch(() => setError('Failed to load dashboard data'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={styles.centered}>
      <Loader2 size={28} color="var(--color-primary)" style={{ animation: 'spin 1s linear infinite' }} />
    </div>
  )

  if (error) return <div style={styles.errorMsg}>{error}</div>

  const callChartData  = (stats?.calls_this_week  || []).map(d => ({ day: d.day, calls: d.count }))
  const orderChartData = (stats?.orders_this_week || []).map(d => ({ day: d.day, orders: d.count }))

  return (
    <div style={styles.page}>
      {/* Stats Row */}
      <div style={styles.statsGrid}>
        {STAT_CONFIG.map(({ key, label, icon: Icon, color }) => (
          <div key={key} style={styles.statCard}>
            <div style={{ ...styles.statIcon, background: color + '20' }}>
              <Icon size={18} color={color} />
            </div>
            <div>
              <div style={styles.statValue}>{stats?.[key] ?? 0}</div>
              <div style={styles.statLabel}>{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div style={styles.chartsRow}>
        <div style={styles.chartCard}>
          <div style={styles.chartTitle}>Calls This Week</div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={callChartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="callGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis dataKey="day" tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Area type="monotone" dataKey="calls" stroke="#6366f1" fill="url(#callGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div style={styles.chartCard}>
          <div style={styles.chartTitle}>Orders This Week</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={orderChartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis dataKey="day" tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="orders" fill="#22c55e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Calls */}
      <div style={styles.tableCard}>
        <div style={styles.chartTitle}>Recent Calls</div>
        {(!stats?.recent_calls?.length) ? (
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13, padding: '12px 0' }}>No calls yet.</p>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                {['Phone', 'Time', 'Status'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {stats.recent_calls.map(call => (
                <tr key={call.id} style={styles.tr}>
                  <td style={styles.td}>{call.phone}</td>
                  <td style={{ ...styles.td, color: 'var(--color-text-muted)' }}>{call.time}</td>
                  <td style={styles.td}>
                    <span style={styles.badge}>{call.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

const tooltipStyle = {
  background: 'var(--color-surface-2)',
  border: '1px solid var(--color-border)',
  borderRadius: 8,
  color: 'var(--color-text)',
  fontSize: 13,
}

const styles = {
  page: { display: 'flex', flexDirection: 'column', gap: 24 },
  centered: { display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 },
  errorMsg: { color: '#ef4444', padding: 16, fontSize: 14 },
  statsGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 },
  statCard: {
    background: 'var(--color-surface)', border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius)', padding: '18px 20px',
    display: 'flex', alignItems: 'center', gap: 16,
  },
  statIcon: {
    width: 42, height: 42, borderRadius: 'var(--radius-sm)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  statValue: { fontSize: 24, fontWeight: 700, lineHeight: 1.2 },
  statLabel: { fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 },
  chartsRow: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
  chartCard: {
    background: 'var(--color-surface)', border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius)', padding: '20px 20px 12px',
  },
  chartTitle: { fontWeight: 600, fontSize: 14, marginBottom: 16, color: 'var(--color-text)' },
  tableCard: {
    background: 'var(--color-surface)', border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius)', padding: '20px',
  },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: {
    textAlign: 'left', padding: '8px 12px',
    color: 'var(--color-text-muted)', fontWeight: 600, fontSize: 12,
    textTransform: 'uppercase', letterSpacing: '0.05em',
    borderBottom: '1px solid var(--color-border)',
  },
  tr: { borderBottom: '1px solid var(--color-border)' },
  td: { padding: '12px 12px', fontSize: 14, color: 'var(--color-text)' },
  badge: {
    background: 'rgba(34, 197, 94, 0.12)', color: '#22c55e',
    padding: '3px 10px', borderRadius: 99, fontSize: 12, fontWeight: 500,
  },
}
