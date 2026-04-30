export default function Header() {
  return (
    <header className="border-b border-ta-border backdrop-blur-sm bg-ta-bg/80 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-ta-accent font-bold text-lg tracking-wider">TAURIC</span>
          <span className="text-ta-muted text-sm">|</span>
          <span className="text-ta-text font-medium">TradingAgents</span>
        </div>
        <div className="text-ta-muted text-xs">
          智能交易分析平台
        </div>
      </div>
    </header>
  )
}
