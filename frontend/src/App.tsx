import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import ResumePage from './pages/Resume'
import ProfilesPage from './pages/Profiles'
import JobsPage from './pages/Jobs'
import ApplicationsPage from './pages/Applications'
import StatsPage from './pages/Stats'
import AITestPage from './pages/AITest'
import InterviewPrepPage from './pages/InterviewPrep'
import ResumeTailorPage from './pages/ResumeTailor'
import KanbanPage from './pages/Kanban'
import ReviewQueuePage from './pages/ReviewQueue'
import { useStore } from './store/useStore'
import api from './api/client'

export default function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('theme') as 'light' | 'dark') || 'dark'
  })

  const setIsRunning = useStore(state => state.setIsRunning)
  const setLogs = useStore(state => state.setLogs)
  const setRunStats = useStore(state => state.setRunStats)

  useEffect(() => {
    const root = window.document.documentElement
    if (theme === 'light') {
      root.classList.add('light')
    } else {
      root.classList.remove('light')
    }
    localStorage.setItem('theme', theme)
  }, [theme])

  // Global background task polling
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await api.get('/run/status')
        setIsRunning(r.data.running)
        setLogs(r.data.logs || [])
        if (r.data.stats && Object.keys(r.data.stats).length > 0) {
          setRunStats(r.data.stats)
        }
      } catch (e) {
        console.error("Failed to fetch background status", e)
      }
    }

    poll() // Initial check
    const interval = setInterval(poll, 3000)
    return () => clearInterval(interval)
  }, [setIsRunning, setLogs, setRunStats])

  const toggleTheme = () => setTheme(prev => prev === 'light' ? 'dark' : 'light')

  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          className: 'glass',
          style: { 
            background: 'var(--card-bg)', 
            color: 'var(--text-primary)', 
            border: '1px solid var(--card-border)',
            backdropFilter: 'blur(10px)'
          },
        }}
      />
      <Routes>
        <Route element={<Layout theme={theme} toggleTheme={toggleTheme} />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/resume" element={<ResumePage />} />
          <Route path="/profiles" element={<ProfilesPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/pipeline" element={<KanbanPage />} />
          <Route path="/review" element={<ReviewQueuePage />} />
          <Route path="/applications" element={<ApplicationsPage />} />
          <Route path="/resume-tailor" element={<ResumeTailorPage />} />
          <Route path="/interview-prep" element={<InterviewPrepPage />} />
          <Route path="/stats" element={<StatsPage />} />
          <Route path="/ai-test" element={<AITestPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
