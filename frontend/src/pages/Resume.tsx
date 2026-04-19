import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { resumeApi } from '../api/client'
import toast from 'react-hot-toast'
import { motion, AnimatePresence, useMotionValue, useSpring, useTransform } from 'framer-motion'
import {
  Upload, FileText, CheckCircle, Loader2, Trash2, Sparkles,
  User, Mail, Phone, MapPin, Briefcase, Code2, X, Eye, EyeOff,
} from 'lucide-react'

// ── 3D Tilt card ───────────────────────────────────────────────────────────
function TiltCard({ children, className = '', style = {} }: { children: React.ReactNode; className?: string; style?: React.CSSProperties }) {
  const ref = useRef<HTMLDivElement>(null)
  const rawX = useMotionValue(0)
  const rawY = useMotionValue(0)
  const rotateX = useSpring(useTransform(rawY, [-0.5, 0.5], [4, -4]), { stiffness: 280, damping: 32 })
  const rotateY = useSpring(useTransform(rawX, [-0.5, 0.5], [-4, 4]), { stiffness: 280, damping: 32 })
  const scale = useSpring(1, { stiffness: 280, damping: 32 })

  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    if (!ref.current) return
    const rect = ref.current.getBoundingClientRect()
    rawX.set((e.clientX - rect.left) / rect.width - 0.5)
    rawY.set((e.clientY - rect.top) / rect.height - 0.5)
    scale.set(1.01)
  }
  function onLeave() { rawX.set(0); rawY.set(0); scale.set(1) }

  return (
    <motion.div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      style={{ rotateX, rotateY, scale, transformStyle: 'preserve-3d', ...style }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

// ── Skill chip ─────────────────────────────────────────────────────────────
function SkillChip({ label, delay = 0 }: { label: string; delay?: number }) {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay }}
      className="inline-flex items-center text-[10px] px-2 py-0.5 rounded-md font-semibold bg-indigo-500/10 text-indigo-500 border border-indigo-500/20"
    >
      {label}
    </motion.span>
  )
}

// ── Info row ───────────────────────────────────────────────────────────────
function InfoRow({ icon: Icon, value, colorClass = "text-indigo-500" }: { icon: any; value: any; colorClass?: string }) {
  if (!value) return null
  return (
    <div className="flex items-center gap-2 text-xs text-secondary">
      <Icon className={`w-3.5 h-3.5 ${colorClass} opacity-70`} />
      <span className="truncate" style={{ color: 'var(--text-secondary)' }}>{value}</span>
    </div>
  )
}

