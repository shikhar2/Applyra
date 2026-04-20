import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// Request interceptor
api.interceptors.request.use((config) => {
  return config
})

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    return Promise.reject(new Error(message))
  }
)

export default api

// ------------------------------------------------------------------ //
// Typed API methods
// ------------------------------------------------------------------ //

export const resumeApi = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/resumes/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000, // 2 min — AI parsing can be slow
    })
  },
  list: () => api.get('/resumes'),
  get: (id: number) => api.get(`/resumes/${id}`),
  delete: (id: number) => api.delete(`/resumes/${id}`),
}

export const profileApi = {
  create: (data: any) => api.post('/profiles', data),
  list: () => api.get('/profiles'),
  update: (id: number, data: any) => api.put(`/profiles/${id}`, data),
}

export const jobApi = {
  list: (params?: any) => api.get('/jobs', { params }),
  get: (id: number) => api.get(`/jobs/${id}`),
}

export const applicationApi = {
  list: (params?: any) => api.get('/applications', { params }),
  update: (id: number, data: any) => api.patch(`/applications/${id}`, data),
}

export const automationApi = {
  runSearch: (data: any) => api.post('/run/search', data),
  runApply: (resumeId: number, dryRun: boolean) =>
    api.post(`/run/apply?resume_id=${resumeId}&dry_run=${dryRun}`),
  testMatch: (data: any) => api.post('/test/match', data),
}

export const statsApi = {
  get: () => api.get('/stats'),
  history: () => api.get('/stats/history'),
  health: () => api.get('/health'),
}

export const followupApi = {
  list: (appId: number) => api.get(`/applications/${appId}/followups`),
  send: (followupId: number) => api.post(`/followups/${followupId}/send`),
  skip: (followupId: number) => api.post(`/followups/${followupId}/skip`),
}
