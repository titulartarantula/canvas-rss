import type { CommunityPost } from '../types'
import { ChatBubbleIcon, DocumentIcon, ClockIcon, ExternalLinkIcon } from './icons'

interface CommunityPostsListProps {
  posts: CommunityPost[]
  emptyMessage?: string
}

export default function CommunityPostsList({ posts, emptyMessage = 'No community posts' }: CommunityPostsListProps) {
  if (posts.length === 0) {
    return (
      <div className="text-center py-6">
        <ChatBubbleIcon className="w-5 h-5 mx-auto text-zinc-700" />
        <p className="mt-2 text-xs text-zinc-500 font-mono">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
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
      className="group card p-3 flex items-start gap-2.5 hover:border-zinc-700 transition-all animate-slide-up"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className={`p-1.5 rounded bg-surface-3 ${typeColor} flex-shrink-0`}>
        <Icon className="w-3 h-3" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 text-xs font-mono">
          <span className={`font-medium uppercase tracking-wider ${typeColor}`}>{typeLabel}</span>
          <span className="text-zinc-700">·</span>
          <span className="text-zinc-500 flex items-center gap-0.5">
            <ClockIcon className="w-2.5 h-2.5" />
            {formatRelativeTime(post.first_posted)}
          </span>
        </div>
        <h4 className="mt-1 text-xs text-zinc-400 group-hover:text-zinc-200 transition-colors line-clamp-2">
          {post.title}
        </h4>
      </div>
      <ExternalLinkIcon className="w-3 h-3 text-zinc-700 group-hover:text-zinc-500 transition-colors flex-shrink-0 mt-1" />
    </a>
  )
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'today'
  if (diffDays === 1) return '1d'
  if (diffDays < 7) return `${diffDays}d`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w`
  return `${Math.floor(diffDays / 30)}mo`
}

export function CommunityPostsListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card p-3 flex items-start gap-2.5">
          <div className="skeleton w-6 h-6 rounded" />
          <div className="flex-1">
            <div className="skeleton h-2.5 w-16 mb-1.5" />
            <div className="skeleton h-3 w-full" />
          </div>
        </div>
      ))}
    </div>
  )
}
