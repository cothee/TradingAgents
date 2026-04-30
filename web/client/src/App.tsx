import { useState, useEffect, useCallback } from 'react'
import type { TaskInfo, TaskResponse } from './types'
import { listRecent } from './api'
import Header from './components/Header'
import NewAnalysis from './components/NewAnalysis'
import TaskList from './components/TaskList'
import LiveProgress from './components/LiveProgress'
import ReportView from './components/ReportView'

type View = 'home' | 'progress' | 'report'

export default function App() {
  const [view, setView] = useState<View>('home')
  const [tasks, setTasks] = useState<TaskInfo[]>([])
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)

  const loadTasks = useCallback(async () => {
    try {
      const recent = await listRecent()
      setTasks(recent)
    } catch (e) {
      console.error('Failed to load tasks:', e)
    }
  }, [])

  useEffect(() => {
    loadTasks()
    const interval = setInterval(loadTasks, 10000)
    return () => clearInterval(interval)
  }, [loadTasks])

  const handleAnalysisStart = (response: TaskResponse) => {
    setActiveTaskId(response.task_id)
    // If the task is already completed, go directly to report view
    if (response.status === 'completed') {
      setView('report')
    } else {
      setView('progress')
    }
  }

  const handleTaskSelect = (taskId: string) => {
    setActiveTaskId(taskId)
    setView('report')
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="max-w-6xl mx-auto px-6 py-8">
        {view === 'home' && (
          <>
            <NewAnalysis onStart={handleAnalysisStart} />
            <div className="mt-10">
              <TaskList tasks={tasks} onSelect={handleTaskSelect} />
            </div>
          </>
        )}
        {view === 'progress' && activeTaskId && (
          <LiveProgress
            taskId={activeTaskId}
            onComplete={() => setView('report')}
            onBack={() => setView('home')}
          />
        )}
        {view === 'report' && activeTaskId && (
          <ReportView taskId={activeTaskId} onBack={() => setView('home')} />
        )}
      </main>
    </div>
  )
}
