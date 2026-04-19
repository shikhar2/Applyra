import React, { useEffect, useState } from 'react'
import api from '../api/client'
import toast from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircle, XCircle, ExternalLink, ChevronDown, ChevronUp,
  Zap, AlertTriangle, Target, TrendingUp, Shield, Lightbulb, Brain
} from 'lucide-react'

// ── helpers ──────────────────────────────────────────────────────────────

function scoreColor(s: number) {
  if (s >= 0.85) return '#34d399'
  if (s >= 0.70) return '#fbbf24'
  return '#f87171'
}

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const c = scoreColor(score)
  return (
    <div className="flex items-center justify-center w-14 h-14 rounded-full flex-shrink-0"
      style={{ background: `${c}18`, border: `2px solid ${c}55` }}>
      <span className="text-sm font-bold" style={{ color: c }}>{pct}%</span>
    </div>
  )
}

function Pill({ label, color }: { label: string; color: string }) {
  return (
    <span className="text-xs font-semibold px-2 py-0.5 rounded-full"
      style={{ background: `${color}18`, border: `1px solid ${color}44`, color }}>
      {label}
    </span>
  )
}

// ── Block renderers ───────────────────────────────────────────────────────

function BlockRow({ icon: Icon, title, children, accent = '#a78bfa' }: any) {
  return (
    <div className="flex gap-3">
      <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
        style={{ background: `${accent}18` }}>
        <Icon className="w-3.5 h-3.5" style={{ color: accent }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold mb-1" style={{ color: 'rgba(255,255,255,0.5)' }}>{title}</p>
        {children}
      </div>
    </div>
  )
}

function DeepAnalysisPanel({ analysis }: { analysis: any }) {
  if (!analysis?.blocks) return null
  const b = analysis.blocks

  const gapColor = { none: '#34d399', minor: '#fbbf24', major: '#f97316', dealbreaker: '#f87171' }
  const fitColor = { undershoot: '#f87171', good_fit: '#34d399', stretch: '#fbbf24' }
  const sigColor = { real: '#34d399', likely_real: '#60a5fa', ghost_job: '#f87171', repost: '#f97316', unknown: '#9ca3af' }

  return (
    <div className="space-y-4 mt-4">
      {/* Verdict summary */}
      {b.verdict_summary && (
        <div className="rounded-xl p-3.5 text-xs leading-relaxed"
          style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', color: 'rgba(255,255,255,0.75)' }}>
          {b.verdict_summary}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        {/* CV Match */}
        {b.cv_match && (
          <BlockRow icon={Target} title="CV Match" accent="#60a5fa">
            {b.cv_match.matching_skills?.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-1">
                {b.cv_match.matching_skills.slice(0, 4).map((s: string) => (
                  <Pill key={s} label={s} color="#34d399" />
                ))}
              </div>
            )}
            {b.cv_match.gaps?.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-1">
                {b.cv_match.gaps.slice(0, 3).map((g: string) => (
                  <Pill key={g} label={g} color="#f87171" />
                ))}
              </div>
            )}
            {b.cv_match.gap_severity && (
              <Pill label={`Gap: ${b.cv_match.gap_severity}`}
                color={(gapColor as any)[b.cv_match.gap_severity] || '#9ca3af'} />
            )}
          </BlockRow>
        )}

        {/* Level Strategy */}
        {b.level_strategy && (
          <BlockRow icon={TrendingUp} title="Level Fit" accent="#a78bfa">
            {b.level_strategy.fit && (
              <Pill label={b.level_strategy.fit.replace('_', ' ')}
                color={(fitColor as any)[b.level_strategy.fit] || '#9ca3af'} />
            )}
            {b.level_strategy.positioning_tip && (
              <p className="text-xs mt-1.5" style={{ color: 'rgba(255,255,255,0.5)' }}>
                {b.level_strategy.positioning_tip}
              </p>
            )}
          </BlockRow>
        )}

        {/* Compensation */}
        {b.compensation && (
          <BlockRow icon={Zap} title="Compensation" accent="#fbbf24">
            <p className="text-xs font-medium" style={{ color: 'rgba(255,255,255,0.8)' }}>
              {b.compensation.likely_range || 'Unknown'}
            </p>
            {b.compensation.fit && b.compensation.fit !== 'unknown' && (
              <Pill label={b.compensation.fit} color={b.compensation.fit === 'within' ? '#34d399' : '#fbbf24'} />
            )}
          </BlockRow>
        )}

        {/* Legitimacy */}
        {b.legitimacy && (
          <BlockRow icon={Shield} title="Job Legitimacy" accent="#34d399">
            {b.legitimacy.signals && (
              <Pill label={b.legitimacy.signals.replace('_', ' ')}
                color={(sigColor as any)[b.legitimacy.signals] || '#9ca3af'} />
            )}
            {b.legitimacy.red_flags?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {b.legitimacy.red_flags.map((f: string) => (
                  <Pill key={f} label={f} color="#f87171" />
                ))}
              </div>
            )}
          </BlockRow>
        )}
      </div>

      {/* Interview angle */}
      {b.interview_angle && (
        <BlockRow icon={Lightbulb} title="Interview Angles" accent="#f59e0b">
          {b.interview_angle.key_stories?.length > 0 && (
            <ul className="space-y-1 mb-2">
              {b.interview_angle.key_stories.map((s: string, i: number) => (
                <li key={i} className="text-xs flex gap-1.5" style={{ color: 'rgba(255,255,255,0.65)' }}>
                  <span style={{ color: '#f59e0b' }}>→</span> {s}
                </li>
              ))}
            </ul>
          )}
          {b.interview_angle.likely_questions?.length > 0 && (
            <ul className="space-y-1">
              {b.interview_angle.likely_questions.map((q: string, i: number) => (
                <li key={i} className="text-xs flex gap-1.5" style={{ color: 'rgba(255,255,255,0.45)' }}>
                  <span style={{ color: 'rgba(255,255,255,0.25)' }}>Q:</span> {q}
                </li>
              ))}
            </ul>
          )}
        </BlockRow>
      )}

      {/* CV gap mitigation */}
      {b.cv_match?.mitigation && (
        <BlockRow icon={Brain} title="Gap Mitigation" accent="#ec4899">
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.6)' }}>{b.cv_match.mitigation}</p>
        </BlockRow>
      )}
    </div>
  )
}

