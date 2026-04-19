import React, { useEffect, useRef, useState } from 'react'
import { statsApi, automationApi, profileApi, resumeApi } from '../api/client'
import api from '../api/client'
import toast from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../store/useStore'
import {
  Briefcase, Send, TrendingUp, Clock,
  Play, AlertCircle, CheckCircle, Loader2, Globe,
  Terminal, Zap, ChevronRight, Activity, FileText
} from 'lucide-react'

interface Scraper { id: string; name: string; description: string; region: string; requires_login: boolean; easy_apply: boolean; type: string }

const STAT_CONFIGS = [
  { key: 'total_jobs_discovered', label: 'Jobs Found',   icon: Briefcase, color: 'var(--accent-primary)', gradient: 'linear-gradient(135deg, #4f46e5, #6366f1)' },
  { key: 'applied',               label: 'Applied',      icon: Send,       color: '#10b981', gradient: 'linear-gradient(135deg, #059669, #10b981)' },
  { key: 'pending',               label: 'Pending',      icon: Clock,      color: '#f59e0b', gradient: 'linear-gradient(135deg, #d97706, #f59e0b)' },
  { key: 'interviews',            label: 'Interviews',   icon: TrendingUp, color: '#8b5cf6', gradient: 'linear-gradient(135deg, #7c3aed, #8b5cf6)' },
]

function StatCard({ label, value, icon: Icon, color, gradient, index }: any) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="glass rounded-2xl p-6 relative overflow-hidden group"
    >
      <div className="absolute top-0 right-0 p-3 opacity-[0.05] group-hover:scale-110 transition-transform">
        <Icon className="w-16 h-16" style={{ color }} />
      </div>
      <div className="flex items-start justify-between relative z-10">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>{label}</p>
          <motion.p
            key={value}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="text-4xl font-extrabold tracking-tight"
            style={{ color: 'var(--text-primary)' }}
          >
            {value ?? '0'}
          </motion.p>
        </div>
        <div className="w-12 h-12 rounded-xl flex items-center justify-center shadow-lg" style={{ background: gradient }}>
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
      <div className="mt-4 flex items-center gap-1.5">
        <div className="flex-1 h-1 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: '70%' }}
            className="h-full rounded-full"
            style={{ background: color }}
          />
        </div>
        <span className="text-[10px] font-bold" style={{ color: 'var(--text-muted)' }}>70% goal</span>
      </div>
    </motion.div>
  )
}

