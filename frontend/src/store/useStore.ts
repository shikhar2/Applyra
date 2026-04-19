import { create } from 'zustand'

interface LogEntry {
  ts: string
  level: string
  msg: string
}

interface AppState {
  activeResume: any | null
  activeProfile: any | null
  stats: any | null
  isRunning: boolean
  logs: LogEntry[]
  runStats: any | null
  setActiveResume: (r: any) => void
  setActiveProfile: (p: any) => void
  setStats: (s: any) => void
  setIsRunning: (v: boolean) => void
  setLogs: (logs: LogEntry[]) => void
  setRunStats: (stats: any) => void
}

export const useStore = create<AppState>((set) => ({
  activeResume: null,
  activeProfile: null,
  stats: null,
  isRunning: false,
  logs: [],
  runStats: null,
  setActiveResume: (r) => set({ activeResume: r }),
  setActiveProfile: (p) => set({ activeProfile: p }),
  setStats: (s) => set({ stats: s }),
  setIsRunning: (v) => set({ isRunning: v }),
  setLogs: (logs) => set({ logs }),
  setRunStats: (runStats) => set({ runStats }),
}))
