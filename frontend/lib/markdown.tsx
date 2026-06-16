// lib/markdown.tsx — lightweight, safe markdown renderer shared across the UI
// (chat panel, full-screen chat, live minutes, diligence binders).
//
// Handles: headers (#/##/###), **bold**, `inline code`, bullet lists (-, *, +, •),
// numbered lists, blank-line spacing, and --- dividers. It NEVER prints raw '#'
// hashes or stray markdown artifacts — headers are rendered as styled text and
// any leftover leading hashes are stripped. Emojis pass through untouched.
import React from 'react'

/** Parse inline spans within a single line: **bold** and `code`. */
function parseInline(str: string, keyBase: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = []
  const regex = /\*\*([^*]+)\*\*|`([^`]+)`/g
  let last = 0
  let i = 0
  let m: RegExpExecArray | null
  while ((m = regex.exec(str)) !== null) {
    if (m.index > last) nodes.push(str.slice(last, m.index))
    if (m[1] !== undefined) {
      nodes.push(
        <strong key={`${keyBase}-b${i}`} className="font-semibold text-text-primary">
          {m[1]}
        </strong>,
      )
    } else if (m[2] !== undefined) {
      nodes.push(
        <code
          key={`${keyBase}-c${i}`}
          className="px-1 py-0.5 rounded bg-bg-muted font-mono text-[0.85em] text-text-primary"
        >
          {m[2]}
        </code>,
      )
    }
    last = regex.lastIndex
    i++
  }
  if (last < str.length) nodes.push(str.slice(last))
  return nodes.length ? nodes : [str]
}

export function renderMarkdown(text: string): React.ReactNode {
  if (!text) return null
  const lines = text.replace(/\r\n/g, '\n').split('\n')
  const out: React.ReactNode[] = []

  lines.forEach((raw, idx) => {
    let line = raw

    // Horizontal divider (---, ***, ___) → thin rule
    if (/^\s*([-*_])\1{2,}\s*$/.test(line)) {
      out.push(<hr key={idx} className="my-2.5 border-t border-border" />)
      return
    }

    // Blank line → vertical breathing room
    if (line.trim() === '') {
      out.push(<div key={idx} className="h-2" />)
      return
    }

    // Header (#, ##, ###…) → styled heading, hashes stripped
    const h = line.match(/^\s*(#{1,6})\s+(.*)$/)
    if (h) {
      const level = h[1].length
      const content = h[2].trim()
      const cls =
        level <= 1
          ? 'text-[15px] font-bold text-text-primary mt-2 mb-1'
          : level === 2
          ? 'text-[13px] font-bold text-text-primary mt-2 mb-0.5'
          : 'text-[11px] font-semibold text-text-secondary uppercase tracking-wide mt-1.5 mb-0.5'
      out.push(
        <div key={idx} className={cls}>
          {parseInline(content, `h${idx}`)}
        </div>,
      )
      return
    }

    // Bullet (-, *, +, •)
    const b = line.match(/^\s*[-*+•]\s+(.*)$/)
    if (b) {
      out.push(
        <div key={idx} className="flex gap-2 my-0.5 text-text-secondary">
          <span className="text-accent select-none leading-relaxed">•</span>
          <span className="flex-1 leading-relaxed">{parseInline(b[1], `b${idx}`)}</span>
        </div>,
      )
      return
    }

    // Numbered list (1. 2. …)
    const n = line.match(/^\s*(\d+)\.\s+(.*)$/)
    if (n) {
      out.push(
        <div key={idx} className="flex gap-2 my-0.5 text-text-secondary">
          <span className="text-accent font-semibold select-none tabular-nums">{n[1]}.</span>
          <span className="flex-1 leading-relaxed">{parseInline(n[2], `n${idx}`)}</span>
        </div>,
      )
      return
    }

    // Plain paragraph — strip any stray leading hashes just in case
    line = line.replace(/^\s*#+\s*/, '')
    out.push(
      <div key={idx} className="my-0.5 text-text-secondary leading-relaxed">
        {parseInline(line, `p${idx}`)}
      </div>,
    )
  })

  return out
}

export default renderMarkdown
