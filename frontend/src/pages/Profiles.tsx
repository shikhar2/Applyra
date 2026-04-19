import React, { useEffect, useState } from 'react'
import { profileApi } from '../api/client'
import toast from 'react-hot-toast'
import { Plus, Settings, Trash2, Save, X, User, Briefcase, MapPin, DollarSign, Tag, CheckCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

function calcCompleteness(p: any): { score: number; missing: string[] } {
  const checks: { label: string; ok: boolean }[] = [
    { label: 'Profile name', ok: !!p.name?.trim() },
    { label: 'Target roles', ok: (p.target_roles || []).length > 0 },
    { label: 'Locations', ok: (p.target_locations || []).length > 0 },
    { label: 'Experience level', ok: (p.experience_levels || []).length > 0 },
    { label: 'Min salary', ok: !!p.min_salary },
    { label: 'Years of experience', ok: p.min_years_experience != null },
    { label: 'Required keywords', ok: (p.required_keywords || []).length > 0 },
    { label: 'Excluded keywords', ok: (p.excluded_keywords || []).length > 0 },
  ]
  const passed = checks.filter(c => c.ok)
  return {
    score: Math.round((passed.length / checks.length) * 100),
    missing: checks.filter(c => !c.ok).map(c => c.label),
  }
}

const EMPTY_PROFILE = {
  name: '',
  target_roles: ['Full Stack Engineer', 'Software Engineer'],
  target_locations: ['Remote'],
  remote_only: true,
  min_salary: null,
  max_salary: null,
  salary_currency: 'USD',
  min_years_experience: null,
  max_years_experience: null,
  experience_levels: ['mid', 'senior'],
  company_size: [],
  excluded_companies: [],
  required_keywords: [],
  excluded_keywords: ['intern', 'junior', 'lead', 'staff', 'principal', 'manager'],
}

const EXP_LEVELS = ['entry', 'junior', 'mid', 'senior', 'lead', 'staff', 'principal', 'manager']

const SALARY_PRESETS: Record<string, { label: string; values: number[] }[]> = {
  USD: [
    { label: '$60k', values: [60000, 0] },
    { label: '$80k', values: [80000, 0] },
    { label: '$100k', values: [100000, 0] },
    { label: '$120k', values: [120000, 0] },
    { label: '$150k', values: [150000, 0] },
    { label: '$200k+', values: [200000, 0] },
  ],
  INR: [
    { label: '5 LPA', values: [500000, 0] },
    { label: '8 LPA', values: [800000, 0] },
    { label: '12 LPA', values: [1200000, 0] },
    { label: '18 LPA', values: [1800000, 0] },
    { label: '25 LPA', values: [2500000, 0] },
    { label: '40 LPA+', values: [4000000, 0] },
  ],
}

function TagInput({ label, value, onChange }: { label: string; value: string[]; onChange: (v: string[]) => void }) {
  const [input, setInput] = useState('')
  const tags: string[] = value || []

  const add = () => {
    const v = input.trim()
    if (v && !tags.includes(v)) {
      onChange([...tags, v])
    }
    setInput('')
  }

  const remove = (tag: string) => onChange(tags.filter((t) => t !== tag))

  return (
    <div>
      <label className="block text-xs font-medium mb-1.5" style={{ color: 'rgba(255,255,255,0.4)' }}>{label}</label>
      <div
        className="rounded-xl p-2.5 min-h-10"
        style={{
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.10)',
        }}
      >
        <div className="flex flex-wrap gap-1.5 mb-2">
          <AnimatePresence>
            {tags.map((t) => (
              <motion.span
                key={t}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium"
                style={{
                  background: 'rgba(96,165,250,0.15)',
                  border: '1px solid rgba(96,165,250,0.3)',
                  color: '#93c5fd',
                }}
              >
                {t}
                <button
                  onClick={() => remove(t)}
                  className="ml-0.5 opacity-60 hover:opacity-100 transition-opacity"
                  style={{ color: '#f87171' }}
                >
                  <X className="w-3 h-3" />
                </button>
              </motion.span>
            ))}
          </AnimatePresence>
        </div>
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), add())}
            placeholder="Type + Enter to add"
            className="flex-1 bg-transparent text-sm text-white outline-none"
            style={{ color: '#f1f5f9' }}
          />
          <button
            onClick={add}
            className="text-xs font-medium px-2 py-0.5 rounded-lg transition-colors"
            style={{ color: '#60a5fa', background: 'rgba(96,165,250,0.1)' }}
          >
            Add
          </button>
        </div>
      </div>
    </div>
  )
}

