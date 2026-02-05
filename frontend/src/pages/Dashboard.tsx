import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { dashboardApi } from '../api/client'
import DateNavigator from '../components/DateNavigator'
import ReleaseCard from '../components/ReleaseCard'
import UpcomingChanges from '../components/UpcomingChanges'
import ActivityFeed from '../components/ActivityFeed'

export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams()
  const dateParam = searchParams.get('date')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['dashboard', dateParam],
    queryFn: () => dashboardApi.get(dateParam || undefined),
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  const handleDateChange = (newDate: string | null) => {
    if (newDate) {
      setSearchParams({ date: newDate })
    } else {
      setSearchParams({})
    }
  }

  if (isError) {
    return (
      <div className="animate-fade-in">
        <DateNavigator
          currentDate={dateParam}
          onDateChange={handleDateChange}
        />
        <div className="card p-8 text-center">
          <p className="text-status-deprecated font-medium">Failed to load dashboard data</p>
          <p className="mt-2 text-sm text-ink-500">
            {error instanceof Error ? error.message : 'Please try again later'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-fade-in">
      {/* Page header with date navigation */}
      <DateNavigator
        currentDate={dateParam}
        onDateChange={handleDateChange}
        isLoading={isLoading}
      />

      {/* Subtle divider */}
      <div className="divider-subtle mb-8" />

      {/* Three-column card layout */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Release Notes Card */}
        <div className="animate-slide-up animate-delay-100">
          <ReleaseCard
            release={data?.release_note ?? null}
            type="release"
            isLoading={isLoading}
          />
        </div>

        {/* Deploy Notes Card */}
        <div className="animate-slide-up animate-delay-200">
          <ReleaseCard
            release={data?.deploy_note ?? null}
            type="deploy"
            isLoading={isLoading}
          />
        </div>

        {/* Upcoming Changes Card */}
        <div className="animate-slide-up animate-delay-300">
          <UpcomingChanges
            changes={data?.upcoming_changes ?? []}
            isLoading={isLoading}
          />
        </div>
      </div>

      {/* Recent Activity Feed */}
      <div className="animate-slide-up animate-delay-400">
        <ActivityFeed
          posts={data?.recent_activity ?? []}
          isLoading={isLoading}
        />
      </div>
    </div>
  )
}
