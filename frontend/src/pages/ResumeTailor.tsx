import React, { useEffect, useState } from 'react'
import { resumeApi } from '../api/client'
import api from '../api/client'
import toast from 'react-hot-toast'
import { FileText, Loader2, Target, ArrowRight, CheckCircle, XCircle, AlertTriangle, GitCompare, ChevronDown, ChevronUp } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

function ScoreRing({ score, label }: { score: number; label: string }) {
  const r = 28
  const circ = 2 * Math.PI * r
  const dash = (score / 100) * circ
  const color = score >= 80 ? '#34d399' : score >= 60 ? '#fbbf24' : '#f87171'
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative flex items-center justify-center w-16 h-16">
        <svg width="64" height="64" className="-rotate-90">
          <circle cx="32" cy="32" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
          <motion.circle
            cx="32" cy="32" r={r} fill="none"
            stroke={color} strokeWidth="5"
            strokeDasharray={circ}
            initial={{ strokeDashoffset: circ }}
            animate={{ strokeDashoffset: circ - dash }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
            strokeLinecap="round"
          />
        </svg>
        <span className="absolute text-base font-bold" style={{ color }}>{score}</span>
      </div>
      <span className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>{label}</span>
    </div>
  )
}

function DiffBullet({ original, tailored }: { original: string; tailored: string }) {
  const [show, setShow] = useState(false)
  const changed = original !== tailored
  return (
    <div className="rounded-xl overflow-hidden mb-2" style={{ border: '1px solid rgba(255,255,255,0.07)' }}>
      {/* Tailored version */}
      <div className="p-3" style={{ background: 'rgba(52,211,153,0.05)' }}>
        <div className="flex items-start gap-2">
          <span className="text-xs font-bold mt-0.5 flex-shrink-0" style={{ color: '#34d399' }}>NEW</span>
          <p className="text-sm" style={{ color: '#f1f5f9' }}>{tailored}</p>
        </div>
      </div>
      {/* Show original toggle */}
      {changed && (
        <>
          <button
            onClick={() => setShow(!show)}
            className="w-full flex items-center gap-1.5 px-3 py-1.5 text-xs transition-colors"
            style={{
              background: 'rgba(255,255,255,0.02)',
              borderTop: '1px solid rgba(255,255,255,0.05)',
              color: 'rgba(255,255,255,0.3)',
            }}
          >
            {show ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {show ? 'Hide original' : 'Show original'}
          </button>
          <AnimatePresence>
            {show && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="p-3" style={{ background: 'rgba(248,113,113,0.04)', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                  <div className="flex items-start gap-2">
                    <span className="text-xs font-bold mt-0.5 flex-shrink-0" style={{ color: '#f87171' }}>OLD</span>
                    <p className="text-sm line-through" style={{ color: 'rgba(255,255,255,0.35)' }}>{original}</p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </div>
  )
}

export default function ResumeTailorPage() {
  const [resumes, setResumes] = useState<any[]>([])
  const [resumeId, setResumeId] = useState<number | null>(null)
  const [jobTitle, setJobTitle] = useState('Senior Full Stack Engineer')
  const [company, setCompany] = useState('')
  const [jobDesc, setJobDesc] = useState('')
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'ats' | 'diff'>('ats')

  useEffect(() => {
    resumeApi.list().then(r => {
      setResumes(r.data)
      if (r.data.length > 0) setResumeId(r.data[0].id)
    }).catch(() => {})
  }, [])

  async function analyze() {
    if (!resumeId || !jobDesc) { toast.error('Select resume and paste job description'); return }
    setLoading(true); setResult(null)
    try {
      const r = await api.post('/ai/tailor-resume', {
        resume_id: resumeId, job_description: jobDesc, job_title: jobTitle, company,
      })
      setResult(r.data)
      setActiveTab('ats')
    } catch (e: any) { toast.error(e.message) }
    finally { setLoading(false) }
  }

  const ats = result?.ats_score || {}
  const tailored = result?.tailored_resume || {}
  const originalResume = resumes.find(r => r.id === resumeId)
  const originalExp: any[] = originalResume?.parsed_data?.experience || []

  // Build diff pairs: match tailored experience bullets to original
  const tailoredExp: any[] = tailored?.experience || []

  return (
    <div className="p-8">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-4 mb-2">
        <div className="w-11 h-11 rounded-2xl flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg, #f97316, #ea580c)' }}>
          <Target className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Resume Tailor & ATS Scanner</h1>
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
            AI rewrites your resume bullets for each specific job and scores ATS keyword match
          </p>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        {/* Input panel */}
        <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <select value={resumeId || ''} onChange={e => setResumeId(Number(e.target.value))}
              className="input-glass rounded-xl px-3 py-2.5 text-sm">
              {resumes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
            <input value={jobTitle} onChange={e => setJobTitle(e.target.value)} placeholder="Job Title"
              className="input-glass rounded-xl px-3 py-2.5 text-sm" />
          </div>
          <input value={company} onChange={e => setCompany(e.target.value)} placeholder="Company (optional)"
            className="w-full input-glass rounded-xl px-3 py-2.5 text-sm" />
          <textarea value={jobDesc} onChange={e => setJobDesc(e.target.value)} rows={12}
            placeholder="Paste the full job description here..."
            className="w-full input-glass rounded-xl px-3 py-2.5 text-sm resize-none" />
          <motion.button onClick={analyze} disabled={loading}
            whileHover={{ scale: loading ? 1 : 1.01 }} whileTap={{ scale: loading ? 1 : 0.99 }}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-white disabled:opacity-50"
            style={{ background: loading ? 'rgba(249,115,22,0.4)' : 'linear-gradient(135deg, #f97316, #ea580c)', border: '1px solid rgba(249,115,22,0.3)' }}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Target className="w-4 h-4" />}
            {loading ? 'Analyzing & Tailoring...' : 'Scan ATS + Tailor Resume'}
          </motion.button>
        </motion.div>

        {/* Results panel */}
        <motion.div initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.15 }}>
          {result ? (
            <div>
              {/* Tab bar */}
              <div className="flex gap-1 mb-4 p-1 rounded-xl" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
                {([
                  { id: 'ats', label: 'ATS Score', icon: Target },
                  { id: 'diff', label: 'Bullet Diff', icon: GitCompare },
                ] as const).map(tab => (
                  <motion.button key={tab.id} onClick={() => setActiveTab(tab.id)}
                    whileTap={{ scale: 0.97 }}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm font-medium transition-all"
                    style={activeTab === tab.id
                      ? { background: 'linear-gradient(135deg, rgba(249,115,22,0.25), rgba(234,88,12,0.15))', color: '#fb923c', border: '1px solid rgba(249,115,22,0.25)' }
                      : { color: 'rgba(255,255,255,0.4)' }}>
                    <tab.icon className="w-3.5 h-3.5" />
                    {tab.label}
                  </motion.button>
                ))}
              </div>

              <AnimatePresence mode="wait">
                {activeTab === 'ats' ? (
                  <motion.div key="ats" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} className="space-y-4">
                    {/* ATS Score card */}
                    <div className="card-3d rounded-2xl p-5">
                      <div className="flex items-center justify-between mb-4">
                        <h2 className="font-semibold text-white">ATS Compatibility</h2>
                        <ScoreRing score={ats.ats_score || 0} label="ATS Score" />
                      </div>
                      <div className="mb-3">
                        <div className="flex justify-between text-xs mb-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
                          <span>Keyword Density</span>
                          <span>{Math.round((ats.keyword_density || 0) * 100)}%</span>
                        </div>
                        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                          <motion.div className="h-full rounded-full" style={{ background: '#3b82f6' }}
                            initial={{ width: 0 }} animate={{ width: `${(ats.keyword_density || 0) * 100}%` }}
                            transition={{ duration: 1, ease: 'easeOut' }} />
                        </div>
                      </div>
                      {(ats.matched_keywords || []).length > 0 && (
                        <div className="mb-3">
                          <p className="text-xs mb-1.5" style={{ color: 'rgba(255,255,255,0.4)' }}>Matched</p>
                          <div className="flex flex-wrap gap-1.5">
                            {ats.matched_keywords.map((k: string) => (
                              <span key={k} className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full"
                                style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.2)', color: '#34d399' }}>
                                <CheckCircle className="w-2.5 h-2.5" /> {k}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {(ats.missing_critical || []).length > 0 && (
                        <div className="mb-3">
                          <p className="text-xs mb-1.5" style={{ color: '#f87171' }}>Missing Critical</p>
                          <div className="flex flex-wrap gap-1.5">
                            {ats.missing_critical.map((k: string) => (
                              <span key={k} className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full"
                                style={{ background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.2)', color: '#f87171' }}>
                                <XCircle className="w-2.5 h-2.5" /> {k}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {(ats.missing_nice_to_have || []).length > 0 && (
                        <div className="mb-3">
                          <p className="text-xs mb-1.5" style={{ color: '#fbbf24' }}>Missing Nice-to-Have</p>
                          <div className="flex flex-wrap gap-1.5">
                            {ats.missing_nice_to_have.map((k: string) => (
                              <span key={k} className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full"
                                style={{ background: 'rgba(251,191,36,0.1)', border: '1px solid rgba(251,191,36,0.2)', color: '#fbbf24' }}>
                                <AlertTriangle className="w-2.5 h-2.5" /> {k}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {(ats.suggestions || []).length > 0 && (
                        <ul className="space-y-1.5 mt-3 pt-3" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                          {ats.suggestions.map((s: string, i: number) => (
                            <li key={i} className="flex items-start gap-2 text-xs" style={{ color: 'rgba(255,255,255,0.6)' }}>
                              <ArrowRight className="w-3 h-3 mt-0.5 flex-shrink-0" style={{ color: '#60a5fa' }} /> {s}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    {/* Top keywords */}
                    {(result.job_keywords || []).length > 0 && (
                      <div className="card-3d rounded-2xl p-4">
                        <h2 className="font-semibold text-white mb-3 text-sm">Top Keywords This Job Wants</h2>
                        <div className="flex flex-wrap gap-1.5">
                          {result.job_keywords.map((k: string, i: number) => (
                            <span key={k} className="text-xs px-2 py-0.5 rounded-full"
                              style={i < 5
                                ? { background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.2)', color: '#f87171' }
                                : i < 10
                                ? { background: 'rgba(251,191,36,0.1)', border: '1px solid rgba(251,191,36,0.2)', color: '#fbbf24' }
                                : { background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.4)' }}>
                              #{i + 1} {k}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </motion.div>
                ) : (
                  <motion.div key="diff" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                    <div className="card-3d rounded-2xl p-5">
                      <div className="flex items-center gap-2 mb-4">
                        <GitCompare className="w-4 h-4" style={{ color: '#fb923c' }} />
                        <h2 className="font-semibold text-white">Tailored vs Original</h2>
                      </div>
                      {tailoredExp.length > 0 ? (
                        tailoredExp.map((exp: any, ei: number) => {
                          const orig = originalExp[ei]
                          const tailoredBullets: string[] = exp.bullets || exp.achievements || []
                          const origBullets: string[] = orig?.bullets || orig?.achievements || []
                          return (
                            <div key={ei} className="mb-5">
                              <p className="text-xs font-semibold mb-2 flex items-center gap-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
                                <span className="w-1.5 h-1.5 rounded-full bg-orange-400 inline-block" />
                                {exp.company || exp.title}
                              </p>
                              {tailoredBullets.map((bullet: string, bi: number) => (
                                <DiffBullet key={bi} original={origBullets[bi] || bullet} tailored={bullet} />
                              ))}
                            </div>
                          )
                        })
                      ) : (
                        <p className="text-sm text-center py-8" style={{ color: 'rgba(255,255,255,0.3)' }}>
                          No bullet-level diff available for this resume format
                        </p>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="card-3d rounded-2xl flex flex-col items-center justify-center h-full text-center py-20"
            >
              <motion.div
                animate={{ y: [0, -6, 0] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
                style={{ background: 'rgba(249,115,22,0.1)', border: '1px solid rgba(249,115,22,0.2)' }}
              >
                <FileText className="w-8 h-8" style={{ color: '#fb923c' }} />
              </motion.div>
              <p className="text-sm font-medium text-white mb-1">Paste a job description and click Scan</p>
              <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
                AI will score your ATS match and rewrite your bullets
              </p>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
