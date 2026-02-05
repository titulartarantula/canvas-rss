import type { CommunityPost } from '../types'
import { ChatBubbleIcon, DocumentIcon, ClockIcon } from './icons'

interface ActivityFeedProps {
  posts: CommunityPost[]
  isLoading?: boolean
}

export default function ActivityFeed({ posts, isLoading }: ActivityFeedProps) {
  if (isLoading) {
    return (
      <section className="mt-10">
        <Header />
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card p-4">
              <div className="skeleton h-4 w-3/4" />
              <div className="skeleton h-3 w-full mt-2" />
              <div className="skeleton h-3 w-1/2 mt-2" />
            </div>
          ))}
        </div>
      </section>
    )
  }

  if (posts.length === 0) {
    return (
      <section className="mt-10">
        <Header />
        <div className="mt-6 text-center py-8 card">
          <p className="text-sm text-ink-500">No recent community activity</p>
        </div>
      </section>
    )
  }

  return (
    <section className="mt-10">
      <Header count={posts.length} />

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {posts.map((post) => (
          <PostCard key={post.source_id} post={post} />
        ))}
      </div>
    </section>
  )
}

function Header({ count }: { count?: number }) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="font-display text-xl font-semibold text-ink-900">
        Recent Activity
      </h2>
      {count !== undefined && count > 0 && (
        <span className="text-sm text-ink-500">
          {count} {count === 1 ? 'post' : 'posts'}
        </span>
      )}
    </div>
  )
}

function PostCard({ post }: { post: CommunityPost }) {
  const isQuestion = post.content_type === 'question'
  const Icon = isQuestion ? ChatBubbleIcon : DocumentIcon
  const typeLabel = isQuestion ? 'Q&A' : 'Blog'
  const typeColor = isQuestion ? 'text-status-optional' : 'text-status-preview'

  // Create a link based on content type
  // For now, linking to external URL since we don't have internal pages for posts
  const href = post.url

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="card p-4 group hover:shadow-card-hover transition-all duration-200"
    >
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg bg-ink-100 ${typeColor} group-hover:bg-ink-200 transition-colors`}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-xs">
            <span className={`font-medium uppercase tracking-wide ${typeColor}`}>
              {typeLabel}
            </span>
            <span className="text-ink-300">·</span>
            <span className="text-ink-500 flex items-center gap-1">
              <ClockIcon className="w-3 h-3" />
              {formatRelativeTime(post.first_posted)}
            </span>
          </div>
          <h4 className="mt-1.5 text-sm font-medium text-ink-800 group-hover:text-accent-primary transition-colors line-clamp-2">
            {post.title}
          </h4>
          {post.summary && (
            <p className="mt-1.5 text-xs text-ink-500 line-clamp-2 leading-relaxed">
              {post.summary}
            </p>
          )}
        </div>
      </div>
    </a>
  )
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`
  return `${Math.floor(diffDays / 365)} years ago`
}
