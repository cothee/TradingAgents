import type { TaskInfo } from '../types'

interface Props {
  tasks: TaskInfo[]
  onSelect: (taskId: string) => void
}

const statusLabel: Record<string, string> = {
  pending: '等待中',
  queued: '排队中',
  running: '分析中',
  completed: '已完成',
  failed: '失败',
}

const statusColor: Record<string, string> = {
  pending: 'text-ta-warning',
  queued: 'text-ta-warning',
  running: 'text-ta-accent',
  completed: 'text-green-400',
  failed: 'text-ta-danger',
}

export default function TaskList({ tasks, onSelect }: Props) {
  if (tasks.length === 0) return null

  return (
    <section>
      <h2 className="text-xl font-semibold text-ta-text mb-4">分析报告</h2>
      <div className="bg-ta-card rounded-xl border border-ta-border overflow-x-auto">
        <table className="w-full text-sm min-w-[480px]">
          <thead>
            <tr className="border-b border-ta-border text-ta-muted">
              <th className="text-left px-6 py-3 font-medium">代码</th>
              <th className="text-left px-6 py-3 font-medium">状态</th>
              <th className="text-left px-6 py-3 font-medium">时间</th>
              <th className="text-right px-6 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr
                key={task.task_id}
                className="border-b border-ta-border hover:bg-ta-bg transition-colors cursor-pointer"
                onClick={() => onSelect(task.task_id)}
              >
                <td className="px-6 py-3 font-mono text-ta-accent">{task.ticker}</td>
                <td className={`px-6 py-3 ${statusColor[task.status] || ''}`}>
                  {statusLabel[task.status] || task.status}
                </td>
                <td className="px-6 py-3 text-ta-muted">
                  {task.completed_at || task.created_at}
                </td>
                <td className="px-6 py-3 text-right text-ta-accent hover:underline">
                  {task.status === 'completed' ? '查看报告' : '查看'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
