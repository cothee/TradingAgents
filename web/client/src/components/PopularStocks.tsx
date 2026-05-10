import { useState, useEffect, useCallback } from 'react'
import { getPopularStocks } from '../api'
import type { PopularStock } from '../types'

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

function detectMarket(ticker: string): string {
  const t = ticker.trim()
  if (/^\d{6}$/.test(t)) return 'A股'
  return '美股'
}

interface Props {
  onSelect: (taskId: string) => void
}

export default function PopularStocks({ onSelect }: Props) {
  const [stocks, setStocks] = useState<PopularStock[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await getPopularStocks()
      setStocks(result)
    } catch (e: any) {
      setError(e.message || 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  if (loading) {
    return (
      <section>
        <h2 className="text-xl font-semibold text-ta-text mb-4">热门排行</h2>
        <div className="bg-ta-card rounded-xl border border-ta-border p-8 animate-pulse">
          <div className="h-4 bg-ta-border rounded w-1/2 mx-auto" />
        </div>
      </section>
    )
  }

  if (error) {
    return (
      <section>
        <h2 className="text-xl font-semibold text-ta-text mb-4">热门排行</h2>
        <div className="bg-ta-card rounded-xl border border-ta-border p-8 text-center">
          <p className="text-ta-muted mb-3">加载失败: {error}</p>
          <button
            onClick={fetchData}
            className="text-sm px-3 py-1 rounded-lg bg-ta-accent/10 border border-ta-accent/30 text-ta-accent hover:bg-ta-accent/20"
          >
            重试
          </button>
        </div>
      </section>
    )
  }

  if (stocks.length === 0) return null

  return (
    <section>
      <h2 className="text-xl font-semibold text-ta-text mb-4">热门排行</h2>
      <div className="bg-ta-card rounded-xl border border-ta-border overflow-x-auto">
        {/* Desktop table */}
        <table className="w-full text-sm min-w-[480px] hidden sm:table">
          <thead>
            <tr className="border-b border-ta-border text-ta-muted">
              <th className="text-left px-6 py-3 font-medium w-12">#</th>
              <th className="text-left px-6 py-3 font-medium">代码</th>
              <th className="text-left px-6 py-3 font-medium">市场</th>
              <th className="text-left px-6 py-3 font-medium">最新状态</th>
              <th className="text-right px-6 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((s, i) => (
              <tr
                key={s.ticker}
                className="border-b border-ta-border hover:bg-ta-bg transition-colors cursor-pointer"
                onClick={() => s.latest_task_id && onSelect(s.latest_task_id)}
              >
                <td className="px-6 py-3 text-ta-muted font-medium">{i + 1}</td>
                <td className="px-6 py-3 font-mono text-ta-accent">{s.ticker}</td>
                <td className="px-6 py-3 text-ta-muted">{detectMarket(s.ticker)}</td>
                <td className={`px-6 py-3 ${statusColor[s.latest_status] || 'text-ta-muted'}`}>
                  {statusLabel[s.latest_status] || s.latest_status}
                </td>
                <td className="px-6 py-3 text-right text-ta-accent hover:underline">
                  查看
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Mobile card list */}
        <div className="sm:hidden divide-y divide-ta-border">
          {stocks.map((s, i) => (
            <div
              key={s.ticker}
              className="px-4 py-3 flex items-center cursor-pointer hover:bg-ta-bg transition-colors"
              onClick={() => s.latest_task_id && onSelect(s.latest_task_id)}
            >
              <span className="text-ta-muted font-medium w-8 text-sm">{i + 1}</span>
              <div className="flex-1 min-w-0">
                <div className="font-mono text-ta-accent text-sm">{s.ticker}</div>
                <div className="text-xs text-ta-muted">
                  {detectMarket(s.ticker)}
                </div>
              </div>
              <span className={`text-xs ${statusColor[s.latest_status] || 'text-ta-muted'} mr-3`}>
                {statusLabel[s.latest_status] || s.latest_status}
              </span>
              <span className="text-ta-accent text-sm">查看</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
