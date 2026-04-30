import type {
  AnalyzeRequest,
  TaskInfo,
  TaskResponse,
  SSEEvent,
} from './types'

const API_BASE = '/api'

export async function submitAnalysis(req: AnalyzeRequest): Promise<TaskResponse> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function getTask(taskId: string): Promise<TaskInfo> {
  const res = await fetch(`${API_BASE}/task/${taskId}`)
  if (!res.ok) throw new Error(`Task not found: ${taskId}`)
  return res.json()
}

export async function listRecent(): Promise<TaskInfo[]> {
  const res = await fetch(`${API_BASE}/tasks/recent`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  const data = await res.json()
  return data.tasks
}

export function subscribeToTask(taskId: string, onEvent: (event: SSEEvent) => void): EventSource {
  const es = new EventSource(`${API_BASE}/task/${taskId}/events`)

  es.addEventListener('task_started', (e) => onEvent({ event: 'task_started', data: JSON.parse(e.data) }))
  es.addEventListener('agent_progress', (e) => onEvent({ event: 'agent_progress', data: JSON.parse(e.data) }))
  es.addEventListener('report_section', (e) => onEvent({ event: 'report_section', data: JSON.parse(e.data) }))
  es.addEventListener('task_completed', (e) => onEvent({ event: 'task_completed', data: JSON.parse(e.data) }))
  es.addEventListener('task_failed', (e) => onEvent({ event: 'task_failed', data: JSON.parse(e.data) }))
  es.addEventListener('task_status', (e) => onEvent({ event: 'task_status', data: JSON.parse(e.data) }))
  es.addEventListener('heartbeat', (e) => onEvent({ event: 'heartbeat', data: JSON.parse(e.data) }))

  return es
}
