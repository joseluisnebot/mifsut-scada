'use client'

import { useEffect, useState } from 'react'
import { PlusCircle, Server, CheckCircle, XCircle, Trash2 } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Device {
  device_id: string
  online: boolean
  protocol: string
  error: string | null
}

interface Template {
  name: string
  manufacturer?: string
  model?: string
  tags?: any[]
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([])
  const [templates, setTemplates] = useState<Record<string, string[]>>({})
  const [form, setForm] = useState({
    device_id: '',
    protocol: '',
    template: '',
    host: '',
    port: '',
    poll_interval_ms: '1000',
  })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  const load = async () => {
    try {
      const [devRes, tplRes] = await Promise.all([
        fetch(`${API_URL}/api/devices`),
        fetch(`${API_URL}/api/templates`),
      ])
      setDevices(await devRes.json())
      setTemplates(await tplRes.json())
    } catch (e) {
      console.error(e)
    }
  }

  const deleteDevice = async (device_id: string) => {
    if (!confirm(`¿Borrar dispositivo "${device_id}"?`)) return
    await fetch(`${API_URL}/api/devices/${device_id}`, { method: 'DELETE' })
    load()
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  const protocols = Object.keys(templates)
  const templateList = form.protocol ? (templates[form.protocol] ?? []) : []

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const connection: Record<string, any> = { host: form.host }
      if (form.port) connection.port = parseInt(form.port)

      const res = await fetch(`${API_URL}/api/devices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: form.device_id,
          protocol: form.protocol,
          template: `${form.template}`,
          connection,
          poll_interval_ms: parseInt(form.poll_interval_ms),
        }),
      })
      if (res.ok) {
        setMsg('Dispositivo guardado. El driver lo detectará en el próximo reinicio.')
        setForm({ device_id: '', protocol: '', template: '', host: '', port: '', poll_interval_ms: '1000' })
        load()
      } else {
        setMsg('Error al guardar')
      }
    } catch {
      setMsg('Error de red')
    } finally {
      setSaving(false)
      setTimeout(() => setMsg(''), 5000)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Dispositivos</h1>

      <div className="grid gap-3 mb-10">
        {devices.length === 0 && (
          <p className="text-gray-500 text-sm">No hay dispositivos registrados aún.</p>
        )}
        {devices.map(d => (
          <div key={d.device_id} className="bg-gray-900 rounded-lg border border-gray-800 px-4 py-3 flex items-center gap-4">
            <Server size={20} className="text-gray-400" />
            <div className="flex-1">
              <div className="font-medium text-sm">{d.device_id}</div>
              <div className="text-xs text-gray-500">{d.protocol}</div>
            </div>
            {d.online
              ? <CheckCircle size={18} className="text-green-400" />
              : <XCircle size={18} className="text-red-400" />
            }
            <span className={`text-xs px-2 py-0.5 rounded ${d.online ? 'bg-green-900 text-green-400' : 'bg-red-900 text-red-400'}`}>
              {d.online ? 'ONLINE' : 'OFFLINE'}
            </span>
            <button onClick={() => deleteDevice(d.device_id)}
              className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors ml-1">
              <Trash2 size={15} />
            </button>
          </div>
        ))}
      </div>

      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <PlusCircle size={20} className="text-blue-400" /> Añadir dispositivo
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">ID del dispositivo</label>
              <input
                required
                value={form.device_id}
                onChange={e => setForm(p => ({ ...p, device_id: e.target.value }))}
                placeholder="variador-linea1"
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Protocolo</label>
              <select
                required
                value={form.protocol}
                onChange={e => setForm(p => ({ ...p, protocol: e.target.value, template: '' }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="">Seleccionar...</option>
                {protocols.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">Template</label>
            <select
              required
              value={form.template}
              onChange={e => setForm(p => ({ ...p, template: e.target.value }))}
              disabled={!form.protocol}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500 disabled:opacity-50"
            >
              <option value="">Seleccionar template...</option>
              {templateList.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <label className="block text-xs text-gray-400 mb-1">Host / IP</label>
              <input
                required
                value={form.host}
                onChange={e => setForm(p => ({ ...p, host: e.target.value }))}
                placeholder="192.168.1.10"
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Puerto</label>
              <input
                value={form.port}
                onChange={e => setForm(p => ({ ...p, port: e.target.value }))}
                placeholder="502"
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">Poll interval (ms)</label>
            <input
              type="number"
              value={form.poll_interval_ms}
              onChange={e => setForm(p => ({ ...p, poll_interval_ms: e.target.value }))}
              className="w-32 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded font-medium text-sm transition-colors"
          >
            {saving ? 'Guardando...' : 'Guardar dispositivo'}
          </button>

          {msg && <p className="text-sm text-blue-300">{msg}</p>}
        </form>
      </div>
    </div>
  )
}
