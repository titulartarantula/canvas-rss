/**
 * Lightweight inline markdown renderer for LLM-generated text.
 * Handles **bold** and *italic* patterns without a full markdown library.
 */
export default function InlineMarkdown({ text, className }: { text: string; className?: string }) {
  const parts = parseInlineMarkdown(text)

  return (
    <p className={className}>
      {parts.map((part, i) => {
        if (part.type === 'bold') return <strong key={i} className="text-zinc-300 font-medium">{part.text}</strong>
        if (part.type === 'italic') return <em key={i}>{part.text}</em>
        return <span key={i}>{part.text}</span>
      })}
    </p>
  )
}

type InlinePart = { type: 'text' | 'bold' | 'italic'; text: string }

function parseInlineMarkdown(input: string): InlinePart[] {
  const parts: InlinePart[] = []
  // Match **bold** or *italic* patterns
  const regex = /\*\*(.+?)\*\*|\*(.+?)\*/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(input)) !== null) {
    // Text before match
    if (match.index > lastIndex) {
      parts.push({ type: 'text', text: input.slice(lastIndex, match.index) })
    }
    if (match[1] !== undefined) {
      parts.push({ type: 'bold', text: match[1] })
    } else if (match[2] !== undefined) {
      parts.push({ type: 'italic', text: match[2] })
    }
    lastIndex = match.index + match[0].length
  }

  // Remaining text
  if (lastIndex < input.length) {
    parts.push({ type: 'text', text: input.slice(lastIndex) })
  }

  return parts
}
