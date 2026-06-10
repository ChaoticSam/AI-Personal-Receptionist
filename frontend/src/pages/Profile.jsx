import { useState, useEffect, useRef } from 'react'
import { User, Mic, Save, AlertCircle, CheckCircle, Play, Loader, Volume2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getBusiness, updateBusiness, getElevenLabsVoices, getConvaiLlmModels } from '../services/api'

const TABS = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'agent', label: 'AI Agent (ElevenLabs)', icon: Mic },
]

const TIMEZONES = [
  'Asia/Kolkata', 'Asia/Dubai', 'Asia/Singapore', 'Asia/Tokyo',
  'Europe/London', 'Europe/Berlin', 'America/New_York', 'America/Los_Angeles',
  'UTC',
]

const DEFAULT_AGENT = {
  elevenlabs_agent_id: '',
  convai_llm_model: '',
  convai_voice_id: '',
  first_message: '',
  language: 'en',
}

export default function Profile() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState('profile')
  const [business, setBusiness] = useState(null)

  const [profileForm, setProfileForm] = useState({
    name: '', business_type: '', phone_number: '',
    whatsapp_number: '', timezone: '', address: '',
  })

  const [agentForm, setAgentForm] = useState(DEFAULT_AGENT)

  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState(null)

  const [voices, setVoices] = useState([])
  const [llmModels, setLlmModels] = useState([])
  const [voicesLoading, setVoicesLoading] = useState(false)
  const [llmLoading, setLlmLoading] = useState(false)
  const [voicesLoaded, setVoicesLoaded] = useState(false)
  const [llmLoaded, setLlmLoaded] = useState(false)
  const [playingId, setPlayingId] = useState(null)
  const audioRef = useRef(null)

  useEffect(() => {
    if (user?.business_id) {
      getBusiness(user.business_id)
        .then(res => {
          const b = res.data
          setBusiness(b)
          setProfileForm({
            name: b.name || '',
            business_type: b.business_type || '',
            phone_number: b.phone_number || '',
            whatsapp_number: b.whatsapp_number || '',
            timezone: b.timezone || '',
            address: b.address || '',
          })
          const ui = b.agent_ui || {}
          setAgentForm({
            elevenlabs_agent_id: b.elevenlabs_agent_id || '',
            convai_llm_model: b.convai_llm_model || '',
            convai_voice_id: b.convai_voice_id || '',
            first_message: ui.first_message || '',
            language: ui.language || 'en',
          })
        })
        .catch(() => setStatus({ type: 'error', msg: 'Failed to load business profile.' }))
    }
  }, [user])

  function setAgent(key, value) {
    setAgentForm(prev => ({ ...prev, [key]: value }))
  }

  async function loadAgentCatalog() {
    setVoicesLoading(true)
    setLlmLoading(true)
    try {
      const [vRes, mRes] = await Promise.all([
        getElevenLabsVoices(),
        getConvaiLlmModels(),
      ])
      setVoices(vRes.data || [])
      setLlmModels(mRes.data || [])
      setVoicesLoaded(true)
      setLlmLoaded(true)
    } catch {
      setStatus({ type: 'error', msg: 'Failed to load ElevenLabs catalog (API key / network).' })
    } finally {
      setVoicesLoading(false)
      setLlmLoading(false)
    }
  }

  function playPreview(voice) {
    if (!voice.preview_url) return
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    if (playingId === voice.voice_id) {
      setPlayingId(null)
      return
    }
    const audio = new Audio(voice.preview_url)
    audioRef.current = audio
    setPlayingId(voice.voice_id)
    audio.play()
    audio.onended = () => setPlayingId(null)
    audio.onerror = () => setPlayingId(null)
  }

  async function handleSave() {
    setSaving(true)
    setStatus(null)
    try {
      if (activeTab === 'profile') {
        await updateBusiness(user.business_id, { ...profileForm })
      } else {
        await updateBusiness(user.business_id, {
          elevenlabs_agent_id: agentForm.elevenlabs_agent_id || null,
          convai_llm_model: agentForm.convai_llm_model || null,
          convai_voice_id: agentForm.convai_voice_id || null,
          agent_ui: {
            first_message: agentForm.first_message || null,
            language: agentForm.language || 'en',
          },
        })
      }
      const res = await getBusiness(user.business_id)
      setBusiness(res.data)
      setStatus({ type: 'success', msg: 'Changes saved successfully.' })
    } catch (err) {
      setStatus({ type: 'error', msg: err.response?.data?.detail || 'Failed to save changes.' })
    } finally {
      setSaving(false)
    }
  }

  const selectedVoiceName = voices.find(v => v.voice_id === agentForm.convai_voice_id)?.name

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h1 style={styles.title}>Settings</h1>
        <p style={styles.subtitle}>Profile and per-tenant ElevenLabs agent (voice + LLM)</p>
      </div>

      <div style={styles.tabBar}>
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            style={{ ...styles.tab, ...(activeTab === id ? styles.tabActive : {}) }}
            onClick={() => { setActiveTab(id); setStatus(null) }}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      {status && (
        <div style={{ ...styles.banner, ...(status.type === 'success' ? styles.bannerSuccess : styles.bannerError) }}>
          {status.type === 'success'
            ? <CheckCircle size={15} color="var(--color-success, #16a34a)" />
            : <AlertCircle size={15} color="var(--color-error, #dc2626)" />
          }
          {status.msg}
        </div>
      )}

      {activeTab === 'profile' && (
        <div style={styles.card}>
          <SectionTitle>Business Info</SectionTitle>

          <div style={styles.row}>
            <Field label="Business Name" required>
              <input
                style={styles.input}
                value={profileForm.name}
                onChange={e => setProfileForm(p => ({ ...p, name: e.target.value }))}
                placeholder="e.g. Shivam's Print Shop"
              />
            </Field>
            <Field label="Business Type">
              <input
                style={styles.input}
                value={profileForm.business_type}
                onChange={e => setProfileForm(p => ({ ...p, business_type: e.target.value }))}
                placeholder="e.g. Print & Frames"
              />
            </Field>
          </div>

          <div style={styles.row}>
            <Field label="Phone Number">
              <input
                style={styles.input}
                value={profileForm.phone_number}
                onChange={e => setProfileForm(p => ({ ...p, phone_number: e.target.value }))}
                placeholder="+91 98765 43210"
              />
            </Field>
            <Field label="WhatsApp Number">
              <input
                style={styles.input}
                value={profileForm.whatsapp_number}
                onChange={e => setProfileForm(p => ({ ...p, whatsapp_number: e.target.value }))}
                placeholder="+91 98765 43210"
              />
            </Field>
          </div>

          <div style={styles.row}>
            <Field label="Timezone">
              <select
                style={styles.input}
                value={profileForm.timezone}
                onChange={e => setProfileForm(p => ({ ...p, timezone: e.target.value }))}
              >
                <option value="">Select timezone</option>
                {TIMEZONES.map(tz => <option key={tz} value={tz}>{tz}</option>)}
              </select>
            </Field>
          </div>

          <Field label="Address">
            <textarea
              style={{ ...styles.input, height: 72, resize: 'vertical' }}
              value={profileForm.address}
              onChange={e => setProfileForm(p => ({ ...p, address: e.target.value }))}
              placeholder="Shop address"
            />
          </Field>

          <SectionTitle style={{ marginTop: 28 }}>Account</SectionTitle>
          <div style={styles.row}>
            <Field label="Your Name">
              <input style={{ ...styles.input, ...styles.inputReadonly }} value={user?.name || ''} readOnly />
            </Field>
            <Field label="Email">
              <input style={{ ...styles.input, ...styles.inputReadonly }} value={user?.email || ''} readOnly />
            </Field>
          </div>
          <Field label="Role">
            <input style={{ ...styles.input, ...styles.inputReadonly, textTransform: 'capitalize' }} value={user?.role || ''} readOnly />
          </Field>
        </div>
      )}

      {activeTab === 'agent' && (
        <div style={styles.card}>
          <p style={styles.sectionDesc}>
            Create one Conversational AI agent per business in the ElevenLabs dashboard, then paste its agent ID here.
            Saving pushes voice, LLM, and first message to ElevenLabs via API.
          </p>

          <Field label="ElevenLabs agent ID">
            <input
              style={styles.input}
              value={agentForm.elevenlabs_agent_id}
              onChange={e => setAgent('elevenlabs_agent_id', e.target.value)}
              placeholder="From ElevenLabs → Agents → your agent"
            />
          </Field>

          <Field label="LLM model">
            {!llmLoaded && (
              <button
                type="button"
                style={styles.loadBtn}
                onClick={loadAgentCatalog}
                disabled={llmLoading}
              >
                {llmLoading ? <Loader size={13} /> : null}
                Load models from ElevenLabs
              </button>
            )}
            {llmLoaded && (
              <select
                style={styles.input}
                value={agentForm.convai_llm_model}
                onChange={e => setAgent('convai_llm_model', e.target.value)}
              >
                <option value="">Select model</option>
                {llmModels.map(m => (
                  <option key={m.id} value={m.id}>{m.name || m.id}</option>
                ))}
              </select>
            )}
          </Field>

          <Field label="Agent language (ISO)">
            <input
              style={styles.input}
              value={agentForm.language}
              onChange={e => setAgent('language', e.target.value)}
              placeholder="en"
            />
          </Field>

          <Field label="First message">
            <textarea
              style={{ ...styles.input, height: 80, resize: 'vertical' }}
              value={agentForm.first_message}
              onChange={e => setAgent('first_message', e.target.value)}
              placeholder="What the agent says when the call starts"
            />
          </Field>

          <SectionTitle style={{ marginTop: 24 }}>Voice</SectionTitle>
          {!voicesLoaded && (
            <button
              type="button"
              style={styles.loadBtn}
              onClick={loadAgentCatalog}
              disabled={voicesLoading}
            >
              {voicesLoading ? <Loader size={13} /> : <Mic size={13} />}
              Load voices from ElevenLabs
            </button>
          )}

          {agentForm.convai_voice_id && (
            <div style={styles.selectedBadge}>
              <Volume2 size={13} />
              <span>Selected: <strong>{selectedVoiceName || agentForm.convai_voice_id}</strong></span>
            </div>
          )}

          {voicesLoaded && voices.length === 0 && (
            <p style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>No voices returned. Check ELEVENLABS_API_KEY.</p>
          )}

          {voicesLoaded && voices.length > 0 && (
            <div style={styles.voiceGrid}>
              {voices.map(voice => {
                const isSelected = agentForm.convai_voice_id === voice.voice_id
                const isPlaying = playingId === voice.voice_id
                return (
                  <div
                    key={voice.voice_id}
                    style={{ ...styles.voiceCard, ...(isSelected ? styles.voiceCardSelected : {}) }}
                    onClick={() => {
                      setAgent('convai_voice_id', voice.voice_id)
                    }}
                  >
                    <div style={styles.voiceCardTop}>
                      <div>
                        <div style={styles.voiceName}>{voice.name}</div>
                        <div style={styles.voiceCategory}>{voice.category}</div>
                      </div>
                      {voice.preview_url && (
                        <button
                          type="button"
                          style={{ ...styles.playBtn, ...(isPlaying ? styles.playBtnActive : {}) }}
                          onClick={e => { e.stopPropagation(); playPreview(voice) }}
                        >
                          {isPlaying ? <Volume2 size={13} /> : <Play size={13} />}
                        </button>
                      )}
                    </div>
                    {isSelected && <div style={styles.voiceSelectedMark}>✓ Selected</div>}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      <div style={styles.footer}>
        <button style={styles.saveBtn} onClick={handleSave} disabled={saving}>
          <Save size={15} />
          {saving ? 'Saving…' : 'Save Changes'}
        </button>
      </div>
    </div>
  )
}

function SectionTitle({ children, style }) {
  return <h3 style={{ ...sectionTitleStyle, ...style }}>{children}</h3>
}

function Field({ label, children, required }) {
  return (
    <div style={fieldStyles.wrapper}>
      <label style={fieldStyles.label}>
        {label}{required && <span style={{ color: 'var(--color-primary)' }}> *</span>}
      </label>
      {children}
    </div>
  )
}

const sectionTitleStyle = {
  fontSize: 13, fontWeight: 600, color: 'var(--color-text)',
  marginBottom: 14, marginTop: 0, letterSpacing: '0.02em',
  textTransform: 'uppercase', opacity: 0.6,
}

const fieldStyles = {
  wrapper: { display: 'flex', flexDirection: 'column', gap: 5, marginBottom: 16 },
  label: { fontSize: 13, fontWeight: 500, color: 'var(--color-text)' },
}

const styles = {
  page: { padding: '28px 32px', maxWidth: 760 },
  header: { marginBottom: 24 },
  title: { fontSize: 22, fontWeight: 700, color: 'var(--color-text)', margin: 0 },
  subtitle: { fontSize: 13, color: 'var(--color-text-muted)', marginTop: 4 },
  tabBar: {
    display: 'flex', gap: 4, marginBottom: 20,
    borderBottom: '1px solid var(--color-border)', paddingBottom: 0,
  },
  tab: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '8px 16px', fontSize: 13, fontWeight: 500,
    background: 'transparent', cursor: 'pointer',
    color: 'var(--color-text-muted)',
    borderBottom: '2px solid transparent', marginBottom: -1,
  },
  tabActive: {
    color: 'var(--color-primary)',
    borderBottomColor: 'var(--color-primary)',
  },
  banner: {
    display: 'flex', alignItems: 'center', gap: 8,
    padding: '10px 14px', borderRadius: 'var(--radius-sm)',
    fontSize: 13, marginBottom: 16,
  },
  bannerSuccess: { background: '#f0fdf4', color: '#15803d', border: '1px solid #bbf7d0' },
  bannerError: { background: '#fef2f2', color: '#b91c1c', border: '1px solid #fecaca' },
  card: {
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius)',
    padding: '24px 28px',
  },
  row: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
  input: {
    width: '100%', padding: '8px 11px',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)',
    fontSize: 13, color: 'var(--color-text)',
    background: 'var(--color-bg)',
    outline: 'none', boxSizing: 'border-box',
  },
  inputReadonly: {
    background: 'var(--color-surface)',
    color: 'var(--color-text-muted)',
    cursor: 'not-allowed',
  },
  sectionDesc: {
    fontSize: 12, color: 'var(--color-text-muted)', marginTop: 0, marginBottom: 16,
  },
  loadBtn: {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    padding: '8px 16px', fontSize: 13, fontWeight: 500,
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)', cursor: 'pointer',
    marginBottom: 8,
  },
  selectedBadge: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '7px 12px', marginBottom: 12,
    background: 'var(--color-primary-soft)',
    border: '1px solid var(--color-primary)',
    borderRadius: 'var(--radius-sm)',
    fontSize: 13, color: 'var(--color-primary)',
  },
  voiceGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: 10, marginTop: 8, maxHeight: 380, overflowY: 'auto', paddingRight: 4,
  },
  voiceCard: {
    padding: '10px 12px',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)', cursor: 'pointer',
    background: 'var(--color-bg)',
  },
  voiceCardSelected: {
    borderColor: 'var(--color-primary)',
    background: 'var(--color-primary-soft)',
  },
  voiceCardTop: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
  },
  voiceName: { fontSize: 13, fontWeight: 600, color: 'var(--color-text)', marginBottom: 2 },
  voiceCategory: { fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'capitalize' },
  playBtn: {
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    width: 26, height: 26, flexShrink: 0,
    border: '1px solid var(--color-border)', borderRadius: '50%',
    background: 'var(--color-surface)', cursor: 'pointer', color: 'var(--color-text-muted)',
  },
  playBtnActive: {
    background: 'var(--color-primary)',
    borderColor: 'var(--color-primary)', color: '#fff',
  },
  voiceSelectedMark: { marginTop: 6, fontSize: 11, fontWeight: 600, color: 'var(--color-primary)' },
  footer: { marginTop: 20, display: 'flex', justifyContent: 'flex-end' },
  saveBtn: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '9px 20px', fontSize: 13, fontWeight: 600,
    background: 'var(--color-primary)', color: '#fff',
    borderRadius: 'var(--radius-sm)', cursor: 'pointer',
  },
}
