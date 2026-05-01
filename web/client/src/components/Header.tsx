interface HeaderProps {
  onHome?: () => void
}

export default function Header({ onHome }: HeaderProps) {
  return (
    <header className="border-b border-ta-border backdrop-blur-sm bg-ta-bg/80 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {onHome ? (
            <button onClick={onHome} className="text-ta-accent font-bold text-lg tracking-wider hover:opacity-80 transition-opacity cursor-pointer">TradingCube</button>
          ) : (
            <span className="text-ta-accent font-bold text-lg tracking-wider">TradingCube</span>
          )}
        </div>
        <div className="text-ta-muted text-xs">
          智能交易分析平台
        </div>
      </div>
    </header>
  )
}