function ProfileForm({ initial, onSave, onCancel }: { initial?: any; onSave: () => void; onCancel: () => void }) {
  const [form, setForm] = useState(initial || EMPTY_PROFILE)

  const set = (key: string, val: any) => setForm((f: any) => ({ ...f, [key]: val }))

  async function save() {
    if (!form.name.trim()) { toast.error('Profile name required'); return }
    try {
      if (initial?.id) {
        await profileApi.update(initial.id, form)
        toast.success('Profile updated')
      } else {
        await profileApi.create(form)
        toast.success('Profile created')
      }
      onSave()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.3 }}
      className="card-3d rounded-2xl p-6 space-y-5"
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, #3b82f6, #6366f1)' }}
        >
          <User className="w-4 h-4 text-white" />
        </div>
        <h3 className="text-lg font-semibold text-white">
          {initial?.id ? 'Edit' : 'New'} Profile
        </h3>
      </div>

      <div style={{ background: 'rgba(255,255,255,0.05)', height: 1 }} />

      {/* Profile Name */}
      <div>
        <label className="block text-xs font-medium mb-1.5" style={{ color: 'rgba(255,255,255,0.4)' }}>
          Profile Name
        </label>
        <input
          value={form.name}
          onChange={(e) => set('name', e.target.value)}
          placeholder="e.g. Full Stack Engineer - Remote"
          className="input-glass rounded-xl px-3 py-2.5 w-full text-sm"
        />
      </div>

      <TagInput label="Target Roles" value={form.target_roles} onChange={(v) => set('target_roles', v)} />
      <TagInput label="Locations" value={form.target_locations} onChange={(v) => set('target_locations', v)} />
      <TagInput label="Required Keywords (in job title/desc)" value={form.required_keywords} onChange={(v) => set('required_keywords', v)} />
      <TagInput label="Excluded Keywords" value={form.excluded_keywords} onChange={(v) => set('excluded_keywords', v)} />
      <TagInput label="Excluded Companies" value={form.excluded_companies} onChange={(v) => set('excluded_companies', v)} />

      {/* Experience Years */}
      <div>
        <label className="block text-xs font-medium mb-2" style={{ color: 'rgba(255,255,255,0.4)' }}>
          Years of Experience
        </label>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs mb-1" style={{ color: 'rgba(255,255,255,0.25)' }}>Min years</label>
            <input
              type="number"
              min={0}
              max={30}
              value={form.min_years_experience ?? ''}
              onChange={(e) => set('min_years_experience', e.target.value ? Number(e.target.value) : null)}
              placeholder="e.g. 3"
              className="input-glass rounded-xl px-3 py-2.5 w-full text-sm"
            />
          </div>
          <div>
            <label className="block text-xs mb-1" style={{ color: 'rgba(255,255,255,0.25)' }}>Max years (blank = no limit)</label>
            <input
              type="number"
              min={0}
              max={40}
              value={form.max_years_experience ?? ''}
              onChange={(e) => set('max_years_experience', e.target.value ? Number(e.target.value) : null)}
              placeholder="e.g. 8"
              className="input-glass rounded-xl px-3 py-2.5 w-full text-sm"
            />
          </div>
        </div>
      </div>

      {/* Experience Level Chips */}
      <div>
        <label className="block text-xs font-medium mb-2" style={{ color: 'rgba(255,255,255,0.4)' }}>
          Experience Level
        </label>
        <div className="flex flex-wrap gap-2">
          {EXP_LEVELS.map((lvl) => {
            const active = (form.experience_levels || []).includes(lvl)
            return (
              <motion.button
                key={lvl}
                type="button"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  const cur: string[] = form.experience_levels || []
                  set('experience_levels', active ? cur.filter((x) => x !== lvl) : [...cur, lvl])
                }}
                className="px-3 py-1 rounded-full text-xs font-medium transition-all"
                style={
                  active
                    ? {
                        background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
                        border: '1px solid rgba(99,102,241,0.5)',
                        color: '#fff',
                        boxShadow: '0 2px 8px rgba(59,130,246,0.35)',
                      }
                    : {
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.10)',
                        color: 'rgba(255,255,255,0.4)',
                      }
                }
              >
                {lvl}
              </motion.button>
            )
          })}
        </div>
      </div>

      {/* Currency + Salary */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-medium" style={{ color: 'rgba(255,255,255,0.4)' }}>
            Minimum Salary
          </label>
          {/* Currency toggle */}
          <div
            className="flex rounded-lg overflow-hidden text-xs"
            style={{ border: '1px solid rgba(255,255,255,0.10)' }}
          >
            {(['USD', 'INR'] as const).map((cur) => (
              <motion.button
                key={cur}
                type="button"
                whileTap={{ scale: 0.97 }}
                onClick={() => { set('salary_currency', cur); set('min_salary', null) }}
                className="px-3 py-1.5 font-medium transition-all"
                style={
                  form.salary_currency === cur
                    ? {
                        background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
                        color: '#fff',
                      }
                    : {
                        background: 'rgba(255,255,255,0.04)',
                        color: 'rgba(255,255,255,0.4)',
                      }
                }
              >
                {cur === 'USD' ? '$ USD' : '₹ INR'}
              </motion.button>
            ))}
          </div>
        </div>

        {/* Salary presets */}
        <div className="flex flex-wrap gap-2 mb-2">
          {(SALARY_PRESETS[form.salary_currency] || SALARY_PRESETS.USD).map((p) => (
            <motion.button
              key={p.label}
              type="button"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => set('min_salary', p.values[0])}
              className="px-3 py-1 rounded-full text-xs font-medium transition-all"
              style={
                form.min_salary === p.values[0]
                  ? {
                      background: 'linear-gradient(135deg, rgba(52,211,153,0.3), rgba(16,185,129,0.2))',
                      border: '1px solid rgba(52,211,153,0.4)',
                      color: '#34d399',
                    }
                  : {
                      background: 'rgba(255,255,255,0.04)',
                      border: '1px solid rgba(255,255,255,0.10)',
                      color: 'rgba(255,255,255,0.4)',
                    }
              }
            >
              {p.label}
            </motion.button>
          ))}
        </div>

        {/* Manual salary input */}
        <div className="relative">
          <span
            className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-medium"
            style={{ color: 'rgba(255,255,255,0.35)' }}
          >
            {form.salary_currency === 'INR' ? '₹' : '$'}
          </span>
          <input
            type="number"
            value={form.min_salary || ''}
            onChange={(e) => set('min_salary', Number(e.target.value) || null)}
            placeholder={form.salary_currency === 'INR' ? 'e.g. 1200000 (12 LPA)' : 'e.g. 120000'}
            className="input-glass rounded-xl pl-7 pr-3 py-2.5 w-full text-sm"
          />
        </div>
        {form.salary_currency === 'INR' && form.min_salary ? (
          <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.25)' }}>
            = {(form.min_salary / 100000).toFixed(1)} LPA
          </p>
        ) : null}
      </div>

      {/* Remote only toggle */}
      <div>
        <label className="flex items-center gap-3 cursor-pointer group">
          <div
            onClick={() => set('remote_only', !form.remote_only)}
            className="relative w-10 h-5 rounded-full transition-all flex-shrink-0 cursor-pointer"
            style={{
              background: form.remote_only
                ? 'linear-gradient(135deg, #3b82f6, #6366f1)'
                : 'rgba(255,255,255,0.1)',
              border: '1px solid rgba(255,255,255,0.15)',
            }}
          >
            <motion.div
              animate={{ x: form.remote_only ? 20 : 2 }}
              transition={{ type: 'spring', stiffness: 500, damping: 30 }}
              className="absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-md"
            />
          </div>
          <span className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.7)' }}>
            Remote only
          </span>
        </label>
        {/* hidden checkbox for form logic */}
        <input
          type="checkbox"
          checked={form.remote_only}
          onChange={(e) => set('remote_only', e.target.checked)}
          className="sr-only"
        />
      </div>

      {/* Action buttons */}
      <div style={{ background: 'rgba(255,255,255,0.05)', height: 1 }} />
      <div className="flex gap-3">
        <motion.button
          onClick={save}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="btn-primary flex items-center gap-2 text-white px-5 py-2.5 rounded-xl text-sm font-semibold"
        >
          <Save className="w-4 h-4" /> Save Profile
        </motion.button>
        <motion.button
          onClick={onCancel}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="px-4 py-2.5 rounded-xl text-sm font-medium transition-colors"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.10)',
            color: 'rgba(255,255,255,0.5)',
          }}
        >
          Cancel
        </motion.button>
      </div>
    </motion.div>
  )
}

