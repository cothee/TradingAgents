import { useState, useEffect, useRef, useCallback } from 'react'
import type { SSEEvent, ReportSection, AgentStatus as AgentStatusType } from '../types'
import { subscribeToTask } from '../api'
import AgentChain from './AgentChain'

interface Props {
  taskId: string
  onComplete: () => void
  onBack: () => void
}

export default function LiveProgress({ taskId, onComplete, onBack }: Props) {
  const [agents, setAgents] = useState<Record<string, AgentStatusType>>({})
  const [sections, setSections] = useState<ReportSection[]>([])
  const [progress, setProgress] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [ticker, setTicker] = useState('')
  const esRef = useRef<EventSource | null>(null)
  const startTimeRef = useRef(Date.now())

  // Elapsed timer
  useEffect(() => {
    const interval = setInterval(() => setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000)), 1000)
    return () => clearInterval(interval)
  }, [])

  const TOTAL_AGENTS = 8

  const handleEvent = useCallback((event: SSEEvent) => {
    switch (event.event) {
      case 'task_started':
        setTicker((event.data as any).ticker || '')
        break
      case 'agent_progress': {
        const d = event.data as any
        setAgents(prev => {
          const next = { ...prev, [d.agent]: { agent: d.agent, status: d.status } }
          // Update progress based on completed agents
          const completed = Object.values(next).filter((a: any) => a.status === 'completed').length
          setProgress(Math.min(Math.floor((completed / TOTAL_AGENTS) * 95), 95))
          return next
        })
        break
      }
      case 'report_section': {
        const d = event.data as any
        setSections(prev => {
          const existing = prev.findIndex(s => s.section === d.section)
          if (existing >= 0) {
            const next = [...prev]
            next[existing] = { section: d.section, content: d.content }
            return next
          }
          return [...prev, { section: d.section, content: d.content }]
        })
        break
      }
      case 'task_completed':
        setProgress(100)
        setTimeout(onComplete, 1500)
        break
      case 'task_failed':
        alert('分析失败: ' + (event.data as any).error)
        onBack()
        break
    }
  }, [onComplete, onBack])

  useEffect(() => {
    esRef.current = subscribeToTask(taskId, handleEvent)
    return () => { esRef.current?.close() }
  }, [taskId, handleEvent])

  const formatTime = (s: number) => `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`

  return (
    <div className="space-y-6">
      {/* Progress bar */}
      <div className="bg-ta-card rounded-xl border border-ta-border p-6">
        <div className="flex items-center justify-between mb-3">
          <button onClick={onBack} className="text-ta-muted hover:text-ta-text text-sm transition-colors">← 返回</button>
          <span className="text-ta-text font-mono font-medium">{ticker || '分析中...'}</span>
          <span className="text-ta-muted font-mono text-sm">⏱ {formatTime(elapsed)}</span>
        </div>
        <div className="w-full bg-ta-bg rounded-full h-2 overflow-hidden">
          <div
            className="h-full bg-ta-accent rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="text-ta-muted text-xs mt-1 text-right">{progress}%</div>
      </div>

      {/* Agent chain */}
      <div className="bg-ta-card rounded-xl border border-ta-border p-6">
        <h3 className="text-sm text-ta-muted mb-4">Agent 执行链</h3>
        <AgentChain agents={agents} />
      </div>

      {/* Real-time report */}
      <div className="bg-ta-card rounded-xl border border-ta-border p-6">
        <h3 className="text-sm text-ta-muted mb-4">实时报告输出</h3>
        <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
          {sections.map((s) => (
            <div key={s.section} className="border-l-2 border-ta-accent pl-4">
              <h4 className="text-ta-accent font-medium mb-2">{s.section}</h4>
              <div className="markdown-content text-sm text-ta-text whitespace-pre-wrap leading-relaxed">
                {s.content}
              </div>
            </div>
          ))}
          {sections.length === 0 && (
            <div className="text-ta-muted text-center py-8">等待分析数据...</div>
          )}
        </div>
      </div>
    </div>
  )
}
