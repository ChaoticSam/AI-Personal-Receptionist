import { useState, useEffect } from 'react'
import { X, Loader2, Phone, Clock, FileText, MessageSquare } from 'lucide-react'
import { getCall } from '../services/api'

function formatDateTime(isoStr) {
  if (!isoStr) return '—'
  return new Date(isoStr).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function formatDuration(secs) {
  if (secs == null || secs === '') return null
  const n = Number(secs)
  if (Number.isNaN(n)) return null
  return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, '0')}`
}

export default function CallTranscriptModal({ callId, onClose }) {
  const [call, setCall]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    if (!callId) return
    setLoading(true)
    setError(null)
    getCall(callId)
      .then(res => setCall(res.data))
      .catch(() => setError('Failed to load transcript'))
      .finally(() => setLoading(false))
  }, [callId])

  // Close on Escape
  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!callId) return null

  const transcript = call?.transcript || []

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={e => e.stopPropagation()}>
        <div style={styles.header}>
          <div>
            <h2 style={styles.title}>Call Transcript</h2>
            {call && (
              <div style={styles.meta}>
                <span style={styles.metaItem}><Phone size={13} /> {call.caller_phone}</span>
                <span style={styles.metaItem}>{call.customer_name || 'Unknown'}</span>
                <span style={styles.metaItem}><Clock size={13} /> {formatDateTime(call.created_at)}</span>
                {formatDuration(call.duration) && <span style={styles.metaItem}>{formatDuration(call.duration)}</span>}
              </div>
            )}
          </div>
          <button style={styles.closeBtn} onClick={onClose} aria-label="Close"><X size={20} /></button>
        </div>

        <div style={styles.body}>
          {loading ? (
            <div style={styles.centered}>
              <Loader2 size={24} color="var(--color-primary)" style={{ animation: 'spin 1s linear infinite' }} />
            </div>
          ) : error ? (
            <div style={styles.errorMsg}>{error}</div>
          ) : (
            <>
              {call?.summary && (
                <div style={styles.summaryCard}>
                  <div style={styles.summaryLabel}><FileText size={14} /> Summary</div>
                  <p style={styles.summaryText}>{call.summary}</p>
                </div>
              )}

              {transcript.length === 0 ? (
                <div style={styles.empty}>
                  <MessageSquare size={28} color="var(--color-text-muted)" />
                  <p style={{ color: 'var(--color-text-muted)', marginTop: 10 }}>
                    No transcript available for this call yet.
                  </p>
                  {call?.notes && (
                    <pre style={styles.notes}>{call.notes}</pre>
                  )}
                </div>
              ) : (
                <div style={styles.thread}>
                  {transcript.map((turn, i) => {
                    const isAgent = turn.role === 'agent'
                    return (
                      <div key={i} style={{ ...styles.row, justifyContent: isAgent ? 'flex-start' : 'flex-end' }}>
                        <div style={{ ...styles.bubble, ...(isAgent ? styles.bubbleAgent : styles.bubbleUser) }}>
                          <div style={styles.bubbleRole}>{isAgent ? 'Clara (AI)' : 'Caller'}</div>
                          <div>{turn.message}</div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

const styles = {
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 20,
  },
  modal: {
    background: 'var(--color-surface)', border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius)', width: '100%', maxWidth: 720, maxHeight: '85vh',
    display: 'flex', flexDirection: 'column', overflow: 'hidden',
  },
  header: {
    display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
    padding: '18px 22px', borderBottom: '1px solid var(--color-border)',
  },
  title: { margin: 0, fontSize: 17, fontWeight: 600, color: 'var(--color-text)' },
  meta: { display: 'flex', flexWrap: 'wrap', gap: 14, marginTop: 8 },
  metaItem: {
    display: 'inline-flex', alignItems: 'center', gap: 5,
    color: 'var(--color-text-muted)', fontSize: 13,
  },
  closeBtn: {
    background: 'transparent', border: 'none', cursor: 'pointer',
    color: 'var(--color-text-muted)', padding: 4, display: 'flex',
  },
  body: { padding: 22, overflowY: 'auto' },
  centered: { display: 'flex', justifyContent: 'center', padding: 40 },
  errorMsg: {
    background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: 'var(--radius-sm)', color: '#ef4444', padding: '10px 14px', fontSize: 13,
  },
  summaryCard: {
    background: 'var(--color-surface-2)', border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)', padding: '12px 16px', marginBottom: 18,
  },
  summaryLabel: {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    color: 'var(--color-text-muted)', fontSize: 12, fontWeight: 600,
    textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6,
  },
  summaryText: { margin: 0, fontSize: 14, color: 'var(--color-text)', lineHeight: 1.5 },
  empty: { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 32 },
  notes: {
    marginTop: 14, width: '100%', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
    background: 'var(--color-surface-2)', border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)', padding: 12, fontSize: 13, color: 'var(--color-text)',
  },
  thread: { display: 'flex', flexDirection: 'column', gap: 10 },
  row: { display: 'flex' },
  bubble: { maxWidth: '78%', padding: '9px 13px', borderRadius: 14, fontSize: 14, lineHeight: 1.45 },
  bubbleAgent: {
    background: 'var(--color-surface-2)', color: 'var(--color-text)',
    border: '1px solid var(--color-border)', borderBottomLeftRadius: 4,
  },
  bubbleUser: {
    background: 'var(--color-primary-soft)', color: 'var(--color-text)',
    border: '1px solid var(--color-primary)', borderBottomRightRadius: 4,
  },
  bubbleRole: {
    fontSize: 11, fontWeight: 600, marginBottom: 3,
    color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em',
  },
}
