import React, { useEffect, useState } from 'react'
import { automationApi, resumeApi } from '../api/client'
import toast from 'react-hot-toast'
import { Bot, Loader2, Zap } from 'lucide-react'

export default function AITestPage() {
  const [resumes, setResumes] = useState<any[]>([])
  const [resumeId, setResumeId] = useState<number | null>(null)
  const [jobTitle, setJobTitle] = useState('Senior Full Stack Engineer')
  const [company, setCompany] = useState('Stripe')
  const [jobDesc, setJobDesc] = useState(`We are looking for a Senior Full Stack Engineer to join our team.

Requirements:
- 5+ years of experience with React and TypeScript
- Strong backend experience with Python or Go
- Experience with PostgreSQL and Redis
- AWS or GCP experience
- Experience with REST APIs and microservices
- Strong understanding of CI/CD pipelines

Nice to have:
- Experience with Kubernetes
- Open source contributions
- Prior fintech experience`)
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    resumeApi.list().then(r => {
      setResumes(r.data)
      if (r.data.length > 0) setResumeId(r.data[0].id)
    }).catch(() => {})
  }, [])

  async function test() {
    if (!resumeId) { toast.error('Upload a resume first'); return }
    setLoading(true)
    setResult(null)
    try {
      const r = await automationApi.testMatch({
        resume_id: resumeId,
        job_description: jobDesc,
        job_title: jobTitle,
        company,
      })
      setResult(r.data)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  const score = result?.score ?? 0
  const scoreColor = score >= 0.85 ? 'text-green-400' : score >= 0.70 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="p-8">
      <div className="flex items-center gap-3 mb-2">
        <Bot className="w-6 h-6 text-blue-400" />
        <h1 className="text-2xl font-bold text-white">AI Match Test</h1>
      </div>
      <p className="text-gray-500 mb-6">Test how well your resume matches a job description</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Resume</label>
            <select
              value={resumeId || ''}
              onChange={(e) => setResumeId(Number(e.target.value))}
              className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-white text-sm"
            >
              {resumes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Job Title</label>
            <input
              value={jobTitle}
              onChange={e => setJobTitle(e.target.value)}
              className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-white text-sm"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Company</label>
            <input
              value={company}
              onChange={e => setCompany(e.target.value)}
              className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-white text-sm"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Job Description</label>
            <textarea
              value={jobDesc}
              onChange={e => setJobDesc(e.target.value)}
              rows={12}
              className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-white text-sm resize-none"
            />
          </div>
          <button
            onClick={test}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-2.5 rounded-lg font-medium"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
            {loading ? 'Analyzing...' : 'Test Match with AI'}
          </button>
        </div>

        {/* Result */}
        <div>
          {result ? (
            <div className="space-y-4">
              {/* Score */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
                <p className="text-sm text-gray-500">Match Score</p>
                <p className={`text-6xl font-bold mt-2 ${scoreColor}`}>{Math.round(score * 100)}%</p>
                <p className={`text-sm mt-1 font-medium ${scoreColor}`}>{result.analysis?.verdict?.replace('_', ' ')}</p>
                <p className={`text-sm mt-2 font-medium ${result.analysis?.apply_recommendation ? 'text-green-400' : 'text-red-400'}`}>
                  {result.analysis?.apply_recommendation ? '✓ Recommended to apply' : '✗ Not recommended'}
                </p>
              </div>

              {/* Skills match */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <p className="text-xs text-gray-500 mb-2">Matching Skills</p>
                <div className="flex flex-wrap gap-1.5">
                  {(result.analysis?.matching_skills || []).map((s: string) => (
                    <span key={s} className="text-xs bg-green-950 text-green-300 border border-green-800 px-2 py-0.5 rounded-full">{s}</span>
                  ))}
                </div>
                {(result.analysis?.missing_skills || []).length > 0 && (
                  <>
                    <p className="text-xs text-gray-500 mt-3 mb-2">Missing Skills</p>
                    <div className="flex flex-wrap gap-1.5">
                      {result.analysis.missing_skills.map((s: string) => (
                        <span key={s} className="text-xs bg-red-950 text-red-300 border border-red-800 px-2 py-0.5 rounded-full">{s}</span>
                      ))}
                    </div>
                  </>
                )}
              </div>

              {/* Explanation */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <p className="text-xs text-gray-500 mb-2">Analysis</p>
                <p className="text-sm text-gray-300 leading-relaxed">{result.analysis?.explanation}</p>
              </div>

              {/* Cover letter */}
              {result.cover_letter && (
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                  <p className="text-xs text-gray-500 mb-2">Generated Cover Letter</p>
                  <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">{result.cover_letter}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-600 text-center py-20">
              <Bot className="w-12 h-12 mb-3 opacity-30" />
              <p>Run a match test to see AI analysis here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
