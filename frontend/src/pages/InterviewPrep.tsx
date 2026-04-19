import React, { useEffect, useState } from 'react'
import { resumeApi } from '../api/client'
import api from '../api/client'
import toast from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'
import {
  GraduationCap, Loader2, Star, Building2, DollarSign,
  AlertTriangle, CheckCircle, Code2, MessageSquare, HelpCircle,
  ChevronDown, Sparkles, ClipboardList
} from 'lucide-react'

function QuestionCard({ q, index, type }: { q: any; index: number; type: 'behavioral' | 'technical' }) {
  const [open, setOpen] = useState(false)
  const accent = type === 'behavioral' ? '#a78bfa' : '#60a5fa'
  const accentBg = type === 'behavioral' ? 'rgba(167,139,250,0.08)' : 'rgba(96,165,250,0.08)'
  const accentBorder = type === 'behavioral' ? 'rgba(167,139,250,0.2)' : 'rgba(96,165,250,0.2)'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="rounded-xl overflow-hidden mb-2"
      style={{ border: `1px solid ${accentBorder}`, background: accentBg }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-start gap-3 p-3 text-left"
      >
        <span
          className="text-xs font-bold mt-0.5 flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center"
          style={{ background: accentBg, color: accent, border: `1px solid ${accentBorder}` }}
        >
          {index + 1}
        </span>
        <span className="flex-1 text-sm font-medium text-white">{q.question}</span>
        {q.category && (
          <span className="text-xs px-2 py-0.5 rounded-full flex-shrink-0"
            style={{ background: accentBg, color: accent, border: `1px solid ${accentBorder}` }}>
            {q.category}
          </span>
        )}
        <ChevronDown className={`w-4 h-4 flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          style={{ color: 'rgba(255,255,255,0.3)' }} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 pt-0 space-y-2" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
              {q.why_they_ask && (
                <p className="text-xs pt-2" style={{ color: 'rgba(255,255,255,0.4)' }}>
                  <span style={{ color: accent }}>Why they ask: </span>{q.why_they_ask}
                </p>
              )}
              {q.preparation_tips && (
                <p className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
                  <span style={{ color: accent }}>Tips: </span>{q.preparation_tips}
                </p>
              )}
              {(q.suggested_answer_points || []).length > 0 && (
                <ul className="space-y-1">
                  {q.suggested_answer_points.map((p: string, i: number) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs" style={{ color: 'rgba(255,255,255,0.55)' }}>
                      <CheckCircle className="w-3 h-3 mt-0.5 flex-shrink-0" style={{ color: accent }} />
                      {p}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function InterviewPrepPage() {
  const [resumes, setResumes] = useState<any[]>([])
  const [resumeId, setResumeId] = useState<number | null>(null)
  const [jobTitle, setJobTitle] = useState('Senior Full Stack Engineer')
  const [company, setCompany] = useState('Stripe')
  const [jobDesc, setJobDesc] = useState('')
  const [prep, setPrep] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'intel' | 'behavioral' | 'technical' | 'questions'>('intel')

  useEffect(() => {
    // Pick up query params if navigated from Kanban
    const params = new URLSearchParams(window.location.search)
    if (params.get('company')) setCompany(params.get('company')!)
    if (params.get('title')) setJobTitle(params.get('title')!)

    resumeApi.list().then(r => {
      setResumes(r.data)
      if (r.data.length > 0) setResumeId(r.data[0].id)
    }).catch(() => {})
  }, [])

  async function generate() {
    if (!resumeId) { toast.error('Upload a resume first'); return }
    setLoading(true); setPrep(null)
    try {
      const r = await api.post('/ai/interview-prep', {
        resume_id: resumeId, job_title: jobTitle, company, job_description: jobDesc,
      })
      setPrep(r.data)
      setActiveTab('intel')
    } catch (e: any) { toast.error(e.message) }
    finally { setLoading(false) }
  }

  const ci = prep?.company_intel
  const tabs = [
    { id: 'intel',      label: 'Company Intel',  icon: Building2,     show: !!ci },
    { id: 'behavioral', label: 'Behavioral',      icon: MessageSquare, show: true },
    { id: 'technical',  label: 'Technical',       icon: Code2,         show: true },
    { id: 'questions',  label: 'Ask Them',        icon: HelpCircle,    show: true },
  ] as const

  return (
    <div className="p-8">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-4 mb-6">
        <div className="w-11 h-11 rounded-2xl flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg, #8b5cf6, #a78bfa)' }}>
          <GraduationCap className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Interview Prep</h1>
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
            AI generates behavioral + technical questions, company intel, and salary data
          </p>
        </div>
      </motion.div>

      {/* Input row */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="card-3d rounded-2xl p-5 mb-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-3 mb-3">
          <select value={resumeId || ''} onChange={e => setResumeId(Number(e.target.value))}
            className="input-glass rounded-xl px-3 py-2.5 text-sm">
            {resumes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          <input value={jobTitle} onChange={e => setJobTitle(e.target.value)} placeholder="Job Title"
            className="input-glass rounded-xl px-3 py-2.5 text-sm" />
          <input value={company} onChange={e => setCompany(e.target.value)} placeholder="Company"
            className="input-glass rounded-xl px-3 py-2.5 text-sm" />
          <motion.button onClick={generate} disabled={loading}
            whileHover={{ scale: loading ? 1 : 1.02 }} whileTap={{ scale: loading ? 1 : 0.98 }}
            className="flex items-center justify-center gap-2 py-2.5 rounded-xl font-semibold text-white disabled:opacity-50"
            style={{ background: loading ? 'rgba(139,92,246,0.4)' : 'linear-gradient(135deg, #8b5cf6, #6d28d9)', border: '1px solid rgba(139,92,246,0.3)' }}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {loading ? 'Generating...' : 'Generate Prep'}
          </motion.button>
        </div>
        <textarea value={jobDesc} onChange={e => setJobDesc(e.target.value)} rows={3}
          placeholder="Paste job description (optional, improves quality)"
          className="w-full input-glass rounded-xl px-3 py-2.5 text-sm resize-none" />
      </motion.div>

      {/* Loading state */}
      <AnimatePresence>
        {loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="card-3d rounded-2xl p-12 flex flex-col items-center gap-4">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              className="w-12 h-12 rounded-2xl flex items-center justify-center"
              style={{ background: 'rgba(139,92,246,0.15)', border: '1px solid rgba(139,92,246,0.3)' }}
            >
              <GraduationCap className="w-6 h-6" style={{ color: '#a78bfa' }} />
            </motion.div>
            <div className="text-center">
              <p className="text-white font-semibold">AI is preparing your interview kit</p>
              <p className="text-sm mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
                Analyzing {company || 'company'} culture, generating questions...
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {prep && !loading && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          {/* Tab bar */}
          <div className="flex gap-1 mb-5 p-1 rounded-2xl" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
            {tabs.filter(t => t.show).map(tab => (
              <motion.button key={tab.id} onClick={() => setActiveTab(tab.id)}
                whileTap={{ scale: 0.97 }}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all"
                style={activeTab === tab.id
                  ? { background: 'linear-gradient(135deg, rgba(139,92,246,0.25), rgba(109,40,217,0.15))', color: '#c084fc', border: '1px solid rgba(139,92,246,0.25)' }
                  : { color: 'rgba(255,255,255,0.4)' }}>
                <tab.icon className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{tab.label}</span>
              </motion.button>
            ))}
          </div>

          <AnimatePresence mode="wait">
            {/* Company Intel */}
            {activeTab === 'intel' && ci && (
              <motion.div key="intel" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <div className="card-3d rounded-2xl p-5">
                  <h2 className="flex items-center gap-2 font-semibold text-white mb-3">
                    <Building2 className="w-4 h-4" style={{ color: '#60a5fa' }} /> Overview
                  </h2>
                  <p className="text-sm mb-3" style={{ color: 'rgba(255,255,255,0.6)' }}>{ci.company_overview}</p>
                  <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                    {[['Industry', ci.industry], ['Size', ci.estimated_size], ['Funding', ci.funding_stage]].map(([k, v]) => (
                      <span key={k} className="px-2.5 py-1.5 rounded-xl" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)', color: 'rgba(255,255,255,0.5)' }}>
                        <span style={{ color: 'rgba(255,255,255,0.3)' }}>{k}: </span>{v}
                      </span>
                    ))}
                    <span className="px-2.5 py-1.5 rounded-xl flex items-center gap-1"
                      style={{ background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.15)', color: '#fbbf24' }}>
                      <Star className="w-3 h-3" /> {ci.estimated_rating}/5
                    </span>
                  </div>
                  {ci.salary_range && (
                    <div className="flex items-center gap-2 p-2.5 rounded-xl mb-3"
                      style={{ background: 'rgba(52,211,153,0.07)', border: '1px solid rgba(52,211,153,0.15)' }}>
                      <DollarSign className="w-4 h-4 flex-shrink-0" style={{ color: '#34d399' }} />
                      <span className="text-sm font-semibold" style={{ color: '#34d399' }}>
                        ${(ci.salary_range.low / 1000).toFixed(0)}K – ${(ci.salary_range.high / 1000).toFixed(0)}K
                      </span>
                      <span className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>{ci.salary_range.note}</span>
                    </div>
                  )}
                  {ci.tech_stack && (
                    <div className="flex flex-wrap gap-1">
                      {ci.tech_stack.map((t: string) => (
                        <span key={t} className="text-xs px-2 py-0.5 rounded-full"
                          style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', color: '#93c5fd' }}>{t}</span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="card-3d rounded-2xl p-5">
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <p className="text-xs font-semibold mb-2" style={{ color: '#34d399' }}>Pros</p>
                      {(ci.pros || []).map((p: string, i: number) => (
                        <p key={i} className="flex items-start gap-1.5 text-xs mb-1.5" style={{ color: 'rgba(255,255,255,0.5)' }}>
                          <CheckCircle className="w-3 h-3 mt-0.5 flex-shrink-0" style={{ color: '#34d399' }} /> {p}
                        </p>
                      ))}
                    </div>
                    <div>
                      <p className="text-xs font-semibold mb-2" style={{ color: '#f87171' }}>Cons</p>
                      {(ci.cons || []).map((c: string, i: number) => (
                        <p key={i} className="flex items-start gap-1.5 text-xs mb-1.5" style={{ color: 'rgba(255,255,255,0.5)' }}>
                          <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" style={{ color: '#f87171' }} /> {c}
                        </p>
                      ))}
                    </div>
                  </div>
                  {ci.tips_for_applying && (
                    <p className="text-xs p-3 rounded-xl" style={{ background: 'rgba(251,191,36,0.07)', border: '1px solid rgba(251,191,36,0.15)', color: '#fde68a' }}>
                      <span className="font-semibold">Tip: </span>{ci.tips_for_applying}
                    </p>
                  )}
                </div>
              </motion.div>
            )}

            {/* Behavioral Questions */}
            {activeTab === 'behavioral' && (
              <motion.div key="behavioral" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                <div className="card-3d rounded-2xl p-5">
                  <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" style={{ color: '#a78bfa' }} /> Behavioral Questions
                  </h2>
                  {(prep.behavioral_questions || []).map((q: any, i: number) => (
                    <QuestionCard key={i} q={q} index={i} type="behavioral" />
                  ))}
                </div>
              </motion.div>
            )}

            {/* Technical Questions */}
            {activeTab === 'technical' && (
              <motion.div key="technical" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                <div className="card-3d rounded-2xl p-5">
                  <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
                    <Code2 className="w-4 h-4" style={{ color: '#60a5fa' }} /> Technical Questions
                  </h2>
                  {(prep.technical_questions || []).map((q: any, i: number) => (
                    <QuestionCard key={i} q={q} index={i} type="technical" />
                  ))}
                  {prep.coding_topics && (
                    <div className="mt-4 pt-4" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                      <p className="text-xs mb-2" style={{ color: 'rgba(255,255,255,0.4)' }}>Key Coding Topics</p>
                      <div className="flex flex-wrap gap-1.5">
                        {prep.coding_topics.map((t: string) => (
                          <span key={t} className="text-xs px-2.5 py-1 rounded-full"
                            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)' }}>{t}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}

            {/* Questions to Ask + Checklist */}
            {activeTab === 'questions' && (
              <motion.div key="questions" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <div className="card-3d rounded-2xl p-5">
                  <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
                    <HelpCircle className="w-4 h-4" style={{ color: '#34d399' }} /> Questions to Ask Them
                  </h2>
                  <ul className="space-y-2">
                    {(prep.questions_to_ask_them || []).map((q: string, i: number) => (
                      <motion.li key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
                        className="flex items-start gap-2 text-sm p-2.5 rounded-xl"
                        style={{ background: 'rgba(52,211,153,0.05)', border: '1px solid rgba(52,211,153,0.1)', color: 'rgba(255,255,255,0.65)' }}>
                        <span style={{ color: '#34d399' }}>?</span> {q}
                      </motion.li>
                    ))}
                  </ul>
                </div>
                <div className="card-3d rounded-2xl p-5">
                  <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
                    <ClipboardList className="w-4 h-4" style={{ color: '#fbbf24' }} /> Prep Checklist
                  </h2>
                  <ul className="space-y-2">
                    {(prep.preparation_checklist || []).map((item: string, i: number) => (
                      <ChecklistItem key={i} item={item} index={i} />
                    ))}
                  </ul>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </div>
  )
}

function ChecklistItem({ item, index }: { item: string; index: number }) {
  const [checked, setChecked] = useState(false)
  return (
    <motion.li
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      onClick={() => setChecked(!checked)}
      className="flex items-start gap-2.5 text-sm p-2.5 rounded-xl cursor-pointer transition-all"
      style={{
        background: checked ? 'rgba(251,191,36,0.07)' : 'rgba(255,255,255,0.02)',
        border: `1px solid ${checked ? 'rgba(251,191,36,0.2)' : 'rgba(255,255,255,0.06)'}`,
        color: checked ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.6)',
        textDecoration: checked ? 'line-through' : 'none',
      }}
    >
      <div className="w-4 h-4 rounded flex-shrink-0 mt-0.5 flex items-center justify-center transition-all"
        style={{ background: checked ? '#fbbf24' : 'rgba(255,255,255,0.06)', border: `1px solid ${checked ? '#fbbf24' : 'rgba(255,255,255,0.12)'}` }}>
        {checked && <CheckCircle className="w-3 h-3 text-black" />}
      </div>
      {item}
    </motion.li>
  )
}
