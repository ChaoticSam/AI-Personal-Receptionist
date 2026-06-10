import { useState, useRef, useCallback, useEffect } from 'react'
import { Mic, MicOff, Radio } from 'lucide-react'

const PROVIDERS = [
  { id: 'openai',     label: 'OpenAI TTS',  sub: 'tts-1 · alloy' },
  { id: 'elevenlabs', label: 'ElevenLabs',  sub: 'Multilingual v2' },
]

const STATUS_CONFIG = {
  idle:        { color: 'var(--color-text-muted)', label: 'Ready' },
  connecting:  { color: 'var(--color-warning)',    label: 'Connecting…' },
  listening:   { color: 'var(--color-danger)',     label: 'Listening' },
  error:       { color: 'var(--color-danger)',     label: 'Error' },
  disconnected:{ color: 'var(--color-text-muted)', label: 'Disconnected' },
}

export default function VoiceTest() {
  const [provider, setProvider]       = useState('openai')
  const [status, setStatus]           = useState('idle')
  const [transcript, setTranscript]   = useState('')
  const [partialTx, setPartialTx]     = useState('')
  const [agentText, setAgentText]     = useState('')
  const [events, setEvents]           = useState([])

  const wsRef           = useRef(null)
  const audioCtxInRef   = useRef(null)
  const audioCtxOutRef  = useRef(null)
  const processorRef    = useRef(null)
  const mediaStreamRef  = useRef(null)
  const nextPlayRef     = useRef(0)
  const sessionStartRef = useRef(0)
  const agentBufRef     = useRef('')

  const isActive = status === 'listening' || status === 'connecting'

  // ── Event log ─────────────────────────────────────────────────────────────
  const logEvent = useCallback((type, body = '') => {
    const elapsed = ((Date.now() - sessionStartRef.current) / 1000).toFixed(1)
    setEvents(prev => [...prev.slice(-99), { type, body: String(body).slice(0, 120), elapsed }])
  }, [])

  // ── Audio playback (PCM s16le 24 kHz) ────────────────────────────────────
  function ensurePlaybackCtx() {
    if (!audioCtxOutRef.current || audioCtxOutRef.current.state === 'closed') {
      audioCtxOutRef.current = new AudioContext({ sampleRate: 24000 })
      nextPlayRef.current = 0
    }
    if (audioCtxOutRef.current.state === 'suspended') audioCtxOutRef.current.resume()
  }

  function playPCM(base64) {
    ensurePlaybackCtx()
    try {
      const binary = atob(base64)
      const bytes  = new Uint8Array(binary.length)
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
      const int16   = new Int16Array(bytes.buffer)
      const float32 = new Float32Array(int16.length)
      for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768
      const buf = audioCtxOutRef.current.createBuffer(1, float32.length, 24000)
      buf.getChannelData(0).set(float32)
      const src = audioCtxOutRef.current.createBufferSource()
      src.buffer = buf
      src.connect(audioCtxOutRef.current.destination)
      const startAt = Math.max(audioCtxOutRef.current.currentTime, nextPlayRef.current)
      src.start(startAt)
      nextPlayRef.current = startAt + buf.duration
    } catch (e) {
      console.error('[playback]', e)
    }
  }

  // ── Pipeline event handler ────────────────────────────────────────────────
  function handleEvent(event) {
    switch (event.type) {
      case 'stt_chunk':
        setPartialTx(event.transcript)
        logEvent('stt_chunk', event.transcript)
        break
      case 'stt_output':
        setTranscript(event.transcript)
        setPartialTx('')
        setAgentText('')
        agentBufRef.current = ''
        logEvent('stt_output', event.transcript)
        break
      case 'agent_chunk':
        agentBufRef.current += event.text
        setAgentText(agentBufRef.current)
        logEvent('agent_chunk', event.text)
        break
      case 'agent_end':
        logEvent('agent_end', '')
        break
      case 'tts_chunk':
        playPCM(event.audio)
        logEvent('tts_chunk', `${event.audio.length} chars`)
        break
    }
  }

  // ── Start session ─────────────────────────────────────────────────────────
  async function start() {
    setStatus('connecting')
    setEvents([])
    setTranscript('')
    setPartialTx('')
    setAgentText('')
    agentBufRef.current = ''
    sessionStartRef.current = Date.now()

    const proto      = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const backendHost = import.meta.env.VITE_BACKEND_URL || 'localhost:8000'
    const ws         = new WebSocket(`${proto}//${backendHost}/voice-pipeline/ws?tts=${provider}`)
    wsRef.current = ws

    ws.onopen = async () => {
      setStatus('listening')
      logEvent('ws_open', `provider=${provider}`)

      try {
        mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true })
        audioCtxInRef.current  = new AudioContext({ sampleRate: 16000 })
        const source    = audioCtxInRef.current.createMediaStreamSource(mediaStreamRef.current)
        const processor = audioCtxInRef.current.createScriptProcessor(4096, 1, 1)
        processorRef.current = processor

        processor.onaudioprocess = (e) => {
          if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
          const f32  = e.inputBuffer.getChannelData(0)
          const i16  = new Int16Array(f32.length)
          for (let i = 0; i < f32.length; i++) {
            const s = Math.max(-1, Math.min(1, f32[i]))
            i16[i]  = s < 0 ? s * 0x8000 : s * 0x7fff
          }
          ws.send(i16.buffer)
        }

        source.connect(processor)
        processor.connect(audioCtxInRef.current.destination)
      } catch (err) {
        logEvent('error', err.message)
        setStatus('error')
        stop()
      }
    }

    ws.onmessage = (e) => {
      try { handleEvent(JSON.parse(e.data)) } catch { /* ignore */ }
    }

    ws.onclose  = () => { setStatus('disconnected'); logEvent('ws_close', '') }
    ws.onerror  = () => { setStatus('error');        logEvent('ws_error', '') }
  }

  // ── Stop session ──────────────────────────────────────────────────────────
  function stop() {
    if (processorRef.current)    { processorRef.current.disconnect(); processorRef.current = null }
    if (audioCtxInRef.current)   { audioCtxInRef.current.close(); audioCtxInRef.current = null }
    if (mediaStreamRef.current)  { mediaStreamRef.current.getTracks().forEach(t => t.stop()); mediaStreamRef.current = null }
    if (wsRef.current)           { wsRef.current.close(); wsRef.current = null }
    setStatus('idle')
  }

  // Clean up on unmount
  useEffect(() => () => stop(), [])

  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.idle

  return (
    <div style={s.page}>
      {/* Header */}
      <div style={s.header}>
        <div style={s.headerLeft}>
          <Radio size={18} color="var(--color-primary)" />
          <span style={s.title}>Voice Pipeline Test</span>
        </div>
        <div style={s.statusPill}>
          <span style={{ ...s.dot, background: cfg.color, boxShadow: status === 'listening' ? `0 0 8px ${cfg.color}` : 'none' }} />
          <span style={{ color: cfg.color, fontSize: 12, fontWeight: 500 }}>{cfg.label}</span>
        </div>
      </div>

      {/* Provider selector */}
      <div style={s.card}>
        <div style={s.cardLabel}>TTS Provider</div>
        <div style={s.providerRow}>
          {PROVIDERS.map(p => (
            <button
              key={p.id}
              disabled={isActive}
              onClick={() => setProvider(p.id)}
              style={{
                ...s.providerBtn,
                ...(provider === p.id ? s.providerBtnActive : {}),
                opacity: isActive ? 0.5 : 1,
                cursor: isActive ? 'not-allowed' : 'pointer',
              }}
            >
              <span style={s.providerLabel}>{p.label}</span>
              <span style={s.providerSub}>{p.sub}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Controls */}
      <div style={s.card}>
        <div style={s.controls}>
          <button
            onClick={start}
            disabled={isActive}
            style={{ ...s.btn, ...s.btnPrimary, opacity: isActive ? 0.4 : 1 }}
          >
            <Mic size={15} />
            Start Session
          </button>
          <button
            onClick={stop}
            disabled={!isActive}
            style={{ ...s.btn, ...s.btnSecondary, opacity: !isActive ? 0.4 : 1 }}
          >
            <MicOff size={15} />
            End Session
          </button>
        </div>
        {isActive && (
          <div style={s.hint}>
            🎙️ Session active — speak naturally. End session when done.
          </div>
        )}
      </div>

      {/* Transcript + Agent */}
      <div style={s.panels}>
        <div style={s.panel}>
          <div style={s.panelLabel}>You said</div>
          <div style={s.panelBody}>
            {partialTx
              ? <span style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>{partialTx} …</span>
              : transcript || <span style={{ color: 'var(--color-text-muted)' }}>—</span>}
          </div>
        </div>
        <div style={s.panel}>
          <div style={s.panelLabel}>Clara (AI)</div>
          <div style={s.panelBody}>
            {agentText || <span style={{ color: 'var(--color-text-muted)' }}>—</span>}
          </div>
        </div>
      </div>

      {/* Event log */}
      <div style={s.card}>
        <div style={s.logHeader}>
          <span style={s.cardLabel}>Event log</span>
          <button onClick={() => setEvents([])} style={s.clearBtn}>Clear</button>
        </div>
        <div style={s.logScroll}>
          {events.length === 0
            ? <div style={s.logEmpty}>Events will appear here…</div>
            : events.map((ev, i) => (
                <div key={i} style={s.logRow}>
                  <span style={s.logTs}>{ev.elapsed}s</span>
                  <span style={{ ...s.logType, color: EVENT_COLORS[ev.type] || 'var(--color-text-muted)' }}>{ev.type}</span>
                  <span style={s.logBody}>{ev.body}</span>
                </div>
              ))}
        </div>
      </div>
    </div>
  )
}

const EVENT_COLORS = {
  stt_chunk:   '#6366f1',
  stt_output:  '#818cf8',
  agent_chunk: '#22d3ee',
  agent_end:   '#0ea5e9',
  tts_chunk:   '#22c55e',
  ws_open:     '#f59e0b',
  ws_close:    '#8b8fa8',
  ws_error:    '#ef4444',
  error:       '#ef4444',
}

const s = {
  page: {
    padding: '28px 32px',
    maxWidth: 860,
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  headerLeft: {
    display: 'flex', alignItems: 'center', gap: 10,
  },
  title: {
    fontSize: 18, fontWeight: 700, letterSpacing: '-0.3px',
    color: 'var(--color-text)',
  },
  statusPill: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '5px 12px',
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 999,
  },
  dot: {
    width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
    transition: 'background 0.3s, box-shadow 0.3s',
  },
  card: {
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius)',
    padding: '18px 20px',
  },
  cardLabel: {
    fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
    letterSpacing: '0.08em', color: 'var(--color-text-muted)',
    marginBottom: 12,
  },
  providerRow: { display: 'flex', gap: 8 },
  providerBtn: {
    flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'flex-start',
    gap: 2, padding: '10px 14px', borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--color-border)',
    background: 'var(--color-surface-2)',
    transition: 'all 0.15s',
  },
  providerBtnActive: {
    border: '1px solid var(--color-primary)',
    background: 'var(--color-primary-soft)',
  },
  providerLabel: { fontSize: 13, fontWeight: 600, color: 'var(--color-text)' },
  providerSub:   { fontSize: 10, fontFamily: 'monospace', color: 'var(--color-text-muted)' },
  controls: { display: 'flex', gap: 10 },
  btn: {
    display: 'flex', alignItems: 'center', gap: 7,
    padding: '10px 18px', borderRadius: 'var(--radius-sm)',
    fontSize: 13, fontWeight: 600, transition: 'all 0.15s',
  },
  btnPrimary: {
    background: 'var(--color-primary)', color: '#fff',
  },
  btnSecondary: {
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border)',
    color: 'var(--color-text-muted)',
  },
  hint: {
    marginTop: 12, padding: '8px 12px',
    background: 'var(--color-primary-soft)',
    border: '1px solid rgba(99,102,241,0.25)',
    borderRadius: 'var(--radius-sm)',
    fontSize: 12, color: 'var(--color-text-muted)',
  },
  panels: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
  panel: {
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius)',
    padding: '16px 18px', minHeight: 100,
  },
  panelLabel: {
    fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
    letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 8,
  },
  panelBody: { fontSize: 14, lineHeight: 1.6, color: 'var(--color-text)', wordBreak: 'break-word' },
  logHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  clearBtn: {
    fontSize: 11, color: 'var(--color-text-muted)',
    background: 'none', padding: '2px 6px', borderRadius: 4,
  },
  logScroll: { height: 200, overflowY: 'auto' },
  logEmpty: { fontSize: 12, color: 'var(--color-text-muted)', padding: '8px 0' },
  logRow: {
    display: 'flex', gap: 12, padding: '3px 0',
    borderBottom: '1px solid var(--color-border)',
    fontSize: 11, fontFamily: 'monospace',
  },
  logTs:   { color: 'var(--color-text-muted)', flexShrink: 0, width: '5ch' },
  logType: { flexShrink: 0, width: '13ch', fontWeight: 600 },
  logBody: { color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
}
