import { useState, useEffect } from 'react'
import { getTask } from '../api'
import type { TaskInfo } from '../types'
import ReactMarkdown from 'react-markdown'

interface Props {
  taskId: string
  onBack: () => void
}

export default function ReportView({ taskId, onBack }: Props) {
  const [task, setTask] = useState<TaskInfo | null>(null)
  const [loading, setLoading] = useState(true)

  // Poll task status until report_path is available
  useEffect(() => {
    const poll = async () => {
      const t = await getTask(taskId)
      setTask(t)
      setLoading(false)

      // If still running or no report_path yet, keep polling
      if (t?.status === 'running' || t?.status === 'queued' || t?.status === 'pending') {
        setTimeout(() => {
          setLoading(true)
          poll()
        }, 3000)
      }
    }
    poll()

    // Re-poll every 5s for running tasks
    const interval = setInterval(() => {
      setTask(prev => {
        if (prev?.status === 'running' || prev?.status === 'queued') {
          setLoading(true)
          poll()
        }
        return prev
      })
    }, 5000)
    return () => clearInterval(interval)
  }, [taskId])

  if (loading && !task) return <div className="text-center py-20 text-ta-muted">加载中...</div>
  if (!task) return <div className="text-center py-20 text-ta-danger">任务不存在</div>
  if (task.status === 'failed') return <ReportFailed task={task} onBack={onBack} />
  if (task.status !== 'completed') return <ReportRunning task={task} onBack={onBack} />

  return <ReportCompleted task={task} onBack={onBack} />
}

function ReportFailed({ task, onBack }: { task: TaskInfo; onBack: () => void }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="text-ta-muted hover:text-ta-text text-sm transition-colors">← 返回列表</button>
      </div>
      <div className="bg-ta-card rounded-xl border border-ta-danger/30 p-10 text-center">
        <div className="text-ta-danger text-3xl font-bold mb-2">分析失败</div>
        <div className="text-ta-muted text-sm mb-4">{task.ticker} · {task.analysis_date}</div>
        <div className="text-ta-text text-sm">{task.error}</div>
      </div>
    </div>
  )
}

function ReportRunning({ task, onBack }: { task: TaskInfo; onBack: () => void }) {
  const statusMap: Record<string, string> = {
    pending: '等待调度',
    queued: '排队中',
    running: '分析执行中',
  }
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="text-ta-muted hover:text-ta-text text-sm transition-colors">← 返回列表</button>
        <div className="text-ta-muted text-sm font-mono">{task.ticker} · {task.analysis_date}</div>
      </div>
      <div className="bg-ta-card rounded-xl border border-ta-accent/30 p-10 text-center">
        <div className="text-ta-accent text-2xl font-bold mb-2">分析正在进行中</div>
        <div className="text-ta-muted text-sm mb-4">
          状态: {statusMap[task.status] || task.status}
        </div>
        <div className="text-ta-muted text-sm">
          请稍后刷新页面查看完整报告
        </div>
      </div>
    </div>
  )
}

function ReportCompleted({ task, onBack }: { task: TaskInfo; onBack: () => void }) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="text-ta-muted hover:text-ta-text text-sm transition-colors">← 返回列表</button>
        <div className="text-ta-muted text-sm font-mono">{task.ticker} · {task.analysis_date}</div>
      </div>

      {/* Title card */}
      <div className="bg-ta-card rounded-xl border border-ta-accent/30 p-10 text-center">
        <div className="text-ta-accent text-3xl font-bold mb-2">分析报告</div>
        <div className="text-ta-muted text-sm">{task.ticker} · {task.analysis_date}</div>
      </div>

      {/* Dynamic report sections */}
      <DynamicReportSections taskId={task.task_id} />
    </div>
  )
}

// File name → Chinese label mapping
const fileLabels: Record<string, string> = {
  'complete_report': '完整报告',
  'market_report': '市场分析报告',
  'sentiment_report': '情感分析报告',
  'news_report': '新闻分析报告',
  'fundamentals_report': '基本面分析报告',
  'investment_plan': '投资计划',
  'trader_investment_plan': '交易员投资计划',
  'final_trade_decision': '最终交易决策',
  'risk_debate_state': '风控评估报告',
  'research_report': '研究报告',
  'debate_summary': '辩论总结',
}

// Logical group ordering for display
const sectionGroups: { key: string; label: string; files: string[] }[] = [
  { key: 'complete', label: '完整报告', files: ['complete_report'] },
  { key: 'decision', label: '最终决策', files: ['final_trade_decision', 'trader_investment_plan', 'investment_plan'] },
  { key: 'analysts', label: '分析师报告', files: ['market_report', 'sentiment_report', 'news_report'] },
  { key: 'fundamentals', label: '基本面', files: ['fundamentals_report'] },
  { key: 'research', label: '研究分析', files: ['research_report', 'debate_summary'] },
  { key: 'risk', label: '风控评估', files: ['risk_debate_state'] },
]

