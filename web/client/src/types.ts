export type TaskStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed'
export type RunMode = 'streaming' | 'background'

export interface TaskInfo {
  task_id: string
  ticker: string
  analysis_date: string
  status: TaskStatus
  created_at: string
  completed_at: string | null
  error: string | null
  report_path?: string | null
}

export interface AnalyzeRequest {
  ticker: string
  analysis_date?: string
  mode: RunMode
}

export interface TaskResponse {
  task_id: string
  status: TaskStatus
  message: string
}

export interface SSEEvent {
  event: string
  data: Record<string, unknown>
}

export interface ReportSection {
  section: string
  content: string
}

export interface AgentStatus {
  agent: string
  status: 'pending' | 'in_progress' | 'completed'
}
