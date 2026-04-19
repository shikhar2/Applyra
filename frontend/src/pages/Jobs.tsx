import React, { useEffect, useState } from 'react'
import { jobApi } from '../api/client'
import toast from 'react-hot-toast'
import { ExternalLink, MapPin, DollarSign, Zap, Search, Briefcase, ChevronLeft, ChevronRight, Bell, BellOff, Bookmark, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const SAVED_KEY = 'applyra_saved_searches'
const ALERT_KEY = 'applyra_job_alerts'

interface SavedSearch { id: string; label: string; source: string; remote: boolean; search: string; savedAt: number; newCount: number }

function loadSaved(): SavedSearch[] {
  try { return JSON.parse(localStorage.getItem(SAVED_KEY) || '[]') } catch { return [] }
}
function saveSearces(list: SavedSearch[]) { localStorage.setItem(SAVED_KEY, JSON.stringify(list)) }
function loadAlerts(): Record<string, number> {
  try { return JSON.parse(localStorage.getItem(ALERT_KEY) || '{}') } catch { return {} }
}

const SOURCE_CONFIG: Record<string, { color: string; bg: string; border: string }> = {
  linkedin:  { color: '#93c5fd', bg: 'rgba(59,130,246,0.12)',  border: 'rgba(59,130,246,0.25)' },
  indeed:    { color: '#c4b5fd', bg: 'rgba(139,92,246,0.12)',  border: 'rgba(139,92,246,0.25)' },
  glassdoor: { color: '#6ee7b7', bg: 'rgba(52,211,153,0.12)',  border: 'rgba(52,211,153,0.25)' },
  naukri:    { color: '#fdba74', bg: 'rgba(251,146,60,0.12)',   border: 'rgba(251,146,60,0.25)' },
  dice:      { color: '#67e8f9', bg: 'rgba(34,211,238,0.12)',  border: 'rgba(34,211,238,0.25)' },
  wellfound: { color: '#f9a8d4', bg: 'rgba(244,114,182,0.12)', border: 'rgba(244,114,182,0.25)' },
}

function fmtSalary(min?: number, max?: number) {
  if (!min && !max) return null
  const k = (v: number) => `$${Math.round(v / 1000)}K`
  if (min && max && min !== max) return `${k(min)} – ${k(max)}`
  return k((min || max)!)
}

function MatchScoreBadge({ score }: { score?: number }) {
  if (score == null) return null
  const pct = Math.round(score * 100)
  const color = pct >= 85 ? '#34d399' : pct >= 70 ? '#fbbf24' : '#f87171'
  const bg    = pct >= 85 ? 'rgba(52,211,153,0.12)' : pct >= 70 ? 'rgba(251,191,36,0.12)' : 'rgba(248,113,113,0.12)'
  const border = pct >= 85 ? 'rgba(52,211,153,0.3)' : pct >= 70 ? 'rgba(251,191,36,0.3)' : 'rgba(248,113,113,0.3)'

  return (
    <div
      className="relative flex items-center justify-center w-10 h-10 rounded-full flex-shrink-0"
      style={{ background: bg, border: `2px solid ${border}` }}
    >
      <span className="text-xs font-bold" style={{ color }}>{pct}%</span>
    </div>
  )
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [source, setSource] = useState('')
  const [remoteOnly, setRemoteOnly] = useState(false)
  const [page, setPage] = useState(0)
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>(loadSaved)
  const [showSaved, setShowSaved] = useState(false)
  const PAGE_SIZE = 50

  useEffect(() => { load() }, [source, remoteOnly, page])

  async function load() {
    setLoading(true)
    try {
      const params: any = { limit: PAGE_SIZE, offset: page * PAGE_SIZE }
      if (source) params.source = source
      if (remoteOnly) params.remote = true
      if (search) params.search = search
      const r = await jobApi.list(params)
      setJobs(r.data)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  function saveCurrentSearch() {
    const label = [search, source, remoteOnly ? 'remote' : ''].filter(Boolean).join(' · ') || 'All jobs'
    const id = Date.now().toString()
    const entry: SavedSearch = { id, label, source, remote: remoteOnly, search, savedAt: Date.now(), newCount: jobs.length }
    const updated = [entry, ...savedSearches.slice(0, 4)]
    setSavedSearches(updated)
    saveSearces(updated)
    toast.success('Search saved! You\'ll see new matches highlighted.')
  }

  function removeSaved(id: string) {
    const updated = savedSearches.filter(s => s.id !== id)
    setSavedSearches(updated)
    saveSearces(updated)
  }

  function applySearch(s: SavedSearch) {
    setSearch(s.search)
    setSource(s.source)
    setRemoteOnly(s.remote)
    setPage(0)
    setShowSaved(false)
  }

  const totalAlerts = savedSearches.reduce((n, s) => n + (s.newCount > 0 ? 1 : 0), 0)
  const srcConfig = source ? SOURCE_CONFIG[source] : null

  return (
    <div className="p-8">
      {/* Page header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex items-center gap-4 mb-2"
      >
        <div
          className="w-11 h-11 rounded-2xl flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg, #6366f1, #a78bfa)' }}
        >
          <Briefcase className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Jobs Found</h1>
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
            All jobs discovered by the scrapers
          </p>
        </div>
      </motion.div>

      {/* Saved Searches */}
      {savedSearches.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Bell className="w-3.5 h-3.5" style={{ color: '#fbbf24' }} />
            <span className="text-xs font-semibold" style={{ color: 'rgba(255,255,255,0.5)' }}>Saved Searches</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {savedSearches.map(s => (
              <motion.button key={s.id} onClick={() => applySearch(s)}
                whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }}
                className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-xl"
                style={{ background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)', color: '#fbbf24' }}
              >
                <Bookmark className="w-3 h-3" />
                {s.label}
                <span onClick={e => { e.stopPropagation(); removeSaved(s.id) }}
                  className="ml-1 opacity-50 hover:opacity-100 transition-opacity">
                  <X className="w-3 h-3" />
                </span>
              </motion.button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.4 }}
        className="card-3d rounded-2xl p-4 mb-5 flex flex-wrap gap-3 items-center"
      >
        <div
          className="flex items-center gap-2 rounded-xl px-3 py-2.5 flex-1 min-w-48"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.10)',
          }}
        >
          <Search className="w-4 h-4 flex-shrink-0" style={{ color: 'rgba(255,255,255,0.3)' }} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && load()}
            placeholder="Search title or company..."
            className="bg-transparent text-sm text-white outline-none w-full"
            style={{ color: '#f1f5f9' }}
          />
        </div>

        <select
          value={source}
          onChange={(e) => setSource(e.target.value)}
          className="input-glass rounded-xl px-3 py-2.5 text-sm"
          style={srcConfig ? { color: srcConfig.color } : {}}
        >
          <option value="">All sources</option>
          <option value="linkedin">LinkedIn</option>
          <option value="indeed">Indeed</option>
          <option value="glassdoor">Glassdoor</option>
          <option value="naukri">Naukri</option>
          <option value="dice">Dice</option>
          <option value="wellfound">Wellfound</option>
        </select>

        <label className="flex items-center gap-2.5 cursor-pointer">
          <div
            onClick={() => setRemoteOnly(!remoteOnly)}
            className="relative w-9 h-5 rounded-full transition-all cursor-pointer"
            style={{
              background: remoteOnly ? 'linear-gradient(135deg, #3b82f6, #6366f1)' : 'rgba(255,255,255,0.1)',
              border: '1px solid rgba(255,255,255,0.15)',
            }}
          >
            <motion.div
              animate={{ x: remoteOnly ? 16 : 2 }}
              transition={{ type: 'spring', stiffness: 500, damping: 30 }}
              className="absolute top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow"
            />
          </div>
          <span className="text-sm" style={{ color: 'rgba(255,255,255,0.6)' }}>Remote only</span>
          <input type="checkbox" checked={remoteOnly} onChange={(e) => setRemoteOnly(e.target.checked)} className="sr-only" />
        </label>

        <motion.button onClick={saveCurrentSearch} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-xl font-medium"
          style={{ background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)', color: '#fbbf24' }}
        >
          <Bell className="w-3.5 h-3.5" /> Save Search
        </motion.button>
      </motion.div>

      {/* Content */}
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-20"
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
              className="w-10 h-10 rounded-full mb-4"
              style={{
                border: '2px solid rgba(255,255,255,0.08)',
                borderTopColor: '#60a5fa',
              }}
            />
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>Loading jobs...</p>
          </motion.div>
        ) : jobs.length === 0 ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="card-3d rounded-2xl flex flex-col items-center justify-center py-20 text-center"
          >
            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
              style={{ background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.2)' }}
            >
              <Search className="w-8 h-8" style={{ color: '#a78bfa' }} />
            </motion.div>
            <h3 className="text-lg font-semibold text-white mb-2">No jobs found</h3>
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Run a search from the Dashboard to discover jobs
            </p>
          </motion.div>
        ) : (
          <motion.div
            key="list"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="space-y-2">
              {jobs.map((job, i) => {
                const salary = fmtSalary(job.salary_min, job.salary_max)
                const src = SOURCE_CONFIG[job.source]
                return (
                  <motion.div
                    key={job.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03, duration: 0.25 }}
                    className="card-3d rounded-2xl p-4 flex items-center justify-between gap-4"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      {/* Match score ring */}
                      <MatchScoreBadge score={job.match_score} />

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-white truncate">{job.title}</span>
                          {job.easy_apply && (
                            <span
                              className="flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full"
                              style={{
                                background: 'rgba(251,191,36,0.12)',
                                border: '1px solid rgba(251,191,36,0.3)',
                                color: '#fbbf24',
                              }}
                            >
                              <Zap className="w-2.5 h-2.5" /> Easy Apply
                            </span>
                          )}
                          {src && (
                            <span
                              className="text-xs font-medium px-2 py-0.5 rounded-full"
                              style={{
                                background: src.bg,
                                border: `1px solid ${src.border}`,
                                color: src.color,
                              }}
                            >
                              {job.source}
                            </span>
                          )}
                          {!src && job.source && (
                            <span
                              className="text-xs font-medium px-2 py-0.5 rounded-full"
                              style={{
                                background: 'rgba(255,255,255,0.06)',
                                border: '1px solid rgba(255,255,255,0.12)',
                                color: 'rgba(255,255,255,0.5)',
                              }}
                            >
                              {job.source}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-3 mt-1 flex-wrap">
                          <span className="text-sm" style={{ color: 'rgba(255,255,255,0.5)' }}>
                            {job.company}
                          </span>
                          {job.location && (
                            <span className="flex items-center gap-1 text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
                              <MapPin className="w-3 h-3" /> {job.location}
                            </span>
                          )}
                          {salary && (
                            <span className="flex items-center gap-1 text-sm font-medium" style={{ color: '#34d399' }}>
                              <DollarSign className="w-3 h-3" /> {salary}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <motion.a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      whileHover={{ scale: 1.15 }}
                      whileTap={{ scale: 0.9 }}
                      className="p-2 rounded-xl flex-shrink-0 transition-colors"
                      style={{
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.08)',
                        color: 'rgba(255,255,255,0.4)',
                      }}
                    >
                      <ExternalLink className="w-4 h-4" />
                    </motion.a>
                  </motion.div>
                )
              })}
            </div>

            {/* Pagination */}
            <div className="flex items-center gap-3 mt-5">
              <motion.button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="flex items-center gap-1.5 text-sm px-3 py-2 rounded-xl disabled:opacity-30 font-medium transition-colors"
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.10)',
                  color: 'rgba(255,255,255,0.6)',
                }}
              >
                <ChevronLeft className="w-4 h-4" /> Prev
              </motion.button>
              <span
                className="text-sm px-3 py-2 rounded-xl"
                style={{
                  background: 'rgba(99,102,241,0.12)',
                  border: '1px solid rgba(99,102,241,0.2)',
                  color: '#a78bfa',
                }}
              >
                Page {page + 1}
              </span>
              <motion.button
                onClick={() => setPage(page + 1)}
                disabled={jobs.length < PAGE_SIZE}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="flex items-center gap-1.5 text-sm px-3 py-2 rounded-xl disabled:opacity-30 font-medium transition-colors"
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.10)',
                  color: 'rgba(255,255,255,0.6)',
                }}
              >
                Next <ChevronRight className="w-4 h-4" />
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
