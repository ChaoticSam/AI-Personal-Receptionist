import { useState, useEffect, useRef } from 'react'
import { User, Mic, Save, AlertCircle, CheckCircle, Play, Loader, Volume2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getBusiness, updateBusiness, getElevenLabsVoices } from '../services/api'

const TABS = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'voice',   label: 'Voice Settings', icon: Mic },
]

const TIMEZONES = [
  'Asia/Kolkata', 'Asia/Dubai', 'Asia/Singapore', 'Asia/Tokyo',
  'Europe/London', 'Europe/Berlin', 'America/New_York', 'America/Los_Angeles',
  'UTC',
]

const LANGUAGES = [
  { value: 'en-IN', label: 'English (India)' },
  { value: 'en-US', label: 'English (US)' },
  { value: 'en-GB', label: 'English (UK)' },
  { value: 'hi-IN', label: 'Hindi' },
  { value: 'mr-IN', label: 'Marathi' },
  { value: 'ta-IN', label: 'Tamil' },
  { value: 'te-IN', label: 'Telugu' },
]

const VAD_SENSITIVITY_OPTIONS = [
  { value: 'low',    label: 'Low',    desc: 'Waits longer before deciding you stopped speaking' },
  { value: 'medium', label: 'Medium', desc: 'Balanced — works for most businesses' },
  { value: 'high',   label: 'High',   desc: 'Responds quickly; cuts off sooner' },
]

const DEFAULT_VOICE = {
  silence_threshold_ms: 1000,
  endpointing_ms: 300,
  vad_sensitivity: 'medium',
  language: 'en-IN',
  greeting_message: '',
  tts_voice_id: '',
  tts_voice_name: '',
}

