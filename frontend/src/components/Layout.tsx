import React, { useState, useEffect } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, FileText, Briefcase, Send,
  Settings, BarChart3, Zap, GraduationCap,
  Target, Kanban, ChevronLeft, ChevronRight, Sparkles, Sun, Moon, AlertTriangle
} from 'lucide-react'

const nav = [
  { to: '/',               label: 'Dashboard',      icon: LayoutDashboard, color: '#6366f1' },
  { to: '/resume',         label: 'Resume',         icon: FileText,        color: '#8b5cf6' },
  { to: '/profiles',       label: 'Job Profiles',   icon: Settings,        color: '#10b981' },
  { to: '/jobs',           label: 'Jobs Found',     icon: Briefcase,       color: '#f59e0b' },
  { to: '/pipeline',       label: 'Pipeline',       icon: Kanban,          color: '#ec4899' },
  { to: '/review',         label: 'Review Queue',   icon: AlertTriangle,   color: '#f59e0b' },
  { to: '/applications',   label: 'Applications',   icon: Send,            color: '#3b82f6' },
  { to: '/resume-tailor',  label: 'ATS Scanner',    icon: Target,          color: '#f97316' },
  { to: '/interview-prep', label: 'Interview Prep', icon: GraduationCap,   color: '#8b5cf6' },
  { to: '/stats',          label: 'Analytics',      icon: BarChart3,       color: '#10b981' },
]

interface LayoutProps {
  theme: 'light' | 'dark'
  toggleTheme: () => void
}

export default function Layout({ theme, toggleTheme }: LayoutProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [reviewCount, setReviewCount] = useState(0)
  const location = useLocation()

  useEffect(() => {
    async function fetchReviewCount() {
      try {
        const r = await fetch('/api/applications/review-queue')
        if (r.ok) {
          const data = await r.json()
          setReviewCount(Array.isArray(data) ? data.length : 0)
        }
      } catch { /* silent */ }
    }
    fetchReviewCount()
    const t = setInterval(fetchReviewCount, 30000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="flex h-screen app-bg overflow-hidden" style={{ color: 'var(--text-primary)' }}>
      {/* Sidebar */}
      <motion.aside
        animate={{ width: collapsed ? 64 : 240 }}
        transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
        className="relative flex flex-col z-10 flex-shrink-0 glass"
        style={{
          background: 'var(--sidebar-bg)',
          borderRight: '1px solid var(--card-border)',
        }}
      >
        {/* Logo */}
        <div className="p-4 flex items-center gap-3 overflow-hidden" style={{ minHeight: 72 }}>
          <motion.div
            animate={{ rotate: [0, 360] }}
            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center btn-primary"
          >
            <Zap className="w-5 h-5 text-white" />
          </motion.div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
              >
                <div className="font-bold text-lg leading-none tracking-tight gradient-text">Applyra</div>
                <div className="text-[10px] mt-1 font-medium opacity-50 uppercase tracking-widest">AI Engine</div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Divider */}
        <div className="mx-4 mb-4" style={{ height: 1, background: 'var(--card-border)' }} />

        {/* Nav */}
        <nav className="flex-1 px-3 py-1 space-y-1 overflow-y-auto overflow-x-hidden">
          {nav.map(({ to, label, icon: Icon, color }) => {
            const isActive = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)
            const badge = to === '/review' && reviewCount > 0 ? reviewCount : 0
            return (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                title={collapsed ? label : undefined}
                className={() =>
                  `nav-item ${isActive ? 'active' : ''} ${collapsed ? 'justify-center' : ''}`
                }
              >
                <motion.div
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  className="flex-shrink-0 relative"
                >
                  <Icon
                    className="w-4.5 h-4.5"
                    style={{ color: isActive ? color : 'inherit' }}
                  />
                  {badge > 0 && (
                    <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold text-white"
                      style={{ background: '#f59e0b' }}>
                      {badge > 9 ? '9+' : badge}
                    </span>
                  )}
                </motion.div>
                <AnimatePresence>
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0, width: 0 }}
                      animate={{ opacity: 1, width: 'auto' }}
                      exit={{ opacity: 0, width: 0 }}
                      transition={{ duration: 0.2 }}
                      className="truncate flex-1"
                    >
                      {label}
                    </motion.span>
                  )}
                </AnimatePresence>
                {!collapsed && badge > 0 && (
                  <span className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded-full"
                    style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}>
                    {badge}
                  </span>
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="px-3 pb-4 pt-2 space-y-2" style={{ borderTop: '1px solid var(--card-border)' }}>
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all hover:bg-slate-500/10"
            style={{ color: 'var(--text-secondary)' }}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-500" />}
            {!collapsed && <span className="text-xs font-semibold">{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>}
          </button>

          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2 px-3 py-2 rounded-xl"
                style={{ background: 'var(--nav-active-bg)', border: '1px solid var(--card-border)' }}
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-500">Gemini AI Active</span>
              </motion.div>
            )}
          </AnimatePresence>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-xl text-xs transition-all"
            style={{ color: 'var(--text-muted)', background: 'var(--input-bg)' }}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <><ChevronLeft className="w-3.5 h-3.5" /><span>Collapse Sidebar</span></>}
          </button>
        </div>
      </motion.aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, scale: 0.995 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="h-full"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}
