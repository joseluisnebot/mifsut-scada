'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  Tooltip, CartesianGrid, ReferenceLine,
} from 'recharts'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Point { ts: number; value: number }

const QUICK_RANGES = [
  { label: '15 min', minutes: 15 },
  { label: '1 h',   minutes: 60 },
  { label: '6 h',   minutes: 360 },
  { label: '24 h',  minutes: 1440 },
  { label: '7 d',   minutes: 10080 },
]

function toLocalInput(date: Date) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function fmt(ts: number, rangeMin: number) {
  const d = new Date(ts)
  if (rangeMin <= 360) return d.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  if (rangeMin <= 1440) return d.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString('es', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function TagChart({
  device_id, tag_id, unit, color = '#3b82f6',
}: {
  device_id: string
  tag_id: string
  unit: string
  color?: string
}) {
  const now = new Date()
  const [points,     setPoints]     = useState<Point[]>([])
  const [minutes,    setMinutes]    = useState(60)
  const [useCustom,  setUseCustom]  = useState(false)
  const [customFrom, setCustomFrom] = useState(toLocalInput(new Date(now.getTime() - 86400_000)))
  const [customTo,   setCustomTo]   = useState(toLocalInput(now))
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      let url: string
      if (useCustom) {
        const start = new Date(customFrom).toISOString()
        const end   = new Date(customTo).toISOString()
        url = `${API_URL}/api/tags/${device_id}/${tag_id}/history?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`
      } else {
        url = `${API_URL}/api/tags/${device_id}/${tag_id}/history?minutes=${minutes}`
      }
      const res = await fetch(url)
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setPoints(data.points)
    } catch {
      setError('Sin datos históricos aún')
    } finally {
      setLoading(false)
    }
  }, [device_id, tag_id, minutes, useCustom, customFrom, customTo])

  useEffect(() => { load() }, [load])

  // refresco automático cada 10s si no hay rango personalizado
  useEffect(() => {
    if (useCustom) return
    const t = setInterval(load, 10000)
    return () => clearInterval(t)
  }, [load, useCustom])

  const effectiveRange = useCustom
    ? (new Date(customTo).getTime() - new Date(customFrom).getTime()) / 60000
    : minutes

  const values = points.map(p => p.value)
  const min = values.length ? Math.min(...values) : 0
  const max = values.length ? Math.max(...values) : 0
  const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0

  return (
    <div className="pt-2">
      {/* selector de rango rápido */}
      <div className="flex items-center gap-1 mb-2 flex-wrap">
        {QUICK_RANGES.map(r => (
          <button
            key={r.minutes}
            onClick={() => { setMinutes(r.minutes); setUseCustom(false) }}
            className={`px-2 py-0.5 text-xs rounded transition-colors ${
              !useCustom && minutes === r.minutes
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            {r.label}
          </button>
        ))}
        <button
          onClick={() => setUseCustom(v => !v)}
          className={`px-2 py-0.5 text-xs rounded transition-colors ${
            useCustom ? 'bg-purple-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          Personalizado
        </button>
        <button onClick={load}
          className="ml-auto px-2 py-0.5 text-xs bg-gray-800 text-gray-400 hover:bg-gray-700 rounded transition-colors">
          ↻
        </button>
      </div>

      {/* selector de fechas personalizado */}
      {useCustom && (
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500">De</span>
            <input
              type="datetime-local"
              value={customFrom}
              onChange={e => setCustomFrom(e.target.value)}
              className="px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded text-gray-200
                focus:outline-none focus:border-purple-500"
            />
          </div>
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500">a</span>
            <input
              type="datetime-local"
              value={customTo}
              onChange={e => setCustomTo(e.target.value)}
              className="px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded text-gray-200
                focus:outline-none focus:border-purple-500"
            />
          </div>
          <button onClick={load}
            className="px-3 py-1 text-xs bg-purple-600 hover:bg-purple-500 rounded text-white transition-colors">
            Consultar
          </button>
        </div>
      )}

      {/* stats rápidas */}
      {points.length > 0 && (
        <div className="flex gap-4 mb-3 text-xs text-gray-500">
          <span>Min: <span className="text-gray-300">{min.toFixed(2)} {unit}</span></span>
          <span>Max: <span className="text-gray-300">{max.toFixed(2)} {unit}</span></span>
          <span>Avg: <span className="text-gray-300">{avg.toFixed(2)} {unit}</span></span>
          <span className="ml-auto">{points.length} muestras</span>
        </div>
      )}

      {loading && <div className="h-40 flex items-center justify-center text-gray-500 text-sm">Cargando...</div>}
      {error && !loading && <div className="h-40 flex items-center justify-center text-gray-600 text-sm">{error}</div>}

      {!loading && !error && points.length > 0 && (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={points} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis
              dataKey="ts"
              tickFormatter={ts => fmt(Number(ts), effectiveRange)}
              tick={{ fontSize: 10, fill: '#6b7280' }}
              tickCount={6}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 10, fill: '#6b7280' }}
              width={52}
              tickFormatter={v => `${Number(v).toFixed(1)}`}
              domain={['auto', 'auto']}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 6, fontSize: 12 }}
              labelFormatter={ts => new Date(Number(ts)).toLocaleString('es')}
              formatter={(v: any) => [`${Number(v).toFixed(3)} ${unit}`, tag_id]}
            />
            <ReferenceLine y={avg} stroke="#374151" strokeDasharray="4 2" />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}

      {!loading && !error && points.length === 0 && (
        <div className="h-40 flex items-center justify-center text-gray-600 text-sm">
          Sin datos en este rango
        </div>
      )}
    </div>
  )
}
