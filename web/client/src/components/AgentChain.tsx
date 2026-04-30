import type { AgentStatus as AgentStatusType } from '../types'

interface Agent {
  name: string
  icon: string
}

const AGENT_CHAIN: Agent[] = [
  { name: 'Market Analyst', icon: '📊' },
  { name: 'Social Analyst', icon: '💬' },
  { name: 'News Analyst', icon: '📰' },
  { name: 'Fundamentals Analyst', icon: '📋' },
  { name: 'Research Team', icon: '⚖️' },
  { name: 'Trader', icon: '💹' },
  { name: 'Risk Management', icon: '🛡️' },
  { name: 'Portfolio Manager', icon: '🎯' },
]

interface Props {
  agents: Record<string, AgentStatusType>
}

export default function AgentChain({ agents }: Props) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
      {AGENT_CHAIN.map((agent, i) => {
        const status = agents[agent.name]?.status || 'pending'
        const color = status === 'completed' ? 'border-green-500 bg-green-500/10'
          : status === 'in_progress' ? 'border-ta-accent bg-ta-accent/10 animate-pulse'
          : 'border-ta-border'

        return (
          <div
            key={agent.name}
            className={`relative border rounded-lg p-3 text-center transition-all ${color}`}
          >
            {i > 0 && (
              <div className="absolute -left-2 top-1/2 -translate-y-1/2 text-ta-muted text-xs z-10 hidden lg:block">→</div>
            )}
            <div className="text-xl mb-1">{agent.icon}</div>
            <div className="text-xs text-ta-text font-medium truncate">{agent.name}</div>
            <div className="text-xs mt-1 text-ta-muted">
              {status === 'completed' ? '✓' : status === 'in_progress' ? '⚡' : '○'}
            </div>
          </div>
        )
      })}
    </div>
  )
}