export default function Profile() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState('profile')
  const [business, setBusiness] = useState(null)

  const [profileForm, setProfileForm] = useState({
    name: '', business_type: '', phone_number: '',
    whatsapp_number: '', timezone: '', address: '',
  })

  const [voiceForm, setVoiceForm] = useState(DEFAULT_VOICE)

  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState(null) // { type: 'success'|'error', msg: string }

  // Voice picker state
  const [voices, setVoices] = useState([])
  const [voicesLoading, setVoicesLoading] = useState(false)
  const [voicesLoaded, setVoicesLoaded] = useState(false)
  const [playingId, setPlayingId] = useState(null)
  const audioRef = useRef(null)

  useEffect(() => {
    if (user?.business_id) {
      getBusiness(user.business_id)
        .then(res => {
          const b = res.data
          setBusiness(b)
          setProfileForm({
            name:            b.name            || '',
            business_type:   b.business_type   || '',
            phone_number:    b.phone_number     || '',
            whatsapp_number: b.whatsapp_number  || '',
            timezone:        b.timezone         || '',
            address:         b.address          || '',
          })
          setVoiceForm({
            ...DEFAULT_VOICE,
            ...(b.voice_config || {}),
          })
        })
        .catch(() => setStatus({ type: 'error', msg: 'Failed to load business profile.' }))
    }
  }, [user])

  function setVoice(key, value) {
    setVoiceForm(prev => ({ ...prev, [key]: value }))
  }

  async function loadVoices() {
    setVoicesLoading(true)
    try {
      const res = await getElevenLabsVoices()
      setVoices(res.data || [])
      setVoicesLoaded(true)
    } catch {
      setStatus({ type: 'error', msg: 'Failed to load voices from ElevenLabs.' })
    } finally {
      setVoicesLoading(false)
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
      const payload = activeTab === 'profile'
        ? { ...profileForm }
        : { voice_config: { ...voiceForm } }

      const res = await updateBusiness(user.business_id, payload)
      setBusiness(res.data)
      setStatus({ type: 'success', msg: 'Changes saved successfully.' })
    } catch (err) {
      setStatus({ type: 'error', msg: err.response?.data?.detail || 'Failed to save changes.' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h1 style={styles.title}>Settings</h1>
        <p style={styles.subtitle}>Manage your profile and AI voice agent configuration</p>
      </div>

      {/* Tab Bar */}
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

      {/* Status Banner */}
      {status && (
        <div style={{ ...styles.banner, ...(status.type === 'success' ? styles.bannerSuccess : styles.bannerError) }}>
          {status.type === 'success'
            ? <CheckCircle size={15} color="var(--color-success, #16a34a)" />
            : <AlertCircle size={15} color="var(--color-error, #dc2626)" />
          }
          {status.msg}
        </div>
      )}

      {/* ── Profile Tab ─────────────────────────────────────────────── */}
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

      {/* ── Voice Settings Tab ───────────────────────────────────────── */}
      {activeTab === 'voice' && (
        <div style={styles.card}>

          <SectionTitle>Turn Detection</SectionTitle>
          <p style={styles.sectionDesc}>Controls how the AI decides you've finished speaking.</p>

          <Field label={`Silence Threshold — ${voiceForm.silence_threshold_ms} ms`}>
            <div style={styles.sliderRow}>
              <span style={styles.sliderLabel}>200 ms</span>
              <input
                type="range" min={200} max={3000} step={100}
                value={voiceForm.silence_threshold_ms}
                onChange={e => setVoice('silence_threshold_ms', Number(e.target.value))}
                style={styles.slider}
              />
              <span style={styles.sliderLabel}>3000 ms</span>
            </div>
            <p style={styles.hint}>How long the AI waits in silence before responding. Lower = faster but may cut you off.</p>
          </Field>

          <Field label={`Endpointing Delay — ${voiceForm.endpointing_ms} ms`}>
            <div style={styles.sliderRow}>
              <span style={styles.sliderLabel}>100 ms</span>
              <input
                type="range" min={100} max={800} step={50}
                value={voiceForm.endpointing_ms}
                onChange={e => setVoice('endpointing_ms', Number(e.target.value))}
                style={styles.slider}
              />
              <span style={styles.sliderLabel}>800 ms</span>
            </div>
            <p style={styles.hint}>Deepgram endpointing window. Lower = faster speech detection; higher = more accurate.</p>
          </Field>

          <Field label="VAD Sensitivity">
            <div style={styles.radioGroup}>
              {VAD_SENSITIVITY_OPTIONS.map(opt => (
                <label key={opt.value} style={{
                  ...styles.radioCard,
                  ...(voiceForm.vad_sensitivity === opt.value ? styles.radioCardActive : {})
                }}>
                  <input
                    type="radio" name="vad_sensitivity" value={opt.value}
                    checked={voiceForm.vad_sensitivity === opt.value}
                    onChange={() => setVoice('vad_sensitivity', opt.value)}
                    style={{ display: 'none' }}
                  />
                  <span style={styles.radioLabel}>{opt.label}</span>
                  <span style={styles.radioDesc}>{opt.desc}</span>
                </label>
              ))}
            </div>
          </Field>

          <SectionTitle style={{ marginTop: 28 }}>Speech & Language</SectionTitle>

          <Field label="STT Language">
            <select
              style={styles.input}
              value={voiceForm.language}
              onChange={e => setVoice('language', e.target.value)}
            >
              {LANGUAGES.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
          </Field>

          <SectionTitle style={{ marginTop: 28 }}>AI Behaviour</SectionTitle>

          <Field label="Greeting Message">
            <textarea
              style={{ ...styles.input, height: 80, resize: 'vertical' }}
              value={voiceForm.greeting_message}
              onChange={e => setVoice('greeting_message', e.target.value)}
              placeholder="e.g. Thank you for calling. How can I help you today?"
            />
            <p style={styles.hint}>What the AI says when a customer calls. Leave blank for default.</p>
          </Field>

          {/* ── Voice Picker ─────────────────────────────────────── */}
          <SectionTitle style={{ marginTop: 28 }}>AI Voice</SectionTitle>
          <p style={styles.sectionDesc}>Choose the voice your AI agent speaks with.</p>

          {/* Current selection badge */}
          {voiceForm.tts_voice_id && (
            <div style={styles.selectedBadge}>
              <Volume2 size={13} />
              <span>
                Selected: <strong>
                  {voiceForm.tts_voice_name || voiceForm.tts_voice_id}
                </strong>
              </span>
            </div>
          )}

          {!voicesLoaded && (
            <button
              style={{ ...styles.loadVoicesBtn, ...(voicesLoading ? styles.loadVoicesBtnDisabled : {}) }}
              onClick={loadVoices}
              disabled={voicesLoading}
            >
              {voicesLoading
                ? <><Loader size={13} style={{ animation: 'spin 1s linear infinite' }} /> Loading voices…</>
                : <><Mic size={13} /> Browse Available Voices</>
              }
            </button>
          )}

          {voicesLoaded && voices.length === 0 && (
            <p style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>
              No voices found. Check your ElevenLabs API key.
            </p>
          )}

          {voicesLoaded && voices.length > 0 && (
            <div style={styles.voiceGrid}>
              {voices.map(voice => {
                const isSelected = voiceForm.tts_voice_id === voice.voice_id
                const isPlaying  = playingId === voice.voice_id
                return (
                  <div
                    key={voice.voice_id}
                    style={{
                      ...styles.voiceCard,
                      ...(isSelected ? styles.voiceCardSelected : {}),
                    }}
                    onClick={() => {
                      setVoice('tts_voice_id', voice.voice_id)
                      setVoice('tts_voice_name', voice.name)
                    }}
                  >
                    <div style={styles.voiceCardTop}>
                      <div>
                        <div style={styles.voiceName}>{voice.name}</div>
                        <div style={styles.voiceCategory}>{voice.category}</div>
                        {voice.labels?.accent && (
                          <div style={styles.voiceAccent}>{voice.labels.accent}</div>
                        )}
                      </div>
                      {voice.preview_url && (
                        <button
                          style={{ ...styles.playBtn, ...(isPlaying ? styles.playBtnActive : {}) }}
                          onClick={e => { e.stopPropagation(); playPreview(voice) }}
                          title={isPlaying ? 'Stop preview' : 'Play preview'}
                        >
                          {isPlaying
                            ? <Volume2 size={13} />
                            : <Play size={13} />
                          }
                        </button>
                      )}
                    </div>
                    {isSelected && (
                      <div style={styles.voiceSelectedMark}>✓ Selected</div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Save Button */}
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
  label:   { fontSize: 13, fontWeight: 500, color: 'var(--color-text)' },
}

const styles = {
  page: {
    padding: '28px 32px',
    maxWidth: 760,
  },
  header: { marginBottom: 24 },
  title: { fontSize: 22, fontWeight: 700, color: 'var(--color-text)', margin: 0 },
  subtitle: { fontSize: 13, color: 'var(--color-text-muted)', marginTop: 4 },

  tabBar: {
    display: 'flex', gap: 4, marginBottom: 20,
    borderBottom: '1px solid var(--color-border)',
    paddingBottom: 0,
  },
  tab: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '8px 16px', fontSize: 13, fontWeight: 500,
    background: 'transparent', cursor: 'pointer',
    color: 'var(--color-text-muted)',
    borderBottom: '2px solid transparent',
    marginBottom: -1,
    transition: 'color 0.15s, border-color 0.15s',
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
  bannerSuccess: {
    background: '#f0fdf4', color: '#15803d',
    border: '1px solid #bbf7d0',
  },
  bannerError: {
    background: '#fef2f2', color: '#b91c1c',
    border: '1px solid #fecaca',
  },

  card: {
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius)',
    padding: '24px 28px',
  },

  row: {
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16,
  },

  input: {
    width: '100%', padding: '8px 11px',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)',
    fontSize: 13, color: 'var(--color-text)',
    background: 'var(--color-bg)',
    outline: 'none',
    boxSizing: 'border-box',
  },
  inputReadonly: {
    background: 'var(--color-surface)',
    color: 'var(--color-text-muted)',
    cursor: 'not-allowed',
  },

  sectionDesc: {
    fontSize: 12, color: 'var(--color-text-muted)', marginTop: -10, marginBottom: 16,
  },

  sliderRow: {
    display: 'flex', alignItems: 'center', gap: 10,
  },
  slider: {
    flex: 1, accentColor: 'var(--color-primary)', cursor: 'pointer',
  },
  sliderLabel: {
    fontSize: 11, color: 'var(--color-text-muted)', whiteSpace: 'nowrap',
  },
  hint: {
    fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4,
  },

  radioGroup: {
    display: 'flex', gap: 10, flexWrap: 'wrap',
  },
  radioCard: {
    flex: 1, minWidth: 160,
    display: 'flex', flexDirection: 'column', gap: 3,
    padding: '10px 14px',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    transition: 'border-color 0.15s, background 0.15s',
  },
  radioCardActive: {
    borderColor: 'var(--color-primary)',
    background: 'var(--color-primary-soft)',
  },
  radioLabel: {
    fontSize: 13, fontWeight: 600, color: 'var(--color-text)',
  },
  radioDesc: {
    fontSize: 11, color: 'var(--color-text-muted)',
  },

  footer: {
    marginTop: 20, display: 'flex', justifyContent: 'flex-end',
  },
  saveBtn: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '9px 20px', fontSize: 13, fontWeight: 600,
    background: 'var(--color-primary)', color: '#fff',
    borderRadius: 'var(--radius-sm)', cursor: 'pointer',
    transition: 'opacity 0.15s',
  },

  // Voice picker
  selectedBadge: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '7px 12px', marginBottom: 12,
    background: 'var(--color-primary-soft)',
    border: '1px solid var(--color-primary)',
    borderRadius: 'var(--radius-sm)',
    fontSize: 13, color: 'var(--color-primary)',
  },
  loadVoicesBtn: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '8px 16px', fontSize: 13, fontWeight: 500,
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)', cursor: 'pointer',
    color: 'var(--color-text)',
    marginBottom: 4,
    transition: 'border-color 0.15s',
  },
  loadVoicesBtnDisabled: {
    opacity: 0.6, cursor: 'not-allowed',
  },
  voiceGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: 10,
    marginTop: 8,
    maxHeight: 380,
    overflowY: 'auto',
    paddingRight: 4,
  },
  voiceCard: {
    padding: '10px 12px',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    transition: 'border-color 0.15s, background 0.15s',
    background: 'var(--color-bg)',
  },
  voiceCardSelected: {
    borderColor: 'var(--color-primary)',
    background: 'var(--color-primary-soft)',
  },
  voiceCardTop: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
  },
  voiceName: {
    fontSize: 13, fontWeight: 600, color: 'var(--color-text)', marginBottom: 2,
  },
  voiceCategory: {
    fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'capitalize',
  },
  voiceAccent: {
    fontSize: 11, color: 'var(--color-text-muted)', marginTop: 1,
    textTransform: 'capitalize',
  },
  playBtn: {
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    width: 26, height: 26, flexShrink: 0,
    border: '1px solid var(--color-border)',
    borderRadius: '50%', background: 'var(--color-surface)',
    cursor: 'pointer', color: 'var(--color-text-muted)',
    transition: 'background 0.15s, color 0.15s',
  },
  playBtnActive: {
    background: 'var(--color-primary)',
    borderColor: 'var(--color-primary)',
    color: '#fff',
  },
  voiceSelectedMark: {
    marginTop: 6,
    fontSize: 11, fontWeight: 600,
    color: 'var(--color-primary)',
  },
}