// ── Resume card ────────────────────────────────────────────────────────────
function ResumeCard({ resume, index, onDelete }: { resume: any; index: number; onDelete: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const active = index === 0
  const pd = resume.parsed_data || {}

  const allSkills = [
    ...(pd.skills?.languages || []),
    ...(pd.skills?.frameworks || []),
    ...(pd.skills?.databases || []),
  ]

  async function handleDelete() {
    if (!confirm(`Delete "${resume.name}"?`)) return
    setDeleting(true)
    try {
      await resumeApi.delete(resume.id)
      toast.success('Resume deleted')
      onDelete()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="group"
    >
      <TiltCard className={`rounded-xl overflow-hidden glass transition-all ${active ? 'border-2 border-indigo-500/50' : ''}`}>
        <div className="p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${active ? 'btn-primary' : 'bg-secondary/10 text-secondary'}`}>
                <FileText className="w-6 h-6" />
              </div>
              <div className="min-w-0">
                <h3 className="font-bold text-base truncate" style={{ color: 'var(--text-primary)' }}>{resume.name}</h3>
                <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                  {pd.name || 'Anonymous User'} • {pd.total_years_experience || 0} Years Exp
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {active && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                  ACTIVE
                </span>
              )}
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="p-2 rounded-lg hover:bg-red-500/10 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                style={{ color: 'var(--text-muted)' }}
              >
                {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-lg bg-black/5 dark:bg-white/5">
            <InfoRow icon={Mail} value={pd.email} />
            <InfoRow icon={Phone} value={pd.phone} />
            <InfoRow icon={MapPin} value={pd.location} />
            <InfoRow icon={Briefcase} value={pd.current_role || 'Job Seeker'} />
          </div>

          {allSkills.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-1.5">
              {allSkills.slice(0, 10).map((s: string, i: number) => (
                <SkillChip key={s} label={s} delay={i * 0.05} />
              ))}
              {allSkills.length > 10 && (
                <span className="text-[10px] font-bold opacity-40 px-1">+{allSkills.length - 10} more</span>
              )}
            </div>
          )}

          <div className="mt-4 pt-4 border-t border-dashed border-card-border flex justify-between items-center">
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-[10px] font-bold flex items-center gap-1.5 uppercase tracking-wider hover:text-indigo-500 transition-colors"
              style={{ color: 'var(--text-muted)' }}
            >
              {expanded ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              {expanded ? 'Collapse Raw Data' : 'View AI Analysis'}
            </button>
            <span className="text-[10px] font-medium opacity-30">Uploaded {new Date(resume.created_at).toLocaleDateString()}</span>
          </div>

          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-4 overflow-hidden"
              >
                <pre className="p-4 rounded-lg bg-black/40 text-[10px] font-mono text-indigo-300 border border-white/5 max-h-60 overflow-y-auto">
                  {JSON.stringify(pd, null, 2)}
                </pre>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </TiltCard>
    </motion.div>
  )
}

export default function ResumePage() {
  const [resumes, setResumes] = useState<any[]>([])
  const [uploading, setUploading] = useState(false)

  useEffect(() => { loadResumes() }, [])

  async function loadResumes() {
    try {
      const r = await resumeApi.list()
      setResumes(r.data)
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const onDrop = useCallback(async (files: File[]) => {
    if (!files[0]) return
    setUploading(true)
    try {
      await resumeApi.upload(files[0])
      toast.success('Resume uploaded and parsed!')
      loadResumes()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setUploading(false)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] },
    maxFiles: 1,
  })

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-10">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <header>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 rounded-xl btn-primary">
              <Sparkles className="w-5 h-5" />
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight" style={{ color: 'var(--text-primary)' }}>Resume Center</h1>
          </div>
          <p style={{ color: 'var(--text-secondary)' }}>Upload your resume and let our AI handle the technical details.</p>
        </header>
      </div>

      <section>
        <div
          {...getRootProps()}
          className={`relative rounded-2xl p-12 text-center border-2 border-dashed transition-all cursor-pointer ${
            isDragActive ? 'border-indigo-500 bg-indigo-500/5' : 'border-card-border hover:border-indigo-500/50 bg-secondary/5'
          }`}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center gap-4">
            <div className={`p-4 rounded-full ${uploading ? 'animate-pulse bg-indigo-500/20' : 'bg-indigo-500/10 text-indigo-500'}`}>
              {uploading ? <Loader2 className="w-8 h-8 animate-spin" /> : <Upload className="w-8 h-8" />}
            </div>
            <div>
              <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                {uploading ? 'Processing Resume...' : 'Drag and drop your resume'}
              </p>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>PDF or DOCX (Max 5MB)</p>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Uploaded Resumes</h2>
            <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-secondary/10 text-secondary border border-secondary/20">
              {resumes.length}
            </span>
          </div>
        </div>

        {resumes.length === 0 ? (
          <div className="p-12 text-center glass rounded-2xl border-dashed border-2 border-indigo-500/20">
            <FileText className="w-12 h-12 mx-auto mb-4 opacity-10" />
            <p className="font-medium opacity-50">No resumes found</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6">
            <AnimatePresence>
              {resumes.map((r, i) => (
                <ResumeCard key={r.id} resume={r} index={i} onDelete={loadResumes} />
              ))}
            </AnimatePresence>
          </div>
        )}
      </section>
    </div>
  )
}