// ── Card ─────────────────────────────────────────────────────────────────

function ReviewCard({ app, onApprove, onSkip }: { app: any; onApprove: () => void; onSkip: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const [acting, setActing] = useState(false)
  const analysis = app.deep_analysis

  async function handle(action: 'approve' | 'skip') {
    setActing(true)
    try {
      await api.post(`/applications/${app.id}/${action}`)
      action === 'approve' ? onApprove() : onSkip()
    } catch {
      toast.error('Action failed')
      setActing(false)
    }
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      className="card-3d rounded-2xl overflow-hidden"
    >
      {/* Header row */}
      <div className="p-5">
        <div className="flex items-start gap-4">
          <ScoreBadge score={app.match_score} />

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-white">{app.job?.title}</span>
              {analysis?.archetype && (
                <Pill label={analysis.archetype} color="#a78bfa" />
              )}
              {app.is_top_tier && <Pill label="Top-Tier" color="#fbbf24" />}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <p className="text-sm" style={{ color: 'rgba(255,255,255,0.45)' }}>{app.job?.company}</p>
              {app.job?.remote && <Pill label="Remote" color="#34d399" />}
              <a href={app.job?.url} target="_blank" rel="noopener noreferrer"
                onClick={e => e.stopPropagation()}
                className="ml-auto" style={{ color: 'rgba(255,255,255,0.3)' }}>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>

            {/* Quick verdict */}
            {app.match_explanation && (
              <p className="text-xs mt-2 line-clamp-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
                {app.match_explanation}
              </p>
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-3 mt-4">
          <motion.button
            whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
            disabled={acting}
            onClick={() => handle('approve')}
            className="flex items-center gap-2 flex-1 justify-center py-2.5 rounded-xl text-sm font-semibold transition-all"
            style={{ background: 'rgba(52,211,153,0.12)', border: '1px solid rgba(52,211,153,0.3)', color: '#34d399' }}
          >
            <CheckCircle className="w-4 h-4" />
            Approve & Queue
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
            disabled={acting}
            onClick={() => handle('skip')}
            className="flex items-center gap-2 flex-1 justify-center py-2.5 rounded-xl text-sm font-semibold transition-all"
            style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#f87171' }}
          >
            <XCircle className="w-4 h-4" />
            Skip
          </motion.button>

          {analysis?.blocks && (
            <motion.button
              whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
              onClick={() => setExpanded(v => !v)}
              className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold"
              style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.4)' }}
            >
              {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              Analysis
            </motion.button>
          )}
        </div>
      </div>

      {/* Expandable deep analysis */}
      <AnimatePresence>
        {expanded && analysis && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
              <DeepAnalysisPanel analysis={analysis} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────

export default function ReviewQueuePage() {
  const [queue, setQueue] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const r = await api.get('/applications/review-queue')
      setQueue(r.data)
    } catch {
      toast.error('Failed to load review queue')
    } finally {
      setLoading(false)
    }
  }

  function remove(id: number) {
    setQueue(q => q.filter(a => a.id !== id))
    toast.success('Done')
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <div className="flex items-center gap-4">
          <div className="w-11 h-11 rounded-2xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #f59e0b, #f97316)' }}>
            <AlertTriangle className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Review Queue</h1>
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
              {queue.length} high-confidence match{queue.length !== 1 ? 'es' : ''} awaiting your decision
            </p>
          </div>
        </div>

        {queue.length > 0 && (
          <div className="mt-4 flex gap-3">
            <motion.button
              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={async () => {
                await Promise.all(queue.map(a => api.post(`/applications/${a.id}/approve`)))
                toast.success(`Approved all ${queue.length} applications`)
                setQueue([])
              }}
              className="text-sm px-4 py-2 rounded-xl font-semibold"
              style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.25)', color: '#34d399' }}
            >
              Approve All
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={async () => {
                await Promise.all(queue.map(a => api.post(`/applications/${a.id}/skip`)))
                toast.success('Skipped all')
                setQueue([])
              }}
              className="text-sm px-4 py-2 rounded-xl font-semibold"
              style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#f87171' }}
            >
              Skip All
            </motion.button>
          </div>
        )}
      </motion.div>

      {loading ? (
        <div className="flex flex-col items-center py-20">
          <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
            className="w-10 h-10 rounded-full mb-4"
            style={{ border: '2px solid rgba(255,255,255,0.08)', borderTopColor: '#f59e0b' }} />
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>Loading review queue...</p>
        </div>
      ) : queue.length === 0 ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="card-3d rounded-2xl flex flex-col items-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
            style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)' }}>
            <CheckCircle className="w-8 h-8" style={{ color: '#f59e0b' }} />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Queue is clear</h3>
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
            High-confidence matches will appear here for your approval before applying
          </p>
        </motion.div>
      ) : (
        <div className="space-y-4">
          <AnimatePresence mode="popLayout">
            {queue.map(app => (
              <ReviewCard
                key={app.id}
                app={app}
                onApprove={() => remove(app.id)}
                onSkip={() => remove(app.id)}
              />
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  )
}