function CompletenessRing({ score }: { score: number }) {
  const r = 20
  const circ = 2 * Math.PI * r
  const dash = (score / 100) * circ
  const color = score >= 80 ? '#34d399' : score >= 50 ? '#fbbf24' : '#f87171'
  return (
    <div className="relative flex items-center justify-center w-14 h-14 flex-shrink-0">
      <svg width="56" height="56" className="-rotate-90">
        <circle cx="28" cy="28" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="4" />
        <motion.circle
          cx="28" cy="28" r={r} fill="none"
          stroke={color} strokeWidth="4"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - dash }}
          transition={{ duration: 1, ease: 'easeOut' }}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute text-xs font-bold" style={{ color }}>{score}%</span>
    </div>
  )
}

function ProfileCard({ p, onEdit }: { p: any; onEdit: () => void }) {
  const expRange =
    p.min_years_experience != null || p.max_years_experience != null
      ? `${p.min_years_experience ?? 0}${p.max_years_experience ? `–${p.max_years_experience}` : '+'} yrs`
      : null

  const salaryLabel = p.min_salary
    ? p.salary_currency === 'INR'
      ? `₹${(p.min_salary / 100000).toFixed(1)} LPA`
      : `$${(p.min_salary / 1000).toFixed(0)}k`
    : null

  const { score, missing } = calcCompleteness(p)

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-3d rounded-2xl p-5"
    >
      {/* Completeness bar */}
      <div className="flex items-center gap-3 mb-4 pb-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <CompletenessRing score={score} />
        <div className="flex-1">
          <p className="text-xs font-semibold mb-1" style={{ color: 'rgba(255,255,255,0.5)' }}>Profile Completeness</p>
          {missing.length > 0 ? (
            <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>
              Missing: {missing.slice(0, 3).join(', ')}{missing.length > 3 ? ` +${missing.length - 3} more` : ''}
            </p>
          ) : (
            <p className="text-xs flex items-center gap-1" style={{ color: '#34d399' }}>
              <CheckCircle className="w-3 h-3" /> Profile fully configured
            </p>
          )}
        </div>
      </div>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Name row */}
          <div className="flex items-center gap-3 flex-wrap mb-2">
            <h3 className="font-semibold text-white text-base">{p.name}</h3>
            {p.remote_only && (
              <span
                className="text-xs font-medium px-2 py-0.5 rounded-full"
                style={{
                  background: 'rgba(52,211,153,0.12)',
                  border: '1px solid rgba(52,211,153,0.25)',
                  color: '#34d399',
                }}
              >
                Remote
              </span>
            )}
            {expRange && (
              <span
                className="text-xs font-medium px-2 py-0.5 rounded-full"
                style={{
                  background: 'rgba(167,139,250,0.12)',
                  border: '1px solid rgba(167,139,250,0.25)',
                  color: '#a78bfa',
                }}
              >
                {expRange}
              </span>
            )}
            {salaryLabel && (
              <span
                className="text-xs font-medium px-2 py-0.5 rounded-full flex items-center gap-1"
                style={{
                  background: 'rgba(251,191,36,0.12)',
                  border: '1px solid rgba(251,191,36,0.25)',
                  color: '#fbbf24',
                }}
              >
                <DollarSign className="w-3 h-3" />
                {salaryLabel}+
              </span>
            )}
          </div>

          {/* Roles */}
          <p className="text-sm mb-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
            <span style={{ color: 'rgba(255,255,255,0.25)' }}>Roles: </span>
            {(p.target_roles || []).join(', ')}
          </p>

          {/* Locations */}
          <p className="text-sm mb-2" style={{ color: 'rgba(255,255,255,0.4)' }}>
            <span style={{ color: 'rgba(255,255,255,0.25)' }}>Locations: </span>
            {(p.target_locations || []).join(', ')}
          </p>

          {/* Experience levels chips */}
          {(p.experience_levels || []).length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {(p.experience_levels as string[]).map((lvl) => (
                <span
                  key={lvl}
                  className="text-xs px-2 py-0.5 rounded-full font-medium"
                  style={{
                    background: 'rgba(96,165,250,0.10)',
                    border: '1px solid rgba(96,165,250,0.2)',
                    color: '#93c5fd',
                  }}
                >
                  {lvl}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Edit button */}
        <motion.button
          onClick={onEdit}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          className="p-2 rounded-xl transition-colors flex-shrink-0"
          style={{
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.08)',
            color: 'rgba(255,255,255,0.4)',
          }}
        >
          <Settings className="w-4 h-4" />
        </motion.button>
      </div>
    </motion.div>
  )
}

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<any>(null)

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const r = await profileApi.list()
      setProfiles(r.data)
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  return (
    <div className="p-8">
      {/* Page header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex items-center justify-between mb-8"
      >
        <div className="flex items-center gap-4">
          <div
            className="w-11 h-11 rounded-2xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #3b82f6, #6366f1)' }}
          >
            <Briefcase className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Job Profiles</h1>
            <p className="text-sm mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Define what jobs to target and filter out
            </p>
          </div>
        </div>
        <motion.button
          onClick={() => { setEditing(null); setShowForm(true) }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="btn-primary flex items-center gap-2 text-white px-5 py-2.5 rounded-xl text-sm font-semibold"
        >
          <Plus className="w-4 h-4" /> New Profile
        </motion.button>
      </motion.div>

      {/* New profile form */}
      <AnimatePresence>
        {showForm && !editing && (
          <motion.div
            key="new-form"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-6 overflow-hidden"
          >
            <ProfileForm
              onSave={() => { setShowForm(false); load() }}
              onCancel={() => setShowForm(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Empty state */}
      {profiles.length === 0 && !showForm ? (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card-3d rounded-2xl flex flex-col items-center justify-center py-20 text-center"
        >
          <motion.div
            animate={{ y: [0, -6, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
            style={{ background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.2)' }}
          >
            <Briefcase className="w-8 h-8" style={{ color: '#a78bfa' }} />
          </motion.div>
          <h3 className="text-lg font-semibold text-white mb-2">No profiles yet</h3>
          <p className="text-sm mb-6" style={{ color: 'rgba(255,255,255,0.4)' }}>
            Create a profile to start targeting the right jobs
          </p>
          <motion.button
            onClick={() => setShowForm(true)}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="btn-primary flex items-center gap-2 text-white px-5 py-2.5 rounded-xl text-sm font-semibold"
          >
            <Plus className="w-4 h-4" /> Create First Profile
          </motion.button>
        </motion.div>
      ) : (
        <div className="space-y-4">
          {profiles.map((p, i) => (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <AnimatePresence mode="wait">
                {editing?.id === p.id ? (
                  <ProfileForm
                    key="edit-form"
                    initial={p}
                    onSave={() => { setEditing(null); load() }}
                    onCancel={() => setEditing(null)}
                  />
                ) : (
                  <ProfileCard
                    key="card"
                    p={p}
                    onEdit={() => setEditing(p)}
                  />
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
