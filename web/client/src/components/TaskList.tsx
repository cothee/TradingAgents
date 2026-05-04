import { useState } from 'react'
import type { TaskInfo } from '../types'

function detectMarket(ticker: string): 'a_share' | 'us' {
  const t = ticker.trim()
  if (t.endsWith('.SS') || t.endsWith('.SZ') || t.endsWith('.SHA') || t.endsWith('.SHE')) {
    return 'a_share'
  }
  if (t.length === 6 && /^\d+$/.test(t)) {
    return 'a_share'
  }
  return 'us'
}

type MarketFilter = 'all' | 'a_share' | 'us'

const marketLabels: Record<MarketFilter, string> = {
  all: '全部',
  a_share: 'A股',
  us: '美股',
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

interface Props {
  tasks: TaskInfo[]
  onSelect: (taskId: string) => void
}

export default function TaskList({ tasks, onSelect }: Props) {
  const [marketFilter, setMarketFilter] = useState<MarketFilter>('all')

  const filteredTasks = tasks.filter(task => {
    if (marketFilter === 'all') return true
    return detectMarket(task.ticker) === marketFilter
  })

  if (tasks.length === 0) return null

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-ta-text">分析报告</h2>
        <div className="flex gap-2">
          {(Object.keys(marketLabels) as MarketFilter[]).map((key) => (
            <button
              key={key}
              onClick={() => setMarketFilter(key)}
              className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                marketFilter === key
                  ? 'bg-ta-accent text-ta-bg font-medium'
                  : 'text-ta-muted hover:bg-ta-card'
              }`}
            >
              {marketLabels[key]}
            </button>
          ))}
        </div>
      </div>
      <div className="bg-ta-card rounded-xl border border-ta-border overflow-x-auto">
        {filteredTasks.length === 0 ? (
          <p className="text-ta-muted text-sm py-8 text-center">暂无{marketLabels[marketFilter]}报告</p>
        ) : (
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
              {filteredTasks.map((task) => (
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
        )}
      </div>
    </section>
  )
}
