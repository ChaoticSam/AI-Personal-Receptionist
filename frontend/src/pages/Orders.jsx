import { useState, useEffect } from 'react'
import { ClipboardList, Loader2 } from 'lucide-react'
import { getOrders, updateOrderStatus } from '../services/api'

const statusColors = {
  pending:   { bg: 'rgba(245,158,11,0.12)',  color: '#f59e0b' },
  confirmed: { bg: 'rgba(99,102,241,0.12)',  color: '#6366f1' },
  delivered: { bg: 'rgba(34,197,94,0.12)',   color: '#22c55e' },
  cancelled: { bg: 'rgba(239,68,68,0.12)',   color: '#ef4444' },
}

const allStatuses = ['all', 'pending', 'confirmed', 'delivered', 'cancelled']

function formatDate(isoStr) {
  if (!isoStr) return '—'
  return new Date(isoStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function Orders() {
  const [orders, setOrders]   = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter]   = useState('all')
  const [error, setError]     = useState(null)

  useEffect(() => {
    getOrders()
      .then(res => setOrders(res.data))
      .catch(() => setError('Failed to load orders'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = filter === 'all' ? orders : orders.filter(o => o.status === filter)

  async function handleStatusChange(orderId, newStatus) {
    try {
      await updateOrderStatus(orderId, newStatus)
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: newStatus } : o))
    } catch {
      setError('Failed to update order status')
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.toolbar}>
        <div style={styles.filters}>
          {allStatuses.map(s => (
            <button
              key={s}
              style={{ ...styles.filterBtn, ...(filter === s ? styles.filterBtnActive : {}) }}
              onClick={() => setFilter(s)}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
        <div style={styles.count}>{loading ? '…' : `${filtered.length} orders`}</div>
      </div>

      {error && <div style={styles.errorMsg}>{error}</div>}

      <div style={styles.tableCard}>
        {loading ? (
          <div style={styles.centered}>
            <Loader2 size={24} color="var(--color-primary)" style={{ animation: 'spin 1s linear infinite' }} />
          </div>
        ) : filtered.length === 0 ? (
          <div style={styles.empty}>
            <ClipboardList size={36} color="var(--color-text-muted)" />
            <p>No orders found.</p>
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                {['Order ID', 'Customer', 'Phone', 'Product', 'Qty', 'Date', 'Status'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(order => {
                const sc = statusColors[order.status] || {}
                return (
                  <tr key={order.id} style={styles.tr}>
                    <td style={{ ...styles.td, fontFamily: 'monospace', fontSize: 12 }}>
                      {String(order.id).slice(0, 8).toUpperCase()}
                    </td>
                    <td style={{ ...styles.td, fontWeight: 500 }}>{order.customer_name || '—'}</td>
                    <td style={{ ...styles.td, color: 'var(--color-text-muted)' }}>{order.customer_phone || '—'}</td>
                    <td style={styles.td}>{order.product_name || '—'}</td>
                    <td style={{ ...styles.td, color: 'var(--color-text-muted)' }}>{order.quantity}</td>
                    <td style={{ ...styles.td, color: 'var(--color-text-muted)' }}>{formatDate(order.created_at)}</td>
                    <td style={styles.td}>
                      <select
                        value={order.status}
                        onChange={e => handleStatusChange(order.id, e.target.value)}
                        style={{ ...styles.statusSelect, background: sc.bg, color: sc.color, border: `1px solid ${sc.color}40` }}
                      >
                        {['pending', 'confirmed', 'delivered', 'cancelled'].map(s => (
                          <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

const styles = {
  page: { display: 'flex', flexDirection: 'column', gap: 20 },
  toolbar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  filters: { display: 'flex', gap: 6 },
  filterBtn: {
    padding: '6px 14px', borderRadius: 99,
    background: 'transparent', color: 'var(--color-text-muted)',
    border: '1px solid var(--color-border)', fontSize: 13, fontWeight: 500, cursor: 'pointer',
  },
  filterBtnActive: {
    background: 'var(--color-primary-soft)', color: 'var(--color-primary)',
    border: '1px solid var(--color-primary)',
  },
  count: { color: 'var(--color-text-muted)', fontSize: 13 },
  errorMsg: {
    background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: 'var(--radius-sm)', color: '#ef4444', padding: '10px 14px', fontSize: 13,
  },
  tableCard: {
    background: 'var(--color-surface)', border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius)', overflow: 'hidden',
  },
  centered: { display: 'flex', justifyContent: 'center', padding: 40 },
  empty: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    gap: 12, padding: 48, color: 'var(--color-text-muted)',
  },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: {
    textAlign: 'left', padding: '10px 16px',
    color: 'var(--color-text-muted)', fontWeight: 600, fontSize: 12,
    textTransform: 'uppercase', letterSpacing: '0.05em',
    borderBottom: '1px solid var(--color-border)', background: 'var(--color-surface-2)',
  },
  tr: { borderBottom: '1px solid var(--color-border)' },
  td: { padding: '13px 16px', fontSize: 14, color: 'var(--color-text)' },
  statusSelect: {
    borderRadius: 99, padding: '4px 10px', fontSize: 12, fontWeight: 500,
    cursor: 'pointer', outline: 'none', appearance: 'none',
  },
}
