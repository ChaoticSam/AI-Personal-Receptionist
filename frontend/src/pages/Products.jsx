import { useState, useEffect } from 'react'
import { Plus, X, Package, Loader2 } from 'lucide-react'
import { getProducts, addProduct, updateProduct } from '../services/api'

export default function Products() {
  const [products, setProducts] = useState([])
  const [loading, setLoading]   = useState(true)
  const [saving, setSaving]     = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm]         = useState({ name: '', description: '', price: '', unit: '' })
  const [error, setError]       = useState(null)

  useEffect(() => {
    getProducts()
      .then(res => setProducts(res.data))
      .catch(() => setError('Failed to load products'))
      .finally(() => setLoading(false))
  }, [])

  function handleChange(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.name.trim()) return
    setSaving(true)
    try {
      const res = await addProduct({
        name: form.name,
        description: form.description || null,
        price: form.price ? parseFloat(form.price) : null,
        unit: form.unit || null,
      })
      setProducts(p => [res.data, ...p])
      setForm({ name: '', description: '', price: '', unit: '' })
      setShowForm(false)
    } catch {
      setError('Failed to add product')
    } finally {
      setSaving(false)
    }
  }

  async function toggleAvailable(product) {
    const newVal = product.is_available === 'true' ? 'false' : 'true'
    try {
      const res = await updateProduct(product.id, { is_available: newVal })
      setProducts(p => p.map(prod => prod.id === product.id ? res.data : prod))
    } catch {
      setError('Failed to update product')
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.toolbar}>
        <div style={styles.count}>
          {loading ? '…' : `${products.length} products`}
        </div>
        <button style={styles.addBtn} onClick={() => setShowForm(true)}>
          <Plus size={15} />
          Add Product
        </button>
      </div>

      {error && <div style={styles.errorMsg}>{error}</div>}

      {showForm && (
        <div style={styles.formCard}>
          <div style={styles.formHeader}>
            <span style={{ fontWeight: 600 }}>New Product</span>
            <button style={styles.closeBtn} onClick={() => setShowForm(false)}>
              <X size={16} />
            </button>
          </div>
          <form onSubmit={handleSubmit} style={styles.form}>
            <div style={styles.formRow}>
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Name *</label>
                <input name="name" value={form.name} onChange={handleChange} placeholder="e.g. Rose Bouquet" style={styles.input} required />
              </div>
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Unit</label>
                <input name="unit" value={form.unit} onChange={handleChange} placeholder="e.g. bouquet" style={styles.input} />
              </div>
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Price</label>
                <input name="price" value={form.price} onChange={handleChange} placeholder="e.g. 499" type="number" style={styles.input} />
              </div>
            </div>
            <div style={styles.fieldGroup}>
              <label style={styles.label}>Description</label>
              <input name="description" value={form.description} onChange={handleChange} placeholder="Short description" style={styles.input} />
            </div>
            <div style={styles.formActions}>
              <button type="button" style={styles.cancelBtn} onClick={() => setShowForm(false)}>Cancel</button>
              <button type="submit" style={styles.submitBtn} disabled={saving}>
                {saving ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : 'Add Product'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div style={styles.tableCard}>
        {loading ? (
          <div style={styles.centered}>
            <Loader2 size={24} color="var(--color-primary)" style={{ animation: 'spin 1s linear infinite' }} />
          </div>
        ) : products.length === 0 ? (
          <div style={styles.empty}>
            <Package size={36} color="var(--color-text-muted)" />
            <p>No products yet. Add your first product.</p>
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                {['Name', 'Description', 'Price', 'Unit', 'Status'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {products.map(prod => (
                <tr key={prod.id} style={styles.tr}>
                  <td style={{ ...styles.td, fontWeight: 500 }}>{prod.name}</td>
                  <td style={{ ...styles.td, color: 'var(--color-text-muted)' }}>{prod.description || '—'}</td>
                  <td style={styles.td}>{prod.price ? `₹${prod.price}` : '—'}</td>
                  <td style={{ ...styles.td, color: 'var(--color-text-muted)' }}>{prod.unit || '—'}</td>
                  <td style={styles.td}>
                    <button
                      style={{ ...styles.statusBadge, ...(prod.is_available === 'true' ? styles.statusActive : styles.statusInactive) }}
                      onClick={() => toggleAvailable(prod)}
                    >
                      {prod.is_available === 'true' ? 'Available' : 'Unavailable'}
                    </button>
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

const styles = {
  page: { display: 'flex', flexDirection: 'column', gap: 20 },
  toolbar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  count: { color: 'var(--color-text-muted)', fontSize: 13 },
  addBtn: {
    display: 'flex', alignItems: 'center', gap: 6,
    background: 'var(--color-primary)', color: '#fff',
    padding: '8px 16px', borderRadius: 'var(--radius-sm)',
    fontWeight: 600, fontSize: 13,
  },
  errorMsg: {
    background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: 'var(--radius-sm)', color: '#ef4444', padding: '10px 14px', fontSize: 13,
  },
  formCard: {
    background: 'var(--color-surface)', border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius)', padding: 20,
  },
  formHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 },
  closeBtn: { background: 'transparent', color: 'var(--color-text-muted)', padding: 4, borderRadius: 4, display: 'flex' },
  form: { display: 'flex', flexDirection: 'column', gap: 14 },
  formRow: { display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 12 },
  fieldGroup: { display: 'flex', flexDirection: 'column', gap: 6 },
  label: { fontSize: 12, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' },
  input: {
    background: 'var(--color-surface-2)', border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)', color: 'var(--color-text)',
    padding: '8px 12px', outline: 'none', width: '100%',
  },
  formActions: { display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 4 },
  cancelBtn: {
    background: 'transparent', color: 'var(--color-text-muted)',
    border: '1px solid var(--color-border)', padding: '8px 16px',
    borderRadius: 'var(--radius-sm)', fontWeight: 500, fontSize: 13,
  },
  submitBtn: {
    background: 'var(--color-primary)', color: '#fff', padding: '8px 16px',
    borderRadius: 'var(--radius-sm)', fontWeight: 600, fontSize: 13,
    display: 'flex', alignItems: 'center', gap: 6,
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
  statusBadge: { padding: '4px 12px', borderRadius: 99, fontSize: 12, fontWeight: 500, cursor: 'pointer' },
  statusActive: { background: 'rgba(34,197,94,0.12)', color: '#22c55e' },
  statusInactive: { background: 'rgba(239,68,68,0.12)', color: '#ef4444' },
}
