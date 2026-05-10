import { useState, useEffect, useCallback } from 'react'
import { getHeatmap } from '../api'
import type { HeatmapStock, HeatmapResponse } from '../types'

type MarketTab = 'us' | 'a_share'

const tabLabels: Record<MarketTab, string> = {
  us: '美股',
  a_share: 'A股',
}

function changeColor(pct: number): string {
  if (pct > 0) return 'bg-green-500/10 border-green-500/30'
  if (pct < 0) return 'bg-ta-danger/10 border-ta-danger/30'
  return 'bg-ta-card border-ta-border'
}

function changeTextColor(pct: number): string {
  if (pct > 0) return 'text-green-400'
  if (pct < 0) return 'text-ta-danger'
  return 'text-ta-muted'
}

function StockCard({ stock }: { stock: HeatmapStock }) {
  const pctStr = stock.change_pct > 0 ? `+${stock.change_pct.toFixed(2)}%` : `${stock.change_pct.toFixed(2)}%`

  return (
    <div className={`rounded-lg border p-3 text-center ${changeColor(stock.change_pct)} transition-colors`}>
      <div className="font-mono text-xs text-ta-accent truncate">{stock.ticker}</div>
      <div className="text-xs text-ta-muted truncate mt-0.5">{stock.name}</div>
      <div className={`font-mono text-sm font-medium mt-1 ${changeTextColor(stock.change_pct)}`}>
        {pctStr}
      </div>
      {stock.price !== '-' && (
        <div className="text-xs text-ta-text/70 mt-0.5">{stock.price}</div>
      )}
    </div>
  )
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mt-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="rounded-lg border border-ta-border bg-ta-card p-3 animate-pulse">
          <div className="h-3 bg-ta-border rounded w-1/2 mx-auto" />
          <div className="h-2 bg-ta-border rounded w-2/3 mx-auto mt-2" />
          <div className="h-4 bg-ta-border rounded w-1/3 mx-auto mt-2" />
        </div>
      ))}
    </div>
  )
}

export default function MarketHeatmap() {
  const [market, setMarket] = useState<MarketTab>('us')
  const [data, setData] = useState<HeatmapResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await getHeatmap()
      setData(result)
    } catch (e: any) {
      setError(e.message || 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const marketData = data?.[market]
  const sectors = marketData ? Object.entries(marketData) : []

  if (loading) {
    return (
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-ta-text">市场热力图</h2>
          <div className="flex gap-2">
            {(Object.keys(tabLabels) as MarketTab[]).map((key) => (
              <button
                key={key}
                className="px-3 py-1 text-sm rounded-lg bg-ta-card text-ta-muted"
              >
                {tabLabels[key]}
              </button>
            ))}
          </div>
        </div>
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="mb-4">
            <div className="h-4 bg-ta-border rounded w-16 animate-pulse" />
            <SkeletonGrid />
          </div>
        ))}
      </section>
    )
  }

  if (error) {
    return (
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-ta-text">市场热力图</h2>
          <button
            onClick={fetchData}
            className="text-sm px-3 py-1 rounded-lg bg-ta-accent/10 border border-ta-accent/30 text-ta-accent hover:bg-ta-accent/20"
          >
            重试
          </button>
        </div>
        <div className="bg-ta-card rounded-xl border border-ta-border p-8 text-center">
          <p className="text-ta-muted">加载失败: {error}</p>
        </div>
      </section>
    )
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-ta-text">市场热力图</h2>
        <div className="flex gap-2">
          {(Object.keys(tabLabels) as MarketTab[]).map((key) => (
            <button
              key={key}
              onClick={() => setMarket(key)}
              className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                market === key
                  ? 'bg-ta-accent text-ta-bg font-medium'
                  : 'text-ta-muted hover:bg-ta-card'
              }`}
            >
              {tabLabels[key]}
            </button>
          ))}
        </div>
      </div>

      {sectors.length === 0 ? (
        <div className="bg-ta-card rounded-xl border border-ta-border p-8 text-center">
          <p className="text-ta-muted">暂无数据</p>
        </div>
      ) : (
        sectors.map(([sector, stocks]) => (
          <div key={sector} className="mb-5">
            <h3 className="text-sm font-medium text-ta-muted mb-2">{sector}</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {stocks.map((s) => (
                <StockCard key={s.ticker} stock={s} />
              ))}
            </div>
          </div>
        ))
      )}
    </section>
  )
}