function DynamicReportSections({ taskId }: { taskId: string }) {
  const [files, setFiles] = useState<string[]>([])
  const [contents, setContents] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadDiskFiles = () =>
      fetch(`/api/task/${taskId}/report-dir/`)
        .then(r => {
          if (!r.ok) throw new Error('not found')
          return r.json()
        })
        .then(data => {
          const fileList: string[] = data.files || []
          setFiles(fileList)
          // Load all files in parallel
          const promises = fileList.map(f =>
            fetch(`/api/task/${taskId}/report/${f}`)
              .then(r => r.ok ? r.text() : Promise.resolve(''))
              .then(text => ({ file: f, content: text }))
          )
          return Promise.all(promises).then(results => {
            const map: Record<string, string> = {}
            results.forEach(r => { map[r.file] = r.content })
            setContents(map)
          })
        })

    const loadMemoryFallback = () =>
      fetch(`/api/task/${taskId}/report-dir/`)
        .then(r => r.ok ? r.json() : Promise.reject(new Error('not found')))
        .then(data => {
          if (data.source !== 'memory' || !data.files?.length) throw new Error('no memory data')
          const fileList: string[] = data.files || []
          setFiles(fileList)
          const promises = fileList.map(f =>
            fetch(`/api/task/${taskId}/report-memory/${f.replace('.md', '')}`)
              .then(r => r.ok ? r.text() : Promise.resolve(''))
              .then(text => ({ file: f, content: text }))
          )
          return Promise.all(promises).then(results => {
            const map: Record<string, string> = {}
            results.forEach(r => { map[r.file] = r.content })
            setContents(map)
          })
        })

    // Try disk first, then memory fallback
    loadDiskFiles()
      .catch(() => loadMemoryFallback())
      .catch(() => setFiles([]))
      .finally(() => setLoading(false))
  }, [taskId])

  if (loading) return <div className="text-ta-muted py-4 text-center">加载报告文件...</div>
  if (files.length === 0) return <div className="text-ta-muted py-4 text-center">暂无报告文件</div>

  // Build groups: only show groups that have at least one file on disk
  const baseNames = files.map(f => f.replace('.md', ''))

  // Also catch any files not in predefined groups
  const groupedFiles = new Set<string>()
  const groupsToShow = sectionGroups.filter(g => {
    const matched = g.files.filter(f => baseNames.includes(f))
    matched.forEach(f => groupedFiles.add(f + '.md'))
    return matched.length > 0
  })

  // Show remaining files as "other"
  const otherFiles = files.filter(f => !groupedFiles.has(f))

  return (
    <div className="space-y-3">
      {groupsToShow.map(group => {
        const groupFiles = group.files
          .filter(f => baseNames.includes(f))
          .map(f => f + '.md')
          .filter(f => files.includes(f))
        return (
          <ReportSection key={group.key} label={group.label} taskId={taskId} files={groupFiles} contents={contents} />
        )
      })}
      {otherFiles.length > 0 && (
        <ReportSection label="其他" taskId={taskId} files={otherFiles} contents={contents} />
      )}
    </div>
  )
}

function ReportSection({ label, taskId, files, contents }: { label: string; taskId: string; files: string[]; contents: Record<string, string> }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-ta-card rounded-xl border border-ta-border overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-4 text-left flex items-center justify-between hover:bg-ta-bg transition-colors"
      >
        <span className="text-ta-text font-medium">{label}</span>
        <span className="text-ta-muted">{expanded ? '▼' : '▶'}</span>
      </button>
      {expanded && (
        <div className="px-6 pb-6 border-t border-ta-border">
          <div className="space-y-4 mt-4">
            {files.map(f => {
              const label = fileLabels[f.replace('.md', '')] || f.replace('.md', '')
              return (
                <div key={f}>
                  {files.length > 1 && (
                    <h4 className="text-ta-accent font-medium mb-2">{label}</h4>
                  )}
                  <div className="markdown-content text-sm text-ta-text leading-relaxed">
                    <ReactMarkdown>{contents[f] || ''}</ReactMarkdown>
                  </div>
                </div>
              )
            })}
            {files.length === 1 && (
              <div className="markdown-content text-sm text-ta-text leading-relaxed">
                <ReactMarkdown>{contents[files[0]] || ''}</ReactMarkdown>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
