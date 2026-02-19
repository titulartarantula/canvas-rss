interface DeploymentTimelineProps {
  status: string
  firstSeen: string | null
  betaDate: string | null
  productionDate: string | null
  deprecationDate: string | null
}

type Stage = {
  key: string
  label: string
  date: string | null
  isActive: boolean
  isComplete: boolean
  isCurrent: boolean
}

export default function DeploymentTimeline({
  status, firstSeen, betaDate, productionDate, deprecationDate,
}: DeploymentTimelineProps) {
  const normalizedStatus = status?.toLowerCase().replace(/\s+/g, '_') || 'pending'
  const today = new Date().toISOString().split('T')[0]
  const stages: Stage[] = []

  stages.push({
    key: 'announced', label: 'Announced', date: firstSeen,
    isActive: true, isComplete: !!firstSeen, isCurrent: normalizedStatus === 'pending',
  })
  stages.push({
    key: 'beta', label: 'Beta', date: betaDate,
    isActive: !!betaDate || normalizedStatus === 'beta',
    isComplete: !!betaDate && betaDate <= today && normalizedStatus !== 'beta',
    isCurrent: normalizedStatus === 'beta',
  })
  const isProdPhase = ['optional', 'default_on', 'feature_preview', 'preview'].includes(normalizedStatus)
  stages.push({
    key: 'production', label: productionDate ? 'Production' : 'Optional', date: productionDate,
    isActive: !!productionDate || isProdPhase,
    isComplete: !!productionDate && productionDate <= today && !isProdPhase,
    isCurrent: isProdPhase,
  })
  stages.push({
    key: 'released', label: 'Released', date: normalizedStatus === 'released' ? productionDate : null,
    isActive: normalizedStatus === 'released', isComplete: normalizedStatus === 'released',
    isCurrent: normalizedStatus === 'released',
  })
  if (deprecationDate || normalizedStatus === 'deprecated') {
    stages.push({
      key: 'deprecated', label: 'Deprecated', date: deprecationDate,
      isActive: true, isComplete: true, isCurrent: normalizedStatus === 'deprecated',
    })
  }

  return (
    <div className="relative">
      <div className="absolute top-3.5 left-0 right-0 h-px bg-zinc-700" />
      <div
        className="absolute top-3.5 left-0 h-px bg-gradient-to-r from-status-beta via-status-optional to-status-released transition-all duration-500"
        style={{ width: `${getProgressWidth(stages)}%` }}
      />
      <div className="relative flex justify-between">
        {stages.map((stage, index) => (
          <div key={stage.key} className={`flex flex-col ${index === 0 ? 'items-start' : index === stages.length - 1 ? 'items-end' : 'items-center'}`}>
            <div className={`
              relative z-10 w-7 h-7 rounded-full flex items-center justify-center transition-all duration-300
              ${stage.isCurrent
                ? 'bg-surface-2 border-2 border-signal-blue ring-4 ring-signal-blue/20'
                : stage.isComplete
                  ? getStageColor(stage.key)
                  : stage.isActive
                    ? 'bg-surface-2 border-2 border-zinc-600'
                    : 'bg-surface-3 border-2 border-zinc-700'
              }
            `}>
              {stage.isComplete && !stage.isCurrent && (
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              )}
              {stage.isCurrent && (
                <div className="w-2 h-2 rounded-full bg-signal-blue animate-pulse-dot" />
              )}
            </div>
            <div className={`mt-2 ${index === 0 ? 'text-left' : index === stages.length - 1 ? 'text-right' : 'text-center'}`}>
              <p className={`text-xs font-mono font-medium uppercase tracking-wider ${
                stage.isCurrent ? 'text-signal-blue' : stage.isComplete || stage.isActive ? 'text-zinc-400' : 'text-zinc-500'
              }`}>
                {stage.label}
              </p>
              {stage.date && (
                <p className="mt-0.5 text-xs font-mono text-zinc-500">{formatDate(stage.date)}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function getProgressWidth(stages: Stage[]): number {
  const activeIndex = stages.findIndex(s => s.isCurrent)
  if (activeIndex === -1) {
    const completeCount = stages.filter(s => s.isComplete).length
    return completeCount === stages.length ? 100 : (completeCount / (stages.length - 1)) * 100
  }
  if (activeIndex === 0) return 0
  return (activeIndex / (stages.length - 1)) * 100
}

function getStageColor(key: string): string {
  switch (key) {
    case 'announced': return 'bg-status-pending'
    case 'beta': return 'bg-status-beta'
    case 'production': return 'bg-status-optional'
    case 'released': return 'bg-status-released'
    case 'deprecated': return 'bg-status-deprecated'
    default: return 'bg-zinc-600'
  }
}

function formatDate(dateStr: string): string {
  const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
  const d = match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function DeploymentTimelineSkeleton() {
  return (
    <div className="card p-5">
      <div className="relative">
        <div className="absolute top-3.5 left-0 right-0 h-px bg-zinc-700" />
        <div className="relative flex justify-between">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex flex-col items-center">
              <div className="skeleton w-7 h-7 rounded-full" />
              <div className="mt-2 skeleton h-3 w-14" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
