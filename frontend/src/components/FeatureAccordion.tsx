import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { featuresApi } from '../api/client'
import type { Feature } from '../types'
import StatusPill, { DatePill } from './StatusPill'
import {
  ChevronDownIcon,
  ChevronUpIcon,
  ArrowRightIcon,
  AdjustmentsIcon,
  CogIcon,
} from './icons'
import InfoTooltip from './InfoTooltip'

interface FeatureAccordionProps {
  feature: Feature
  defaultOpen?: boolean
}

export default function FeatureAccordion({ feature, defaultOpen = false }: FeatureAccordionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  const optionCount = feature.option_count || 0
  const settingCount = feature.setting_count || 0
  const totalCount = optionCount + settingCount
  const hasContent = totalCount > 0

  return (
    <div className={`border-b border-zinc-800/50 last:border-b-0 ${isOpen ? 'bg-surface-3/20' : ''}`}>
      {/* Accordion header */}
      <button
        onClick={() => hasContent && setIsOpen(!isOpen)}
        className={`
          w-full flex items-center gap-4 px-4 py-3 text-left transition-colors
          ${hasContent ? 'hover:bg-surface-3/30 cursor-pointer' : 'cursor-default'}
        `}
        aria-expanded={isOpen}
        disabled={!hasContent}
      >
        {/* Expand indicator */}
        <div className="w-4 flex-shrink-0">
          {hasContent ? (
            isOpen
              ? <ChevronUpIcon className="w-3.5 h-3.5 text-zinc-400" />
              : <ChevronDownIcon className="w-3.5 h-3.5 text-zinc-600" />
          ) : (
            <span className="block w-1 h-1 rounded-full bg-zinc-700 mx-auto" />
          )}
        </div>

        {/* Feature name */}
        <div className="flex-1 min-w-0">
          <span className={`text-sm ${hasContent ? 'text-zinc-300' : 'text-zinc-500'} transition-colors`}>
            {feature.name}
          </span>
        </div>

        {/* Status summary */}
        {feature.status_summary && (
          <div className="hidden sm:flex items-center gap-2 flex-shrink-0">
            {feature.status_summary.split(',').map((part, idx) => (
              <span key={idx} className={`text-xs font-mono ${getStatusTextColor(part.trim())}`}>
                {part.trim()}
              </span>
            ))}
          </div>
        )}

        {/* Counts */}
        <div className="flex items-center gap-3 flex-shrink-0">
          {optionCount > 0 && (
            <span className="inline-flex items-center gap-1 text-xs font-mono text-zinc-400">
              <AdjustmentsIcon className="w-3 h-3" />
              {optionCount}
            </span>
          )}
          {settingCount > 0 && (
            <span className="inline-flex items-center gap-1 text-xs font-mono text-zinc-400">
              <CogIcon className="w-3 h-3" />
              {settingCount}
            </span>
          )}
          {!hasContent && (
            <span className="text-xs font-mono text-zinc-600">--</span>
          )}
        </div>
      </button>

      {/* Accordion content */}
      {isOpen && hasContent && (
        <FeatureAccordionContent featureId={feature.feature_id} featureName={feature.name} />
      )}
    </div>
  )
}

