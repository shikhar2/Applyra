import React, { useEffect, useState } from 'react'
import { statsApi } from '../api/client'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, Cell
} from 'recharts'
import { TrendingUp, Briefcase, CheckCircle, Award, BarChart2 } from 'lucide-react'
import { motion } from 'framer-motion'

const STAT_CARDS = [
  {
    key: 'total_jobs_discovered',
    label: 'Jobs Found',
    icon: Briefcase,
    gradient: 'linear-gradient(90deg, #3b82f6, #6366f1)',
    iconBg: 'rgba(59,130,246,0.15)',
    color: '#60a5fa',
  },
  {
    key: 'applied',
    label: 'Applied',
    icon: CheckCircle,
    gradient: 'linear-gradient(90deg, #34d399, #10b981)',
    iconBg: 'rgba(52,211,153,0.15)',
    color: '#34d399',
  },
  {
    key: 'interviews',
    label: 'Interviews',
    icon: TrendingUp,
    gradient: 'linear-gradient(90deg, #a78bfa, #8b5cf6)',
    iconBg: 'rgba(167,139,250,0.15)',
    color: '#a78bfa',
  },
  {
    key: 'success_rate',
    label: 'Success Rate',
    icon: Award,
    gradient: 'linear-gradient(90deg, #fbbf24, #f59e0b)',
    iconBg: 'rgba(251,191,36,0.15)',
    color: '#fbbf24',
    suffix: '%',
  },
]

const FUNNEL_FILLS = ['#3b82f6', '#eab308', '#22c55e', '#a855f7']

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div
      className="rounded-xl px-3 py-2.5 text-sm"
      style={{
        background: 'rgba(2,4,10,0.95)',
        border: '1px solid rgba(255,255,255,0.12)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        color: '#f1f5f9',
      }}
    >
      <p className="font-medium mb-1" style={{ color: 'rgba(255,255,255,0.6)' }}>{label}</p>
      {payload.map((entry: any, i: number) => (
        <p key={i} className="font-semibold" style={{ color: entry.color || entry.fill }}>
          {entry.name}: {entry.value}
        </p>
      ))}
    </div>
  )
}

export default function StatsPage() {
  const [stats, setStats] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])

  useEffect(() => {
    statsApi.get().then(r => setStats(r.data)).catch(() => {})
    statsApi.history().then(r => setHistory(r.data.reverse())).catch(() => {})
  }, [])

  const funnelData = stats ? [
    { name: 'Discovered', value: stats.total_jobs_discovered },
    { name: 'Queued',     value: stats.pending },
    { name: 'Applied',    value: stats.applied },
    { name: 'Interviews', value: stats.interviews },
  ] : []

  const axisStyle = { fill: 'rgba(255,255,255,0.35)', fontSize: 11 }
  const gridStyle = 'rgba(255,255,255,0.05)'

  return (
    <div className="p-8">
      {/* Page header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex items-center gap-4 mb-8"
      >
        <div
          className="w-11 h-11 rounded-2xl flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg, #fbbf24, #f59e0b)' }}
        >
          <BarChart2 className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
            Your job search performance at a glance
          </p>
        </div>
      </motion.div>

      {/* Summary stat cards */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {STAT_CARDS.map(({ key, label, icon: Icon, gradient, iconBg, color, suffix }, i) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07, duration: 0.4 }}
              className="card-3d rounded-2xl p-5 stat-card"
              style={{ '--stat-gradient': gradient } as React.CSSProperties}
            >
              <div className="flex items-start justify-between mb-3">
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center"
                  style={{ background: iconBg }}
                >
                  <Icon className="w-4 h-4" style={{ color }} />
                </div>
              </div>
              <p className="text-xs font-medium mb-1" style={{ color: 'rgba(255,255,255,0.4)' }}>
                {label}
              </p>
              <p className="text-3xl font-bold" style={{ color }}>
                {stats[key] ?? 0}{suffix || ''}
              </p>
            </motion.div>
          ))}
        </div>
      )}

      {/* Application Funnel */}
      {funnelData.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="card-3d rounded-2xl p-6 mb-5"
        >
          <div className="flex items-center gap-3 mb-5">
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center"
              style={{ background: 'rgba(59,130,246,0.15)' }}
            >
              <BarChart2 className="w-4 h-4" style={{ color: '#60a5fa' }} />
            </div>
            <h2 className="text-sm font-semibold" style={{ color: 'rgba(255,255,255,0.7)' }}>
              Application Funnel
            </h2>
          </div>

          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={funnelData} barCategoryGap="32%">
              <CartesianGrid vertical={false} stroke={gridStyle} />
              <XAxis
                dataKey="name"
                axisLine={false}
                tickLine={false}
                tick={axisStyle}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={axisStyle}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {funnelData.map((_, i) => (
                  <Cell key={i} fill={FUNNEL_FILLS[i % FUNNEL_FILLS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </motion.div>
      )}

      {/* Daily Activity Line Chart */}
      {history.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.4 }}
          className="card-3d rounded-2xl p-6"
        >
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div
                className="w-8 h-8 rounded-xl flex items-center justify-center"
                style={{ background: 'rgba(52,211,153,0.15)' }}
              >
                <TrendingUp className="w-4 h-4" style={{ color: '#34d399' }} />
              </div>
              <h2 className="text-sm font-semibold" style={{ color: 'rgba(255,255,255,0.7)' }}>
                Daily Activity (last 30 days)
              </h2>
            </div>
            {/* Legend */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-0.5 rounded-full" style={{ background: '#34d399' }} />
                <span className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Applied</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-0.5 rounded-full" style={{ background: '#3b82f6' }} />
                <span className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>Discovered</span>
              </div>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={history}>
              <CartesianGrid stroke={gridStyle} vertical={false} />
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={axisStyle}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={axisStyle}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)' }} />
              <Line
                type="monotone"
                dataKey="applications_sent"
                stroke="#22c55e"
                dot={false}
                strokeWidth={2}
                name="Applied"
              />
              <Line
                type="monotone"
                dataKey="jobs_discovered"
                stroke="#3b82f6"
                dot={false}
                strokeWidth={2}
                name="Discovered"
              />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>
      )}

      {/* Empty state when no data at all */}
      {!stats && history.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="card-3d rounded-2xl flex flex-col items-center py-20 text-center"
        >
          <motion.div
            animate={{ y: [0, -6, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
            style={{ background: 'rgba(251,191,36,0.12)', border: '1px solid rgba(251,191,36,0.2)' }}
          >
            <BarChart2 className="w-8 h-8" style={{ color: '#fbbf24' }} />
          </motion.div>
          <h3 className="text-lg font-semibold text-white mb-2">No data yet</h3>
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
            Stats will appear once you start applying to jobs
          </p>
        </motion.div>
      )}
    </div>
  )
}
