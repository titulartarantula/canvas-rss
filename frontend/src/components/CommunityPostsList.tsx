import type { CommunityPost } from '../types'
import { ChatBubbleIcon, DocumentIcon, ClockIcon, ExternalLinkIcon } from './icons'

interface CommunityPostsListProps {
  posts: CommunityPost[]
  emptyMessage?: string
}

export default function CommunityPostsList({
  posts,
  emptyMessage = 'No community posts',
}: CommunityPostsListProps) {
  if (posts.length === 0) {
    return (
      <div className="text-center py-8">
        <ChatBubbleIcon className="w-8 h-8 mx-auto text-ink-300" />
        <p className="mt-2 text-sm text-ink-500">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {posts.map((post, index) => (
        <PostCard key={post.source_id} post={post} index={index} />
      ))}
    </div>
  )
}

function PostCard({ post, index }: { post: CommunityPost; index: number }) {
  const isQuestion = post.content_type === 'question'
  const Icon = isQuestion ? ChatBubbleIcon : DocumentIcon
  const typeLabel = isQuestion ? 'Q&A' : 'Blog'
  const typeColor = isQuestion ? 'text-status-optional' : 'text-status-preview'

  return (
    <a
      href={post.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group card p-4 flex items-start gap-3 hover:shadow-card-hover transition-all animate-slide-up"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      {/* Icon */}
      <div className={`p-2 rounded-lg bg-ink-100 ${typeColor} group-hover:bg-ink-200 transition-colors flex-shrink-0`}>
        <Icon className="w-4 h-4" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Meta info */}
        <div className="flex items-center gap-2 text-xs">
          <span className={`font-medium uppercase tracking-wide ${typeColor}`}>
            {typeLabel}
          </span>
          {post.mention_type && (
            <>
              <span className="text-ink-300">·</span>
              <span className="text-ink-500 capitalize">{post.mention_type}</span>
            </>
          )}
          <span className="text-ink-300">·</span>
          <span className="text-ink-500 flex items-center gap-1">
            <ClockIcon className="w-3 h-3" />
            {formatRelativeTime(post.first_posted)}
          </span>
        </div>

        {/* Title */}
        <h4 className="mt-1.5 font-medium text-ink-800 group-hover:text-accent-primary transition-colors line-clamp-2">
          {post.title}
        </h4>

        {/* Summary */}
        {post.summary && (
          <p className="mt-1.5 text-sm text-ink-500 line-clamp-2 leading-relaxed">
            {post.summary}
          </p>
        )}
      </div>

      {/* External link indicator */}
      <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        <ExternalLinkIcon className="w-4 h-4 text-ink-400" />
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

// Skeleton for loading state
export function CommunityPostsListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card p-4 flex items-start gap-3">
          <div className="skeleton w-8 h-8 rounded-lg" />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <div className="skeleton h-3 w-12" />
              <div className="skeleton h-3 w-20" />
            </div>
            <div className="mt-2 skeleton h-4 w-full max-w-xs" />
            <div className="mt-2 skeleton h-3 w-full" />
          </div>
        </div>
      ))}
    </div>
  )
}
