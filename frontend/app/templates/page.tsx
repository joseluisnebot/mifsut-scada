'use client'

import { useEffect, useState } from 'react'
import { PlusCircle, Trash2, FileText, ChevronDown, ChevronUp } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const PROTOCOLS = ['modbus', 'opcua', 'ethernet_ip', 'bacnet', 'dnp3', 'snmp', 'mqtt_ext']

const PROTOCOL_FIELDS: Record<string, string[]> = {
  modbus:      ['address', 'scale', 'type', 'unit', 'writable'],
  opcua:       ['node_id', 'type', 'unit', 'writable'],
  ethernet_ip: ['tag_name', 'type', 'unit', 'writable'],
  bacnet:      ['object_type', 'object_instance', 'property', 'unit', 'writable'],
  dnp3:        ['group', 'variation', 'index', 'unit', 'writable'],
  snmp:        ['oid', 'type', 'unit'],
  mqtt_ext:    ['subscribe_topic', 'publish_topic', 'type', 'unit', 'writable'],
}

const TAG_TYPES = ['float32', 'float', 'int16', 'int32', 'int', 'bool', 'real']

interface Tag {
  id: string
  type: string
  unit: string
  writable: boolean
  scale: number
  address?: number
  node_id?: string
  tag_name?: string
  object_type?: string
  object_instance?: number
  property?: string
  oid?: string
  group?: number
  variation?: number
  index?: number
  subscribe_topic?: string
  publish_topic?: string
}

interface Template {
  name: string
  manufacturer: string
  model: string
  protocol: string
  tags: Tag[]
}