function FeatureAccordionContent({ featureId, featureName }: { featureId: string; featureName: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['feature', featureId],
    queryFn: () => featuresApi.get(featureId),
    staleTime: 1000 * 60 * 5,
  })

  if (isLoading) {
    return (
      <div className="px-4 pb-4 pl-8">
        <div className="space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex items-center gap-3 px-3 py-2">
              <div className="skeleton h-4 w-14 rounded" />
              <div className="skeleton h-4 w-48" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  const options = data?.options || []
  const settings = data?.settings || []

  return (
    <div className="px-4 pb-4 pl-8 animate-fade-in">
      {/* Description */}
      {data?.description && (
        <div className="mb-4">
          <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 mb-1.5">
            Description
          </h3>
          <p className="text-sm text-zinc-400 leading-relaxed max-w-2xl">
            {data.description}
          </p>
        </div>
      )}

      {/* Options section */}
      {options.length > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-1.5 px-1">
            <AdjustmentsIcon className="w-3 h-3 text-signal-violet" />
            <span className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-400">
              Feature Options
            </span>
            <InfoTooltip term="Feature Option" className="ml-0.5">
              <p>A <strong className="text-zinc-300">feature option</strong> is a Canvas admin toggle that can be enabled or disabled at the account or course level.</p>
              <p>These appear in Canvas Settings and require an admin to activate them.</p>
            </InfoTooltip>
          </div>
          <div className="rounded-md border border-zinc-800/50 overflow-hidden">
            {options.map((option) => (
              <Link
                key={option.option_id}
                to={`/options/${option.option_id}`}
                className="flex items-center gap-3 px-3 py-2 border-b border-zinc-800/30 last:border-b-0 hover:bg-surface-3/50 transition-colors group"
              >
                <StatusPill status={option.status} size="sm" showDot={false} />
                <span className="flex-1 text-xs text-zinc-400 group-hover:text-zinc-200 transition-colors truncate">
                  {option.canonical_name || option.name}
                </span>
                <div className="hidden sm:flex items-center gap-2 flex-shrink-0">
                  <DatePill label="B" date={option.beta_date} variant="beta" />
                  <DatePill label="P" date={option.production_date} variant="prod" />
                </div>
                <ArrowRightIcon className="w-3 h-3 text-zinc-700 group-hover:text-zinc-500 transition-colors flex-shrink-0" />
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Settings section */}
      {settings.length > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-1.5 px-1">
            <CogIcon className="w-3 h-3 text-signal-cyan" />
            <span className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-400">
              Feature Settings
            </span>
            <InfoTooltip term="Feature Setting" className="ml-0.5">
              <p>A <strong className="text-zinc-300">feature setting</strong> is a non-toggle change to Canvas — such as a bug fix, UI improvement, or backend enhancement.</p>
              <p>Unlike feature options, these don't require admin action to enable. They're applied automatically by Instructure.</p>
            </InfoTooltip>
          </div>
          <div className="rounded-md border border-zinc-800/50 overflow-hidden">
            {settings.slice(0, 8).map((setting) => (
              <Link
                key={setting.setting_id}
                to={`/settings/${setting.setting_id}`}
                className="flex items-center gap-3 px-3 py-2 border-b border-zinc-800/30 last:border-b-0 hover:bg-surface-3/50 transition-colors group"
              >
                <StatusPill status={setting.status} size="sm" showDot={false} />
                <span className="flex-1 text-xs text-zinc-400 group-hover:text-zinc-200 transition-colors truncate">
                  {setting.name}
                </span>
                <div className="hidden sm:flex items-center gap-2 flex-shrink-0">
                  <DatePill label="P" date={setting.production_date} variant="prod" />
                </div>
                <ArrowRightIcon className="w-3 h-3 text-zinc-700 group-hover:text-zinc-500 transition-colors flex-shrink-0" />
              </Link>
            ))}
            {settings.length > 8 && (
              <Link
                to={`/features/${featureId}`}
                className="flex items-center justify-center gap-1 px-3 py-2 text-xs font-mono text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                +{settings.length - 8} more settings
                <ArrowRightIcon className="w-3 h-3" />
              </Link>
            )}
          </div>
        </div>
      )}

      {/* View full detail link */}
      <Link
        to={`/features/${featureId}`}
        className="inline-flex items-center gap-1.5 px-1 py-1 text-xs font-mono text-signal-blue hover:text-signal-blue/80 transition-colors"
      >
        view full detail for {featureName}
        <ArrowRightIcon className="w-3 h-3" />
      </Link>
    </div>
  )
}

function getStatusTextColor(text: string): string {
  if (text.includes('preview')) return 'text-status-preview'
  if (text.includes('pending')) return 'text-status-pending'
  if (text.includes('optional')) return 'text-status-optional'
  if (text.includes('beta')) return 'text-status-beta'
  if (text.includes('stable') || text.includes('released')) return 'text-status-released'
  return 'text-zinc-500'
}
