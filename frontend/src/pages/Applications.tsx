import React, { useEffect, useState } from 'react'
import { applicationApi, followupApi } from '../api/client'
import api from '../api/client'
import toast from 'react-hot-toast'
import { ExternalLink, CheckCircle, Clock, XCircle, TrendingUp, FileText, Layers, ChevronRight, Star, RotateCcw, Download, Sparkles, Mail, Send, SkipForward } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; border: string; icon: any }> = {
  pending:   { label: 'Pending',   color: '#fbbf24', bg: 'rgba(251,191,36,0.12)',  border: 'rgba(251,191,36,0.3)',  icon: Clock },
  applying:  { label: 'Applying',  color: '#60a5fa', bg: 'rgba(96,165,250,0.12)',  border: 'rgba(96,165,250,0.3)',  icon: Clock },
  applied:   { label: 'Applied',   color: '#34d399', bg: 'rgba(52,211,153,0.12)',  border: 'rgba(52,211,153,0.3)',  icon: CheckCircle },
  failed:    { label: 'Failed',    color: '#f87171', bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.3)', icon: XCircle },
  skipped:   { label: 'Skipped',   color: 'rgba(255,255,255,0.4)', bg: 'rgba(255,255,255,0.06)', border: 'rgba(255,255,255,0.12)', icon: XCircle },
  interview: { label: 'Interview', color: '#a78bfa', bg: 'rgba(167,139,250,0.12)', border: 'rgba(167,139,250,0.3)', icon: TrendingUp },
  rejected:  { label: 'Rejected',  color: '#f87171', bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.3)', icon: XCircle },
  offer:     { label: 'Offer!',    color: '#34d399', bg: 'rgba(52,211,153,0.15)',  border: 'rgba(52,211,153,0.4)',  icon: Star },
}

function StatusBadge({ status }: { status: string }) {
  const sc = STATUS_CONFIG[status] || STATUS_CONFIG.pending
  const Icon = sc.icon
  return (
    <span
      className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full"
      style={{ color: sc.color, background: sc.bg, border: `1px solid ${sc.border}` }}
    >
      <Icon className="w-3 h-3" />
      {sc.label}
    </span>
  )
}