function emptyTag(): Tag {
  return { id: '', type: 'float32', unit: '', writable: false, scale: 1 }
}

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Record<string, string[]>>({})
  const [expanded, setExpanded] = useState<string | null>(null)
  const [detail, setDetail] = useState<Template | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [msg, setMsg] = useState('')
  const [saving, setSaving] = useState(false)

  const [form, setForm] = useState({
    protocol: 'modbus',
    name: '',
    manufacturer: '',
    model: '',
    community: '',
    version: 'v2c',
  })
  const [tags, setTags] = useState<Tag[]>([emptyTag()])

  const load = async () => {
    const res = await fetch(`${API_URL}/api/templates`)
    setTemplates(await res.json())
  }

  useEffect(() => { load() }, [])

  const loadDetail = async (protocol: string, name: string) => {
    const key = `${protocol}/${name}`
    if (expanded === key) { setExpanded(null); setDetail(null); return }
    setExpanded(key)
    const res = await fetch(`${API_URL}/api/templates/${protocol}/${name}`)
    const data = await res.json()
    setDetail({ name, ...data })
  }

  const deleteTemplate = async (protocol: string, name: string) => {
    if (!confirm(`¿Borrar template "${name}"?`)) return
    await fetch(`${API_URL}/api/templates/${protocol}/${name}`, { method: 'DELETE' })
    setExpanded(null)
    setDetail(null)
    load()
  }

  const addTag = () => setTags(t => [...t, emptyTag()])
  const removeTag = (i: number) => setTags(t => t.filter((_, j) => j !== i))
  const updateTag = (i: number, field: string, value: any) =>
    setTags(t => t.map((tag, j) => j === i ? { ...tag, [field]: value } : tag))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const body = { ...form, tags }
      const res = await fetch(`${API_URL}/api/templates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        setMsg('Template creado correctamente')
        setShowForm(false)
        setTags([emptyTag()])
        setForm({ protocol: 'modbus', name: '', manufacturer: '', model: '', community: '', version: 'v2c' })
        load()
      } else {
        const err = await res.json()
        setMsg(`Error: ${err.detail}`)
      }
    } catch { setMsg('Error de red') }
    finally {
      setSaving(false)
      setTimeout(() => setMsg(''), 4000)
    }
  }

  const fields = PROTOCOL_FIELDS[form.protocol] || []

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Templates</h1>
        <button onClick={() => setShowForm(f => !f)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium transition-colors">
          <PlusCircle size={16} /> Nuevo template
        </button>
      </div>

      {/* ── Formulario nuevo template ── */}
      {showForm && (
        <form onSubmit={handleSubmit}
          className="bg-gray-900 border border-blue-700 rounded-xl p-6 mb-8 space-y-5">
          <h2 className="text-lg font-semibold text-blue-400">Crear template</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Protocolo</label>
              <select required value={form.protocol}
                onChange={e => setForm(p => ({ ...p, protocol: e.target.value }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500">
                {PROTOCOLS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Nombre del template</label>
              <input required value={form.name} placeholder="delta-ms300"
                onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Fabricante</label>
              <input required value={form.manufacturer} placeholder="Delta Electronics"
                onChange={e => setForm(p => ({ ...p, manufacturer: e.target.value }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Modelo</label>
              <input required value={form.model} placeholder="MS300"
                onChange={e => setForm(p => ({ ...p, model: e.target.value }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500" />
            </div>
            {form.protocol === 'snmp' && <>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Versión SNMP</label>
                <select value={form.version} onChange={e => setForm(p => ({ ...p, version: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500">
                  <option>v1</option><option>v2c</option><option>v3</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Community</label>
                <input value={form.community} placeholder="public"
                  onChange={e => setForm(p => ({ ...p, community: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:border-blue-500" />
              </div>
            </>}
          </div>

          {/* Tags */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-300">Tags</label>
              <button type="button" onClick={addTag}
                className="text-xs px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded transition-colors">
                + Añadir tag
              </button>
            </div>

            <div className="space-y-2">
              {tags.map((tag, i) => (
                <div key={i} className="bg-gray-800 rounded-lg p-3 grid gap-2"
                  style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>

                  <div>
                    <label className="block text-xs text-gray-500 mb-0.5">ID tag</label>
                    <input value={tag.id} placeholder="frecuencia_salida"
                      onChange={e => updateTag(i, 'id', e.target.value)}
                      className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                  </div>

                  {fields.includes('address') && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-0.5">Dirección (40001+)</label>
                      <input type="number" value={tag.address ?? ''} placeholder="48450"
                        onChange={e => updateTag(i, 'address', parseInt(e.target.value))}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                    </div>
                  )}
                  {fields.includes('scale') && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-0.5">Scale</label>
                      <input type="number" step="any" value={tag.scale}
                        onChange={e => updateTag(i, 'scale', parseFloat(e.target.value))}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                    </div>
                  )}
                  {fields.includes('node_id') && (
                    <div className="col-span-2">
                      <label className="block text-xs text-gray-500 mb-0.5">Node ID</label>
                      <input value={tag.node_id ?? ''} placeholder="ns=2;s=DB1.Temp"
                        onChange={e => updateTag(i, 'node_id', e.target.value)}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                    </div>
                  )}
                  {fields.includes('tag_name') && (
                    <div className="col-span-2">
                      <label className="block text-xs text-gray-500 mb-0.5">Tag name PLC</label>
                      <input value={tag.tag_name ?? ''} placeholder="Program:Main.Speed"
                        onChange={e => updateTag(i, 'tag_name', e.target.value)}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                    </div>
                  )}
                  {fields.includes('object_type') && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-0.5">Object type</label>
                      <input value={tag.object_type ?? ''} placeholder="analogInput"
                        onChange={e => updateTag(i, 'object_type', e.target.value)}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                    </div>
                  )}
                  {fields.includes('object_instance') && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-0.5">Instance</label>
                      <input type="number" value={tag.object_instance ?? ''}
                        onChange={e => updateTag(i, 'object_instance', parseInt(e.target.value))}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                    </div>
                  )}
                  {fields.includes('property') && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-0.5">Property</label>
                      <input value={tag.property ?? 'presentValue'}
                        onChange={e => updateTag(i, 'property', e.target.value)}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                    </div>
                  )}
                  {fields.includes('oid') && (
                    <div className="col-span-2">
                      <label className="block text-xs text-gray-500 mb-0.5">OID</label>
                      <input value={tag.oid ?? ''} placeholder="1.3.6.1.4.1..."
                        onChange={e => updateTag(i, 'oid', e.target.value)}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                    </div>
                  )}
                  {fields.includes('group') && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-0.5">Group</label>
                      <input type="number" value={tag.group ?? ''}
                        onChange={e => updateTag(i, 'group', parseInt(e.target.value))}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                    </div>
                  )}
                  {fields.includes('variation') && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-0.5">Variation</label>
                      <input type="number" value={tag.variation ?? ''}
                        onChange={e => updateTag(i, 'variation', parseInt(e.target.value))}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                    </div>
                  )}
                  {fields.includes('index') && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-0.5">Index</label>
                      <input type="number" value={tag.index ?? ''}
                        onChange={e => updateTag(i, 'index', parseInt(e.target.value))}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                    </div>
                  )}
                  {fields.includes('subscribe_topic') && (
                    <div className="col-span-2">
                      <label className="block text-xs text-gray-500 mb-0.5">Topic suscripción</label>
                      <input value={tag.subscribe_topic ?? ''}
                        placeholder="sensors/{device_id}/temp"
                        onChange={e => updateTag(i, 'subscribe_topic', e.target.value)}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                    </div>
                  )}
                  {fields.includes('publish_topic') && (
                    <div className="col-span-2">
                      <label className="block text-xs text-gray-500 mb-0.5">Topic publicación</label>
                      <input value={tag.publish_topic ?? ''}
                        placeholder="sensors/{device_id}/setpoint"
                        onChange={e => updateTag(i, 'publish_topic', e.target.value)}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                    </div>
                  )}

                  {fields.includes('type') && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-0.5">Tipo</label>
                      <select value={tag.type} onChange={e => updateTag(i, 'type', e.target.value)}
                        className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500">
                        {TAG_TYPES.map(t => <option key={t}>{t}</option>)}
                      </select>
                    </div>
                  )}
                  <div>
                    <label className="block text-xs text-gray-500 mb-0.5">Unidad</label>
                    <input value={tag.unit} placeholder="Hz"
                      onChange={e => updateTag(i, 'unit', e.target.value)}
                      className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs focus:outline-none focus:border-blue-500" />
                  </div>
                  {fields.includes('writable') && (
                    <div className="flex items-center gap-2 pt-4">
                      <input type="checkbox" id={`w${i}`} checked={tag.writable}
                        onChange={e => updateTag(i, 'writable', e.target.checked)}
                        className="accent-blue-500" />
                      <label htmlFor={`w${i}`} className="text-xs text-gray-400">Escribible</label>
                    </div>
                  )}

                  <div className="flex items-end justify-end">
                    <button type="button" onClick={() => removeTag(i)}
                      className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-900/30 rounded transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button type="submit" disabled={saving}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded font-medium text-sm transition-colors">
              {saving ? 'Guardando...' : 'Guardar template'}
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors">
              Cancelar
            </button>
            {msg && <span className="text-sm text-blue-300">{msg}</span>}
          </div>
        </form>
      )}

      {msg && !showForm && <p className="mb-4 text-sm text-blue-300">{msg}</p>}

      {/* ── Lista de templates ── */}
      <div className="space-y-3">
        {Object.entries(templates).map(([protocol, names]) => (
          <div key={protocol}>
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-1">
              {protocol}
            </div>
            {names.map(name => {
              const key = `${protocol}/${name}`
              const isOpen = expanded === key
              return (
                <div key={name} className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden mb-2">
                  <div className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-800 transition-colors"
                    onClick={() => loadDetail(protocol, name)}>
                    <FileText size={16} className="text-blue-400 shrink-0" />
                    <span className="font-medium text-sm flex-1">{name}</span>
                    <span className="text-xs text-gray-500">{protocol}</span>
                    <button onClick={e => { e.stopPropagation(); deleteTemplate(protocol, name) }}
                      className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors">
                      <Trash2 size={14} />
                    </button>
                    {isOpen ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
                  </div>

                  {isOpen && detail && (
                    <div className="border-t border-gray-800 px-4 py-3">
                      <div className="text-xs text-gray-400 mb-3">
                        {detail.manufacturer} · {detail.model}
                      </div>
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-gray-500 text-left">
                            <th className="pb-1 font-medium">Tag ID</th>
                            <th className="pb-1 font-medium">Tipo</th>
                            <th className="pb-1 font-medium">Unidad</th>
                            <th className="pb-1 font-medium">R/W</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800">
                          {(detail.tags || []).map((t: any) => (
                            <tr key={t.id}>
                              <td className="py-1 font-mono text-blue-300">{t.id}</td>
                              <td className="py-1 text-gray-400">{t.type}</td>
                              <td className="py-1 text-gray-400">{t.unit || '—'}</td>
                              <td className="py-1">
                                <span className={`px-1.5 py-0.5 rounded text-xs ${t.writable ? 'bg-green-900 text-green-400' : 'bg-gray-800 text-gray-500'}`}>
                                  {t.writable ? 'R/W' : 'R'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}
