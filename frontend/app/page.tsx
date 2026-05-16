'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { Wifi, WifiOff, AlertTriangle, Bell, BellOff, Send, X } from 'lucide-react'
import dynamic from 'next/dynamic'

const Sparkline = dynamic(() => import('./components/Sparkline'), { ssr: false })

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_URL  = process.env.NEXT_PUBLIC_WS_URL  || 'ws://localhost:8000'
const BUFFER_SIZE = 120

const COLORS = [
  '#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6',
  '#06b6d4','#f97316','#84cc16','#ec4899','#14b8a6',
]

interface TagData   { value: number|boolean|string; unit: string; ts: number; quality: string; protocol: string }
interface DevStatus { online: boolean; protocol: string; error: string|null }
interface TagEntry  { tag_id: string; data: TagData }
interface DevGroup  { device_id: string; status: DevStatus|null; tags: TagEntry[] }
interface Threshold { min?: number; max?: number }
interface AlarmEdit { device_id: string; tag_id: string; min: string; max: string }

function isAlarming(value: number|boolean|string, thr?: Threshold) {
  if (!thr || typeof value !== 'number') return false
  if (thr.max !== undefined && value > thr.max) return true
  if (thr.min !== undefined && value < thr.min) return true
  return false
}

export default function Dashboard() {
  const [devices,    setDevices]    = useState<Record<string, DevGroup>>({})
  const [wsStatus,   setWsStatus]   = useState<'connecting'|'connected'|'disconnected'>('connecting')
  const [thresholds, setThresholds] = useState<Record<string, Threshold>>({})
  const [alarmEdit,  setAlarmEdit]  = useState<AlarmEdit|null>(null)
  const [writeInputs, setWriteInputs] = useState<Record<string, string>>({})
  const [writeStatus, setWriteStatus] = useState<Record<string, string>>({})

  // buffer de histórico en tiempo real por tag
  const buffers = useRef<Record<string, {ts:number; value:number}[]>>({})
  const [tick, setTick] = useState(0)   // fuerza re-render cuando cambia el buffer

  // ── carga inicial ────────────────────────────────────────────────────────
  const loadAlarms = useCallback(async () => {
    const res = await fetch(`${API_URL}/api/alarms`)
    if (res.ok) setThresholds(await res.json())
  }, [])

  const loadTags = useCallback(async () => {
    const res = await fetch(`${API_URL}/api/tags`)
    if (!res.ok) return
    const tags = await res.json()
    setDevices(prev => {
      const next = { ...prev }
      for (const t of tags) {
        if (!next[t.device_id]) next[t.device_id] = { device_id: t.device_id, status: null, tags: [] }
        const entry: TagEntry = { tag_id: t.tag_id, data: { value: t.value, unit: t.unit, ts: t.ts, quality: t.quality, protocol: t.protocol } }
        const idx = next[t.device_id].tags.findIndex(x => x.tag_id === t.tag_id)
        if (idx >= 0) next[t.device_id].tags[idx] = entry
        else next[t.device_id].tags.push(entry)
        // poblar buffer con dato inicial
        if (typeof t.value === 'number') {
          const key = `${t.device_id}/${t.tag_id}`
          if (!buffers.current[key]) buffers.current[key] = []
          buffers.current[key].push({ ts: t.ts, value: t.value })
        }
      }
      return next
    })
  }, [])

  useEffect(() => {
    loadTags()
    loadAlarms()

    const connect = () => {
      const ws = new WebSocket(`${WS_URL}/ws/tags`)
      ws.onopen  = () => setWsStatus('connected')
      ws.onclose = () => { setWsStatus('disconnected'); setTimeout(connect, 3000) }
      ws.onerror = () => setWsStatus('disconnected')
      ws.onmessage = ev => {
        const msg = JSON.parse(ev.data)
        const did = msg.device_id

        setDevices(prev => {
          const next = { ...prev }
          if (!next[did]) next[did] = { device_id: did, status: null, tags: [] }

          if (msg.type === 'status') {
            next[did] = { ...next[did], status: msg.data }
          } else if (msg.type === 'tag') {
            const tags = [...next[did].tags]
            const idx  = tags.findIndex(t => t.tag_id === msg.tag_id)
            const entry: TagEntry = { tag_id: msg.tag_id, data: msg.data }
            if (idx >= 0) tags[idx] = entry; else tags.push(entry)
            next[did] = { ...next[did], tags }

            // actualizar buffer
            if (typeof msg.data.value === 'number') {
              const key = `${did}/${msg.tag_id}`
              if (!buffers.current[key]) buffers.current[key] = []
              buffers.current[key].push({ ts: msg.data.ts, value: msg.data.value })
              if (buffers.current[key].length > BUFFER_SIZE)
                buffers.current[key] = buffers.current[key].slice(-BUFFER_SIZE)
            }
          }
          return next
        })
        setTick(t => t + 1)
      }
      return ws
    }

    const ws = connect()
    return () => ws.close()
  }, [loadTags, loadAlarms])

  // ── escritura setpoint ───────────────────────────────────────────────────
  const sendWrite = async (device_id: string, tag_id: string) => {
    const key   = `${device_id}/${tag_id}`
    const value = parseFloat(writeInputs[key] ?? '')
    if (isNaN(value)) return
    const res = await fetch(`${API_URL}/api/tags/${device_id}/${tag_id}/write`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value }),
    })
    setWriteStatus(prev => ({ ...prev, [key]: res.ok ? '✓' : '✗' }))
    setTimeout(() => setWriteStatus(prev => { const n={...prev}; delete n[key]; return n }), 2000)
  }

  // ── guardar umbral ───────────────────────────────────────────────────────
  const saveAlarm = async () => {
    if (!alarmEdit) return
    const { device_id, tag_id, min, max } = alarmEdit
    const body: any = { device_id, tag_id }
    if (min !== '') body.min = parseFloat(min)
    if (max !== '') body.max = parseFloat(max)

    if (min === '' && max === '') {
      await fetch(`${API_URL}/api/alarms/${device_id}/${tag_id}`, { method: 'DELETE' })
    } else {
      await fetch(`${API_URL}/api/alarms`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
    }
    await loadAlarms()
    setAlarmEdit(null)
  }

  const fmtValue = (v: number|boolean|string, unit: string) => {
    if (typeof v === 'boolean') return v ? 'ON' : 'OFF'
    if (typeof v === 'number')  return `${v.toFixed(2)} ${unit}`
    return `${v} ${unit}`
  }

  const devList = Object.values(devices)
  const totalAlarms = devList.reduce((acc, dev) =>
    acc + dev.tags.filter(t => isAlarming(t.data.value, thresholds[`${dev.device_id}/${t.tag_id}`])).length, 0)

  return (
    <div>
      {/* ── cabecera ── */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold">Dashboard</h1>
          {totalAlarms > 0 && (
            <span className="flex items-center gap-1.5 px-3 py-1 bg-red-900/60 border border-red-700 rounded-full text-red-400 text-sm animate-pulse">
              <AlertTriangle size={14}/> {totalAlarms} alarma{totalAlarms > 1 ? 's' : ''} activa{totalAlarms > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-sm">
          {wsStatus === 'connected'
            ? <><Wifi size={16} className="text-green-400"/><span className="text-green-400">En vivo</span></>
            : <><WifiOff size={16} className="text-red-400"/><span className="text-red-400">{wsStatus}</span></>
          }
        </div>
      </div>

      {/* ── sin dispositivos ── */}
      {devList.length === 0 && (
        <div className="text-center text-gray-500 mt-20">
          <Wifi size={48} className="mx-auto mb-4 opacity-20"/>
          <p>Esperando datos de dispositivos...</p>
        </div>
      )}

      {/* ── dispositivos ── */}
      <div className="space-y-8">
        {devList.map(({ device_id, status, tags }) => (
          <div key={device_id} className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">

            {/* cabecera dispositivo */}
            <div className="flex items-center gap-3 px-5 py-3 border-b border-gray-800 bg-gray-900/80">
              <div className={`w-2.5 h-2.5 rounded-full ${status?.online ? 'bg-green-400' : 'bg-red-500'}`}/>
              <span className="font-semibold">{device_id}</span>
              <span className="text-xs text-gray-500">{status?.protocol ?? '—'}</span>
              {status?.error && (
                <span className="text-xs text-red-400 ml-2">{status.error}</span>
              )}
              <span className={`ml-auto text-xs px-2 py-0.5 rounded font-medium
                ${status?.online ? 'bg-green-900 text-green-400' : 'bg-gray-800 text-gray-500'}`}>
                {status?.online ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>

            {/* grid de tags */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-px bg-gray-800">
              {tags.map(({ tag_id, data }, idx) => {
                const key       = `${device_id}/${tag_id}`
                const thr       = thresholds[key]
                const alarming  = isAlarming(data.value, thr)
                const color     = COLORS[idx % COLORS.length]
                const buf       = buffers.current[key] ?? []
                const isNum     = typeof data.value === 'number'

                return (
                  <div key={tag_id}
                    className={`bg-gray-900 p-4 flex flex-col gap-2
                      ${alarming ? 'ring-1 ring-red-500/50' : ''}`}>

                    {/* fila superior: nombre + alarma */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }}/>
                        <span className="text-xs text-gray-400 truncate">{tag_id}</span>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        {alarming && (
                          <span className="flex items-center gap-1 text-xs text-red-400 animate-pulse">
                            <AlertTriangle size={12}/> ALARMA
                          </span>
                        )}
                        <button
                          onClick={() => setAlarmEdit({
                            device_id, tag_id,
                            min: thr?.min?.toString() ?? '',
                            max: thr?.max?.toString() ?? '',
                          })}
                          title="Configurar umbral"
                          className={`p-1 rounded transition-colors
                            ${thr ? 'text-orange-400 hover:text-orange-300' : 'text-gray-600 hover:text-gray-400'}`}>
                          {thr ? <Bell size={13}/> : <BellOff size={13}/>}
                        </button>
                      </div>
                    </div>

                    {/* valor grande */}
                    <div className={`font-mono text-2xl font-bold tracking-tight
                      ${alarming ? 'text-red-400' : 'text-white'}`}>
                      {fmtValue(data.value, data.unit)}
                    </div>

                    {/* umbrales activos */}
                    {thr && (
                      <div className="flex gap-3 text-xs">
                        {thr.min !== undefined && (
                          <span className="text-amber-500">▼ mín {thr.min} {data.unit}</span>
                        )}
                        {thr.max !== undefined && (
                          <span className="text-red-500">▲ máx {thr.max} {data.unit}</span>
                        )}
                      </div>
                    )}

                    {/* sparkline en tiempo real */}
                    {isNum && (
                      <div className="mt-1">
                        <Sparkline
                          points={buf}
                          color={alarming ? '#ef4444' : color}
                          threshold={thr}
                          unit={data.unit}
                        />
                      </div>
                    )}

                    {/* setpoint */}
                    <div className="flex items-center gap-1 mt-1">
                      <input
                        type="number"
                        placeholder="setpoint"
                        value={writeInputs[key] ?? ''}
                        onChange={e => setWriteInputs(p => ({ ...p, [key]: e.target.value }))}
                        className="flex-1 px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded
                          text-gray-200 focus:outline-none focus:border-blue-500"
                      />
                      <button onClick={() => sendWrite(device_id, tag_id)}
                        className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-xs transition-colors flex items-center gap-1">
                        <Send size={11}/> Enviar
                      </button>
                      {writeStatus[key] && (
                        <span className={`text-xs ${writeStatus[key]==='✓'?'text-green-400':'text-red-400'}`}>
                          {writeStatus[key]}
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* ── modal umbral ── */}
      {alarmEdit && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
          onClick={e => { if (e.target === e.currentTarget) setAlarmEdit(null) }}>
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-sm shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">Umbral de alarma</h3>
              <button onClick={() => setAlarmEdit(null)}
                className="text-gray-500 hover:text-gray-300">
                <X size={18}/>
              </button>
            </div>

            <div className="text-xs text-gray-400 mb-4 font-mono">
              {alarmEdit.device_id} / {alarmEdit.tag_id}
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs text-amber-400 mb-1">▼ Mínimo (alarma si valor &lt; min)</label>
                <input
                  type="number" step="any"
                  value={alarmEdit.min}
                  onChange={e => setAlarmEdit(p => p ? { ...p, min: e.target.value } : p)}
                  placeholder="Sin límite inferior"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm
                    focus:outline-none focus:border-amber-500"
                />
              </div>
              <div>
                <label className="block text-xs text-red-400 mb-1">▲ Máximo (alarma si valor &gt; max)</label>
                <input
                  type="number" step="any"
                  value={alarmEdit.max}
                  onChange={e => setAlarmEdit(p => p ? { ...p, max: e.target.value } : p)}
                  placeholder="Sin límite superior"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm
                    focus:outline-none focus:border-red-500"
                />
              </div>
            </div>

            <div className="flex gap-2 mt-5">
              <button onClick={saveAlarm}
                className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 rounded font-medium text-sm transition-colors">
                Guardar
              </button>
              <button
                onClick={async () => {
                  await fetch(`${API_URL}/api/alarms/${alarmEdit.device_id}/${alarmEdit.tag_id}`, { method: 'DELETE' })
                  await loadAlarms()
                  setAlarmEdit(null)
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors text-gray-300">
                Quitar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