const REGION_STYLE: Record<string, { bg: string; text: string; border: string }> = {
  Global: { bg: 'rgba(59,130,246,0.1)', text: '#3b82f6', border: 'rgba(59,130,246,0.2)' },
  USA:    { bg: 'rgba(139,92,246,0.1)', text: '#8b5cf6', border: 'rgba(139,92,246,0.2)' },
  India:  { bg: 'rgba(249,115,22,0.1)', text: '#f97316', border: 'rgba(249,115,22,0.2)' },
}

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null)
  const [health, setHealth] = useState<any>(null)
  const [resumes, setResumes] = useState<any[]>([])
  const [profiles, setProfiles] = useState<any[]>([])
  const [scrapers, setScrapers] = useState<Scraper[]>([])
  
  // Use global store state
  const running = useStore(state => state.isRunning)
  const logs = useStore(state => state.logs)
  const setRunning = useStore(state => state.setIsRunning)
  const setLogs = useStore(state => state.setLogs)
  const setRunStatsGlobal = useStore(state => state.setRunStats)

  const [selectedResume, setSelectedResume] = useState<number | null>(null)
  const [selectedProfile, setSelectedProfile] = useState<number | null>(null)
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set(['linkedin', 'indeed', 'dice', 'wellfound']))
  const [dryRun, setDryRun] = useState(true)
  
  const logEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => { loadData(); const t = setInterval(loadData, 30000); return () => clearInterval(t) }, [])
  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [logs])

  async function loadData() {
    try {
      const [s, h, r, p, sc] = await Promise.all([statsApi.get(), statsApi.health(), resumeApi.list(), profileApi.list(), api.get('/scrapers')])
      setStats(s.data); setHealth(h.data); setResumes(r.data); setProfiles(p.data); setScrapers(sc.data)
      if (r.data.length > 0 && !selectedResume) setSelectedResume(r.data[0].id)
      if (p.data.length > 0 && !selectedProfile) setSelectedProfile(p.data[0].id)
    } catch { /* silent */ }
  }

  function toggleSource(id: string) {
    setSelectedSources(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })
  }

  async function handleRun() {
    if (!selectedResume || !selectedProfile) { toast.error('Select a resume and profile first'); return }
    if (selectedSources.size === 0) { toast.error('Select at least one job source'); return }
    setRunning(true); setLogs([]); setRunStatsGlobal(null)
    try {
      await automationApi.runSearch({ profile_id: selectedProfile, resume_id: selectedResume, sources: Array.from(selectedSources), dry_run: dryRun })
      toast.success(dryRun ? 'Search started — dry run mode' : 'Search started — LIVE mode!')
    } catch (e: any) { toast.error(e.message); setRunning(false) }
  }

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
        <div className="flex items-center gap-4 mb-2">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center btn-primary">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight" style={{ color: 'var(--text-primary)' }}>Command Center</h1>
            <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Automate your career growth with precision AI.</p>
          </div>
        </div>
      </motion.div>

      {/* Health Banner */}
      <AnimatePresence>
        {health && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="p-1 rounded-2xl glass"
          >
            <div className={`px-4 py-3 rounded-xl flex items-center gap-3 text-sm font-bold ${health.auto_apply_enabled ? 'text-emerald-500 bg-emerald-500/5' : 'text-amber-500 bg-amber-500/5'}`}>
              <Zap className="w-4 h-4 animate-pulse" />
              <span>
                {health.auto_apply_enabled
                  ? `SYSTEM LIVE · ${health.max_apps_per_day} apps/day · AI: ${health.ai_provider}`
                  : `SAFE MODE ACTIVE · AI: ${health.ai_provider} · Applications will be simulated only.`}
              </span>
              <div className="ml-auto flex items-center gap-2 text-[10px] uppercase tracking-widest px-2 py-1 rounded-md bg-white/10 dark:bg-black/10">
                <span className="w-1.5 h-1.5 rounded-full bg-current animate-ping" />
                Network Ready
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {STAT_CONFIGS.map(({ key, ...cfg }, i) => (
          <StatCard key={key} index={i} value={stats?.[key]} {...cfg} />
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Left: Control Panel */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          className="xl:col-span-2 glass rounded-3xl p-8"
        >
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-500 border border-indigo-500/20">
                <Play className="w-5 h-5" />
              </div>
              <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Execution Engine</h2>
            </div>
            <div className="flex bg-slate-100 dark:bg-slate-900 rounded-xl p-1">
              {[{ v: true, l: 'Dry Run' }, { v: false, l: 'Live' }].map(o => (
                <button
                  key={String(o.v)}
                  onClick={() => setDryRun(o.v)}
                  className={`px-4 py-1.5 text-xs font-bold rounded-lg transition-all ${dryRun === o.v ? 'bg-white dark:bg-slate-800 shadow-sm text-indigo-500' : 'text-slate-400'}`}
                >
                  {o.l}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {[
              { label: 'Select Resume', value: selectedResume, onChange: setSelectedResume, options: resumes, icon: FileText },
              { label: 'Select Profile', value: selectedProfile, onChange: setSelectedProfile, options: profiles, icon: Briefcase },
            ].map(f => (
              <div key={f.label} className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest opacity-40 ml-1">{f.label}</label>
                <div className="relative group">
                  <f.icon className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-indigo-500 opacity-50" />
                  <select
                    value={f.value || ''}
                    onChange={(e) => f.onChange(Number(e.target.value))}
                    className="w-full input-glass rounded-2xl pl-11 pr-4 py-3.5 text-sm font-semibold appearance-none"
                  >
                    <option value="">Choose {f.label.split(' ')[1]}</option>
                    {f.options.map((o: any) => <option key={o.id} value={o.id}>{o.name}</option>)}
                  </select>
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-3 mb-8 text-secondary">
             <div className="flex items-center justify-between ml-1">
               <label className="text-xs font-bold uppercase tracking-widest opacity-40">Job Sources</label>
               {selectedProfile && profiles.find(p => p.id === selectedProfile)?.target_locations?.length > 0 && (
                 <span className="text-[10px] opacity-40 flex items-center gap-1">
                   <Globe className="w-3 h-3" />
                   searching: {profiles.find(p => p.id === selectedProfile)?.target_locations?.join(', ')}
                 </span>
               )}
             </div>
             <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
               {scrapers.map(sc => {
                 const selected = selectedSources.has(sc.id)
                 const activeProfile = profiles.find(p => p.id === selectedProfile)
                 const locations: string[] = activeProfile?.target_locations || []
                 const locationLabel = locations.length > 0
                   ? locations.slice(0, 2).join(', ') + (locations.length > 2 ? ` +${locations.length - 2}` : '')
                   : sc.region
                 return (
                   <button
                    key={sc.id}
                    onClick={() => toggleSource(sc.id)}
                    className={`p-3 rounded-2xl text-center border-2 transition-all ${
                      selected ? 'border-indigo-500 bg-indigo-500/5 shadow-inner shadow-indigo-500/10' : 'border-transparent bg-slate-100 dark:bg-slate-900 opacity-50'
                    }`}
                   >
                     <p className={`text-xs font-bold ${selected ? 'text-indigo-500' : ''}`}>{sc.name}</p>
                     <p className="text-[9px] uppercase tracking-tighter opacity-50">{locationLabel}</p>
                   </button>
                 )
               })}
             </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-6">
            <button
              onClick={handleRun}
              disabled={running || !selectedResume || !selectedProfile}
              className="w-full sm:w-auto btn-primary px-10 py-4 rounded-2xl flex items-center justify-center gap-3 disabled:opacity-30 ripple-button"
            >
              {running ? <Loader2 className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
              <span className="text-lg font-bold">{running ? 'AI Engine Running...' : 'Initiate Search'}</span>
            </button>
            <div className="text-sm font-medium opacity-60 flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${dryRun ? 'bg-amber-400' : 'bg-red-400'} animate-pulse`} />
              {dryRun ? 'Safety mode: No real logs will be filed.' : 'Live mode: Proceed with caution.'}
            </div>
          </div>
        </motion.div>

        {/* Right: Console */}
        <div className="space-y-6">
           <div className="glass rounded-3xl p-6 h-full flex flex-col">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-red-400" />
                <div className="w-3 h-3 rounded-full bg-yellow-400" />
                <div className="w-3 h-3 rounded-full bg-green-400" />
                <span className="ml-3 text-[10px] font-bold uppercase opacity-30">AI Console</span>
              </div>
              <div className="flex-1 rounded-2xl p-4 font-mono text-[11px] h-[400px] overflow-y-auto leading-relaxed bg-black/60 dark:bg-black/40 border border-white/5 scrollbar-hide">
                 {logs.length === 0 && <p className="opacity-20 animate-pulse text-indigo-400">Waiting for command...</p>}
                 {logs.map((l, i) => (
                   <div key={i} className="mb-2">
                      <span className="opacity-30 mr-3">[{l.ts}]</span>
                      <span className={l.level === 'error' ? 'text-red-400' : l.level === 'warning' ? 'text-amber-400' : 'text-indigo-200'}>
                        {l.msg}
                      </span>
                   </div>
                 ))}
                 <div ref={logEndRef} />
              </div>
           </div>
        </div>
      </div>
    </div>
  )
}
