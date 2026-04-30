import { useState } from 'react'
import type { RunMode, TaskResponse } from '../types'
import { submitAnalysis } from '../api'

interface Props {
  onStart: (response: TaskResponse) => void
}

export default function NewAnalysis({ onStart }: Props) {
  const [ticker, setTicker] = useState('')
  const [mode, setMode] = useState<RunMode>('streaming')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!ticker.trim()) return
    setLoading(true)
    try {
      const res = await submitAnalysis({ ticker, mode })
      // If validation failed, show error
      if (res.status === 'failed' && !res.task_id) {
        alert(res.message)
      } else {
        onStart(res)
      }
    } catch (err) {
      alert('提交失败: ' + (err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="bg-ta-card rounded-xl border border-ta-border p-8">
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm text-ta-muted mb-2">股票代码</label>
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="NVDA"
            className="w-full bg-ta-bg border border-ta-border rounded-lg px-4 py-3 text-ta-text font-mono focus:outline-none focus:border-ta-accent transition-colors"
          />
          <p className="text-xs text-ta-muted mt-1">仅支持美股（如 NVDA, AAPL）</p>
        </div>

        <div className="flex gap-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              checked={mode === 'streaming'}
              onChange={() => setMode('streaming')}
              className="accent-ta-accent"
            />
            <span className="text-sm text-ta-text">⚡ 实时流式分析</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              checked={mode === 'background'}
              onChange={() => setMode('background')}
              className="accent-ta-accent"
            />
            <span className="text-sm text-ta-text">○ 后台提交</span>
          </label>
        </div>

        <button
          type="submit"
          disabled={loading || !ticker.trim()}
          className="w-full bg-ta-accent text-ta-bg font-semibold py-3 rounded-lg hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          {loading ? '提交中...' : '智能分析'}
        </button>
      </form>
    </section>
  )
}
