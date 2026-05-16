'use client'

import {
  ResponsiveContainer, LineChart, Line,
  ReferenceLine, Tooltip, YAxis,
} from 'recharts'

interface Point { ts: number; value: number }
interface Threshold { min?: number; max?: number }

const CustomTooltip = ({ active, payload, unit }: any) => {
  if (!active || !payload?.length) return null
  const v = payload[0]?.value
  const t = payload[0]?.payload?.ts
  return (
    <div className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs">
      <div className="text-gray-400">{t ? new Date(t).toLocaleTimeString('es') : ''}</div>
      <div className="text-white font-mono">{typeof v === 'number' ? v.toFixed(2) : v} {unit}</div>
    </div>
  )
}

export default function Sparkline({
  points, color, threshold, unit,
}: {
  points: Point[]
  color: string
  threshold?: Threshold
  unit: string
}) {
  if (!points.length) {
    return <div className="h-16 flex items-center justify-center text-gray-700 text-xs">Sin datos</div>
  }

  const values = points.map(p => p.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const pad = (max - min) * 0.2 || 1
  const domain: [number, number] = [min - pad, max + pad]

  return (
    <ResponsiveContainer width="100%" height={64}>
      <LineChart data={points} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
        <YAxis domain={domain} hide />
        <Tooltip content={<CustomTooltip unit={unit} />} />
        {threshold?.max !== undefined && (
          <ReferenceLine y={threshold.max} stroke="#ef4444" strokeDasharray="3 2" strokeWidth={1} />
        )}
        {threshold?.min !== undefined && (
          <ReferenceLine y={threshold.min} stroke="#f59e0b" strokeDasharray="3 2" strokeWidth={1} />
        )}
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
