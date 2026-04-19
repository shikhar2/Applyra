import React, { useEffect, useRef, useState } from 'react'
import { applicationApi } from '../api/client'
import api from '../api/client'
import toast from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Clock, Send, CheckCircle, XCircle, TrendingUp, Star,
  ExternalLink, Mail, GraduationCap, ChevronDown, GripVertical
} from 'lucide-react'

const COLUMNS = [
  { status: 'pending',   label: 'Queued',    color: '#eab308', glow: 'rgba(234,179,8,0.15)',   icon: Clock },
  { status: 'applied',   label: 'Applied',   color: '#3b82f6', glow: 'rgba(59,130,246,0.15)',  icon: Send },
  { status: 'interview', label: 'Interview', color: '#a855f7', glow: 'rgba(168,85,247,0.15)',  icon: TrendingUp },
  { status: 'offer',     label: 'Offer',     color: '#22c55e', glow: 'rgba(34,197,94,0.15)',   icon: Star },
  { status: 'rejected',  label: 'Rejected',  color: '#ef4444', glow: 'rgba(239,68,68,0.15)',   icon: XCircle },
]

function KanbanCard({ app, onMove, onFollowUp, onPrep, isDragging }: any) {
  const [expanded, setExpanded] = useState(false)
  const score = Math.round((app.match_score || 0) * 100)
  const scoreColor = score >= 85 ? '#34d399' : score >= 70 ? '#fbbf24' : 'rgba(255,255,255,0.4)'

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: isDragging ? 0.5 : 1, y: 0, scale: isDragging ? 1.02 : 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="rounded-xl p-3 mb-2 cursor-grab active:cursor-grabbing"
      style={{
        background: 'rgba(255,255,255,0.04)',
        border: isDragging ? '1px solid rgba(99,102,241,0.4)' : '1px solid rgba(255,255,255,0.07)',
        boxShadow: isDragging ? '0 8px 32px rgba(0,0,0,0.5)' : 'none',
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <GripVertical className="w-3 h-3 flex-shrink-0 opacity-20" />
          <div className="min-w-0">
            <p className="text-sm font-medium text-white truncate">{app.job?.title}</p>
            <p className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>{app.job?.company}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span className="text-xs font-bold" style={{ color: scoreColor }}>{score}%</span>
          <a href={app.job?.url} target="_blank" rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="transition-colors" style={{ color: 'rgba(255,255,255,0.2)' }}
            onMouseEnter={e => (e.currentTarget.style.color = '#60a5fa')}
            onMouseLeave={e => (e.currentTarget.style.color = 'rgba(255,255,255,0.2)')}>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      <button onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs mt-2 transition-colors"
        style={{ color: 'rgba(255,255,255,0.25)' }}
        onMouseEnter={e => (e.currentTarget.style.color = 'rgba(255,255,255,0.6)')}
        onMouseLeave={e => (e.currentTarget.style.color = 'rgba(255,255,255,0.25)')}>
        <ChevronDown className={`w-3 h-3 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        Actions
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-2 pt-2 space-y-1.5" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
              <div className="flex flex-wrap gap-1">
                {['pending', 'applied', 'interview', 'offer', 'rejected'].filter(s => s !== app.status).map(s => (
                  <motion.button key={s} onClick={() => onMove(app.id, s)}
                    whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                    className="text-xs px-2 py-0.5 rounded-lg transition-colors"
                    style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.6)' }}>
                    → {s}
                  </motion.button>
                ))}
              </div>
              <div className="flex gap-1">
                {app.status === 'applied' && (
                  <motion.button onClick={() => onFollowUp(app.id)}
                    whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                    className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-lg"
                    style={{ background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.25)', color: '#60a5fa' }}>
                    <Mail className="w-3 h-3" /> Follow-up
                  </motion.button>
                )}
                {app.status === 'interview' && (
                  <motion.button onClick={() => onPrep(app)}
                    whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                    className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-lg"
                    style={{ background: 'rgba(168,85,247,0.12)', border: '1px solid rgba(168,85,247,0.25)', color: '#c084fc' }}>
                    <GraduationCap className="w-3 h-3" /> Prep
                  </motion.button>
                )}
              </div>
              {app.cover_letter && (
                <p className="text-xs line-clamp-2" style={{ color: 'rgba(255,255,255,0.25)' }}>
                  {app.cover_letter.slice(0, 120)}...
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function KanbanColumn({ col, items, onMove, onFollowUp, onPrep, onDrop }: any) {
  const [dragOver, setDragOver] = useState(false)
  const Icon = col.icon

  return (
    <div
      className="flex-1 min-w-[220px] max-w-[300px] rounded-2xl p-3 flex flex-col transition-all duration-200"
      style={{
        background: dragOver ? col.glow : 'rgba(255,255,255,0.02)',
        border: dragOver ? `1px solid ${col.color}44` : '1px solid rgba(255,255,255,0.06)',
        borderTop: `2px solid ${col.color}`,
        boxShadow: dragOver ? `0 0 20px ${col.color}22` : 'none',
      }}
      onDragOver={e => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={e => {
        e.preventDefault()
        setDragOver(false)
        const id = Number(e.dataTransfer.getData('appId'))
        if (id) onDrop(id, col.status)
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="w-3.5 h-3.5" style={{ color: col.color }} />
          <span className="text-sm font-semibold text-white">{col.label}</span>
        </div>
        <span
          className="text-xs font-bold px-2 py-0.5 rounded-full"
          style={{ background: `${col.color}18`, color: col.color, border: `1px solid ${col.color}30` }}
        >
          {items.length}
        </span>
      </div>

      <div className="flex-1 max-h-[calc(100vh-220px)] overflow-y-auto space-y-0 pr-0.5">
        <AnimatePresence>
          {items.length === 0 ? (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: dragOver ? 0.6 : 0.25 }}
              className="text-xs text-center py-6"
              style={{ color: col.color }}
            >
              {dragOver ? 'Drop here' : 'No applications'}
            </motion.p>
          ) : (
            items.map((app: any) => (
              <div
                key={app.id}
                draggable
                onDragStart={e => e.dataTransfer.setData('appId', String(app.id))}
              >
                <KanbanCard
                  app={app}
                  onMove={onMove}
                  onFollowUp={onFollowUp}
                  onPrep={onPrep}
                  isDragging={false}
                />
              </div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default function KanbanPage() {
  const [apps, setApps] = useState<any[]>([])
  const [followUpResult, setFollowUpResult] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const r = await applicationApi.list({ limit: 200 })
      setApps(r.data)
    } catch (e: any) { toast.error(e.message) }
    finally { setLoading(false) }
  }

  async function moveApp(id: number, status: string) {
    // Optimistic update
    setApps(prev => prev.map(a => a.id === id ? { ...a, status } : a))
    try {
      await applicationApi.update(id, { status })
      toast.success(`Moved to ${status}`)
    } catch (e: any) {
      toast.error(e.message)
      load() // revert
    }
  }

  async function generateFollowUp(appId: number) {
    try {
      const r = await api.post('/ai/follow-up', { application_id: appId, followup_type: 'gentle_check' })
      setFollowUpResult(r.data)
      toast.success('Follow-up email generated')
    } catch (e: any) { toast.error(e.message) }
  }

  function openPrep(app: any) {
    window.location.href = `/interview-prep?company=${encodeURIComponent(app.job?.company || '')}&title=${encodeURIComponent(app.job?.title || '')}`
  }

  const grouped: Record<string, any[]> = {}
  COLUMNS.forEach(c => { grouped[c.status] = [] })
  apps.forEach(a => {
    const s = a.status
    if (grouped[s]) grouped[s].push(a)
    else if (s === 'applying') grouped['applied']?.push(a)
    else if (s === 'failed' || s === 'skipped') grouped['rejected']?.push(a)
  })

  return (
    <div className="p-6 h-full flex flex-col">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-5"
      >
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #ec4899, #a855f7)' }}>
            <TrendingUp className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Application Pipeline</h1>
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
              {apps.length} total · drag cards to update status
            </p>
          </div>
        </div>
      </motion.div>

      {/* Follow-up modal */}
      <AnimatePresence>
        {followUpResult && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="mb-4 rounded-2xl p-4"
            style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)' }}
          >
            <div className="flex justify-between items-start mb-2">
              <h3 className="text-sm font-semibold" style={{ color: '#60a5fa' }}>Generated Follow-up Email</h3>
              <button onClick={() => setFollowUpResult(null)}
                className="text-xs px-2 py-0.5 rounded-lg"
                style={{ color: 'rgba(255,255,255,0.4)', background: 'rgba(255,255,255,0.05)' }}>
                Close
              </button>
            </div>
            <p className="text-xs mb-1" style={{ color: 'rgba(96,165,250,0.7)' }}>Subject: {followUpResult.email?.subject}</p>
            <div className="rounded-xl p-3 text-sm whitespace-pre-wrap"
              style={{ background: 'rgba(0,0,0,0.3)', color: 'rgba(255,255,255,0.7)' }}>
              {followUpResult.email?.body}
            </div>
            <motion.button
              onClick={() => { navigator.clipboard.writeText(followUpResult.email?.body || ''); toast.success('Copied!') }}
              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              className="mt-2 text-xs px-3 py-1.5 rounded-xl font-medium"
              style={{ background: 'rgba(59,130,246,0.2)', border: '1px solid rgba(59,130,246,0.3)', color: '#60a5fa' }}>
              Copy to Clipboard
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
            className="w-8 h-8 rounded-full"
            style={{ border: '2px solid rgba(255,255,255,0.08)', borderTopColor: '#a855f7' }}
          />
        </div>
      ) : (
        <div className="flex-1 flex gap-4 overflow-x-auto pb-4">
          {COLUMNS.map(col => (
            <KanbanColumn
              key={col.status}
              col={col}
              items={grouped[col.status] || []}
              onMove={moveApp}
              onFollowUp={generateFollowUp}
              onPrep={openPrep}
              onDrop={moveApp}
            />
          ))}
        </div>
      )}
    </div>
  )
}
