import { useState, useEffect } from 'react'
import { PhoneMissed, PhoneIncoming, Loader2 } from 'lucide-react'
import { getCalls } from '../services/api'

const statusConfig = {
  received: { icon: PhoneIncoming, color: '#22c55e', bg: 'rgba(34,197,94,0.12)',  label: 'Received' },
  missed:   { icon: PhoneMissed,   color: '#ef4444', bg: 'rgba(239,68,68,0.12)',  label: 'Missed' },
}

const allFilters = ['all', 'received', 'missed']

function formatDate(isoStr) {
  if (!isoStr) return '—'
  return new Date(isoStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function formatTime(isoStr) {
  if (!isoStr) return '—'
  return new Date(isoStr).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}

export default function CallHistory() {
  const [calls, setCalls]     = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter]   = useState('all')
  const [error, setError]     = useState(null)

  useEffect(() => {
    getCalls()
      .then(res => setCalls(res.data))
      .catch(() => setError('Failed to load call history'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = filter === 'all' ? calls : calls.filter(c => c.status === filter)

  return (
    <div style={styles.page}>
      <div style={styles.toolbar}>
        <div style={styles.filters}>
          {allFilters.map(f => (
            <button
              key={f}
              style={{ ...styles.filterBtn, ...(filter === f ? styles.filterBtnActive : {}) }}
              onClick={() => setFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <div style={styles.count}>{loading ? '…' : `${filtered.length} calls`}</div>
      </div>

      {error && <div style={styles.errorMsg}>{error}</div>}

      <div style={styles.tableCard}>
        {loading ? (
          <div style={styles.centered}>
            <Loader2 size={24} color="var(--color-primary)" style={{ animation: 'spin 1s linear infinite' }} />
          </div>
        ) : filtered.length === 0 ? (
          <div style={styles.empty}>
            <p style={{ color: 'var(--color-text-muted)' }}>No calls found.</p>
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                {['Status', 'Phone', 'Customer', 'Date', 'Time', 'Duration', 'Linked Order'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(call => {
                const cfg = statusConfig[call.status] || statusConfig.received
                const Icon = cfg.icon
                return (
                  <tr key={call.id} style={styles.tr}>
                    <td style={styles.td}>
                      <div style={{ ...styles.statusChip, background: cfg.bg }}>
                        <Icon size={13} color={cfg.color} />
                        <span style={{ color: cfg.color, fontSize: 12, fontWeight: 500 }}>{cfg.label}</span>
                      </div>
                    </td>
                    <td style={{ ...styles.td, fontFamily: 'monospace', fontSize: 13 }}>{call.caller_phone}</td>
                    <td style={{ ...styles.td, fontWeight: 500 }}>{call.customer_name || 'Unknown'}</td>
                    <td style={{ ...styles.td, color: 'var(--color-text-muted)' }}>{formatDate(call.created_at)}</td>
                    <td style={{ ...styles.td, color: 'var(--color-text-muted)' }}>{formatTime(call.created_at)}</td>
                    <td style={{ ...styles.td, color: 'var(--color-text-muted)' }}>{call.duration || '—'}</td>
                    <td style={styles.td}>
                      {call.linked_order_id
                        ? <span style={styles.orderLink}>{String(call.linked_order_id).slice(0, 8).toUpperCase()}</span>
                        : <span style={{ color: 'var(--color-text-muted)' }}>—</span>
                      }
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
  empty: { display: 'flex', justifyContent: 'center', padding: 48 },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: {
    textAlign: 'left', padding: '10px 16px',
    color: 'var(--color-text-muted)', fontWeight: 600, fontSize: 12,
    textTransform: 'uppercase', letterSpacing: '0.05em',
    borderBottom: '1px solid var(--color-border)', background: 'var(--color-surface-2)',
  },
  tr: { borderBottom: '1px solid var(--color-border)' },
  td: { padding: '13px 16px', fontSize: 14, color: 'var(--color-text)' },
  statusChip: {
    display: 'inline-flex', alignItems: 'center', gap: 5,
    padding: '4px 10px', borderRadius: 99,
  },
  orderLink: {
    background: 'var(--color-primary-soft)', color: 'var(--color-primary)',
    padding: '3px 10px', borderRadius: 99, fontSize: 12, fontWeight: 500, fontFamily: 'monospace',
  },
}