function MatchScoreCircle({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color  = pct >= 85 ? '#34d399' : pct >= 70 ? '#fbbf24' : '#f87171'
  const bg     = pct >= 85 ? 'rgba(52,211,153,0.12)' : pct >= 70 ? 'rgba(251,191,36,0.12)' : 'rgba(248,113,113,0.12)'
  const border = pct >= 85 ? 'rgba(52,211,153,0.35)' : pct >= 70 ? 'rgba(251,191,36,0.35)' : 'rgba(248,113,113,0.35)'
  return (
    <div
      className="flex items-center justify-center w-11 h-11 rounded-full flex-shrink-0"
      style={{ background: bg, border: `2px solid ${border}` }}
    >
      <span className="text-xs font-bold leading-none" style={{ color }}>{pct}%</span>
    </div>
  )
}

const FOLLOWUP_TYPE_LABEL: Record<string, string> = {
  thank_you: 'Thank You',
  gentle_check: 'Check-In',
  final_followup: 'Final Follow-Up',
}

const FOLLOWUP_STATUS_COLOR: Record<string, string> = {
  pending: '#fbbf24',
  sent: '#34d399',
  skipped: 'rgba(255,255,255,0.3)',
  failed: '#f87171',
}

function FollowUpTimeline({ appId, appStatus }: { appId: number; appStatus: string }) {
  const [followups, setFollowups] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState<number | null>(null)

  useEffect(() => {
    followupApi.list(appId)
      .then(r => setFollowups(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [appId])

  async function handleSend(fuId: number) {
    setActing(fuId)
    try {
      const r = await followupApi.send(fuId)
      toast.success('Follow-up sent!')
      setFollowups(prev => prev.map(f => f.id === fuId ? { ...f, status: 'sent', subject: r.data.subject, body: r.data.body } : f))
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setActing(null)
    }
  }

  async function handleSkip(fuId: number) {
    setActing(fuId)
    try {
      await followupApi.skip(fuId)
      setFollowups(prev => prev.map(f => f.id === fuId ? { ...f, status: 'skipped' } : f))
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setActing(null)
    }
  }

  if (loading) return (
    <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>Loading follow-ups…</p>
  )

  if (followups.length === 0) {
    if (appStatus !== 'applied') return null
    return (
      <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
        Follow-ups will be scheduled once the application is processed.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {followups.map((fu) => {
        const color = FOLLOWUP_STATUS_COLOR[fu.status] || '#fbbf24'
        const isDue = fu.status === 'pending' && new Date(fu.scheduled_for) <= new Date()
        return (
          <div key={fu.id} className="rounded-xl p-3" style={{ background: 'rgba(0,0,0,0.25)', border: `1px solid rgba(255,255,255,0.06)` }}>
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
                <span className="text-xs font-semibold text-white">{FOLLOWUP_TYPE_LABEL[fu.followup_type] || fu.label}</span>
                {isDue && (
                  <span className="text-xs font-bold px-1.5 py-0.5 rounded-md" style={{ background: 'rgba(251,191,36,0.15)', color: '#fbbf24' }}>Due</span>
                )}
              </div>
              <span className="text-xs capitalize" style={{ color }}>{fu.status}</span>
            </div>
            <p className="text-xs mb-2" style={{ color: 'rgba(255,255,255,0.35)' }}>
              {fu.status === 'sent' && fu.sent_at
                ? `Sent ${new Date(fu.sent_at).toLocaleDateString()}`
                : `Scheduled ${new Date(fu.scheduled_for).toLocaleDateString()}`}
            </p>
            {fu.subject && (
              <p className="text-xs mb-2 truncate" style={{ color: 'rgba(255,255,255,0.5)' }}>{fu.subject}</p>
            )}
            {fu.status === 'pending' && (
              <div className="flex gap-1.5">
                <motion.button
                  onClick={() => handleSend(fu.id)}
                  disabled={acting === fu.id}
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                  className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg font-medium"
                  style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.25)', color: '#34d399' }}
                >
                  <Send className="w-3 h-3" />
                  {acting === fu.id ? 'Sending…' : 'Send Now'}
                </motion.button>
                <motion.button
                  onClick={() => handleSkip(fu.id)}
                  disabled={acting === fu.id}
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                  className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg font-medium"
                  style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.4)' }}
                >
                  <SkipForward className="w-3 h-3" />
                  Skip
                </motion.button>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function ApplicationsPage() {
  const [apps, setApps] = useState<any[]>([])
  const [filter, setFilter] = useState('')
  const [selected, setSelected] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { load() }, [filter])

  async function load() {
    setLoading(true)
    try {
      const params: any = { limit: 100 }
      if (filter) params.status = filter
      const r = await applicationApi.list(params)
      setApps(r.data)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function updateStatus(id: number, status: string) {
    try {
      await applicationApi.update(id, { status })
      toast.success('Status updated')
      load()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  async function retryFailed() {
    const failed = apps.filter(a => a.status === 'failed')
    if (failed.length === 0) { toast('No failed applications to retry'); return }
    try {
      await api.post('/applications/retry-failed')
      toast.success(`Retrying ${failed.length} failed application${failed.length > 1 ? 's' : ''}`)
      load()
    } catch (e: any) {
      // Fallback: bulk-reset to pending so the engine picks them up on next run
      await Promise.all(failed.map(a => applicationApi.update(a.id, { status: 'pending' })))
      toast.success(`Reset ${failed.length} failed → pending for next run`)
      load()
    }
  }

  const failedCount = apps.filter(a => a.status === 'failed').length

  return (
    <div className="p-8 flex gap-5 min-h-full">
      {/* Left: applications list */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="flex items-center justify-between mb-6"
        >
          <div className="flex items-center gap-4">
            <div
              className="w-11 h-11 rounded-2xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #6366f1, #a78bfa)' }}
            >
              <Layers className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Applications</h1>
              <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
                {apps.length} total tracked
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {failedCount > 0 && (
              <motion.button
                onClick={retryFailed}
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.96 }}
                className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-xl font-semibold"
                style={{ background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.25)', color: '#f87171' }}
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Retry {failedCount} Failed
              </motion.button>
            )}
            {/* Filter select */}
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="input-glass rounded-xl px-3 py-2.5 text-sm"
            >
              <option value="">All statuses</option>
              {Object.entries(STATUS_CONFIG).map(([k, v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </select>
          </div>
        </motion.div>

        {/* List */}
        {loading ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center py-20"
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
              className="w-10 h-10 rounded-full mb-4"
              style={{ border: '2px solid rgba(255,255,255,0.08)', borderTopColor: '#60a5fa' }}
            />
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>Loading applications...</p>
          </motion.div>
        ) : apps.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            className="card-3d rounded-2xl flex flex-col items-center py-20 text-center"
          >
            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
              style={{ background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.2)' }}
            >
              <Layers className="w-8 h-8" style={{ color: '#a78bfa' }} />
            </motion.div>
            <h3 className="text-lg font-semibold text-white mb-2">No applications yet</h3>
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Start the auto-apply bot from the Dashboard to track applications here
            </p>
          </motion.div>
        ) : (
          <div className="space-y-2">
            {apps.map((app, i) => {
              const isSelected = selected?.id === app.id
              return (
                <motion.div
                  key={app.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03, duration: 0.25 }}
                  onClick={() => setSelected(isSelected ? null : app)}
                  className="card-3d rounded-2xl p-4 cursor-pointer transition-all"
                  style={isSelected ? { borderColor: 'rgba(99,102,241,0.5)', boxShadow: '0 0 0 1px rgba(99,102,241,0.25), 0 20px 60px rgba(0,0,0,0.5)' } : {}}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      {/* Match score */}
                      {app.match_score > 0 && <MatchScoreCircle score={app.match_score} />}

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-white truncate">{app.job?.title}</span>
                          {app.is_top_tier && (
                            <span className="flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                              style={{ background: 'rgba(251,191,36,0.12)', border: '1px solid rgba(251,191,36,0.3)', color: '#fbbf24' }}>
                              <Sparkles className="w-2.5 h-2.5" /> Top-Tier
                            </span>
                          )}
                          {app.has_tailored_resume && (
                            <span className="flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                              style={{ background: 'rgba(52,211,153,0.10)', border: '1px solid rgba(52,211,153,0.25)', color: '#34d399' }}>
                              <FileText className="w-2.5 h-2.5" /> Tailored CV
                            </span>
                          )}
                          <a
                            href={app.job?.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="flex-shrink-0 transition-colors"
                            style={{ color: 'rgba(255,255,255,0.3)' }}
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                        <p className="text-sm mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>
                          {app.job?.company}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 flex-shrink-0">
                      <StatusBadge status={app.status} />
                      <ChevronRight
                        className="w-4 h-4 transition-transform"
                        style={{
                          color: 'rgba(255,255,255,0.2)',
                          transform: isSelected ? 'rotate(90deg)' : 'rotate(0deg)',
                        }}
                      />
                    </div>
                  </div>

                  {/* Expanded: status update buttons */}
                  <AnimatePresence>
                    {isSelected && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden"
                      >
                        <div
                          className="mt-3 pt-3 flex flex-wrap gap-2"
                          style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}
                        >
                          <span className="text-xs self-center mr-1" style={{ color: 'rgba(255,255,255,0.35)' }}>
                            Update status:
                          </span>
                          {['interview', 'rejected', 'offer'].map((s) => {
                            const sc = STATUS_CONFIG[s]
                            return (
                              <motion.button
                                key={s}
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={(e) => { e.stopPropagation(); updateStatus(app.id, s) }}
                                className="text-xs px-3 py-1.5 rounded-lg font-medium transition-all"
                                style={{ color: sc.color, background: sc.bg, border: `1px solid ${sc.border}` }}
                              >
                                {sc.label}
                              </motion.button>
                            )
                          })}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )
            })}
          </div>
        )}
      </div>

      {/* Right: detail panel */}
      <AnimatePresence>
        {selected && (
          <motion.div
            key="detail"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 24 }}
            transition={{ duration: 0.3 }}
            className="w-88 flex-shrink-0"
            style={{ width: '22rem' }}
          >
            <div className="card-3d rounded-2xl p-5 sticky top-6">
              {/* Panel header */}
              <div className="flex items-start justify-between gap-3 mb-4">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-white leading-snug">{selected.job?.title}</h3>
                  <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
                    {selected.job?.company}
                  </p>
                </div>
                {selected.match_score > 0 && <MatchScoreCircle score={selected.match_score} />}
              </div>

              {/* Status + badges */}
              <div className="flex items-center gap-2 flex-wrap mb-4">
                <StatusBadge status={selected.status} />
                {selected.is_top_tier && (
                  <span className="flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full"
                    style={{ background: 'rgba(251,191,36,0.12)', border: '1px solid rgba(251,191,36,0.3)', color: '#fbbf24' }}>
                    <Sparkles className="w-3 h-3" /> Top-Tier Company
                  </span>
                )}
              </div>

              {/* Tailored resume download */}
              {selected.has_tailored_resume && (
                <motion.a
                  href={`/api/applications/${selected.id}/tailored-resume`}
                  target="_blank"
                  rel="noopener noreferrer"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="flex items-center gap-2 w-full px-4 py-2.5 rounded-xl text-sm font-semibold mb-4"
                  style={{ background: 'rgba(52,211,153,0.10)', border: '1px solid rgba(52,211,153,0.25)', color: '#34d399' }}
                >
                  <Download className="w-4 h-4" />
                  Download Tailored Resume (PDF)
                </motion.a>
              )}

              <div style={{ background: 'rgba(255,255,255,0.05)', height: 1 }} className="mb-4" />

              {/* Cover letter */}
              {selected.cover_letter && (
                <div className="mb-4">
                  <p
                    className="text-xs font-medium mb-2 flex items-center gap-1.5"
                    style={{ color: 'rgba(255,255,255,0.4)' }}
                  >
                    <div
                      className="w-5 h-5 rounded-md flex items-center justify-center"
                      style={{ background: 'rgba(96,165,250,0.15)' }}
                    >
                      <FileText className="w-3 h-3" style={{ color: '#60a5fa' }} />
                    </div>
                    Cover Letter
                  </p>
                  <div
                    className="rounded-xl p-3.5 text-xs leading-relaxed max-h-52 overflow-auto"
                    style={{
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.07)',
                      color: 'rgba(255,255,255,0.7)',
                    }}
                  >
                    {selected.cover_letter}
                  </div>
                </div>
              )}

              {/* Match analysis */}
              {selected.match_score > 0 && (
                <div>
                  <p
                    className="text-xs font-medium mb-2 flex items-center gap-1.5"
                    style={{ color: 'rgba(255,255,255,0.4)' }}
                  >
                    <div
                      className="w-5 h-5 rounded-md flex items-center justify-center"
                      style={{ background: 'rgba(167,139,250,0.15)' }}
                    >
                      <TrendingUp className="w-3 h-3" style={{ color: '#a78bfa' }} />
                    </div>
                    Match Analysis
                  </p>
                  <p
                    className="text-xs leading-relaxed"
                    style={{ color: 'rgba(255,255,255,0.5)' }}
                  >
                    {selected.match_explanation || '—'}
                  </p>
                </div>
              )}

              {/* Follow-up timeline — only for applied+ */}
              {['applied', 'interview', 'rejected', 'offer'].includes(selected.status) && (
                <div className="mt-4">
                  <div style={{ background: 'rgba(255,255,255,0.05)', height: 1 }} className="mb-4" />
                  <p
                    className="text-xs font-medium mb-3 flex items-center gap-1.5"
                    style={{ color: 'rgba(255,255,255,0.4)' }}
                  >
                    <div
                      className="w-5 h-5 rounded-md flex items-center justify-center"
                      style={{ background: 'rgba(52,211,153,0.15)' }}
                    >
                      <Mail className="w-3 h-3" style={{ color: '#34d399' }} />
                    </div>
                    Follow-Up Schedule
                  </p>
                  <FollowUpTimeline appId={selected.id} appStatus={selected.status} />
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
