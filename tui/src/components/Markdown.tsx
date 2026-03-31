/**
 * Markdown renderer for terminal output.
 * Adapted from Claude Code's src/components/Markdown.tsx — same approach
 * (marked → chalk ANSI → <Ansi>) but without the theme/cliHighlight chain.
 */
import React, { useMemo } from 'react'
import { marked, type Token } from 'marked'
import { Ansi } from '../ink/Ansi.js'
import Box from '../ink/components/Box.js'
import { configureMarked, formatToken } from '../utils/markdown.js'

// Single regex that matches any markdown syntax character.
// If absent, skip the full marked.lexer call (covers most plain-text responses).
const MD_SYNTAX_RE = /[#*`|[\]>_~\\]|\n\n|^\d+\. |\n\d+\. /m

function hasMarkdownSyntax(s: string): boolean {
  return MD_SYNTAX_RE.test(s.length > 500 ? s.slice(0, 500) : s)
}

// Module-level LRU token cache — same reasoning as CC: useMemo doesn't survive
// unmount→remount (virtual-scroll), so we cache at module scope.
const TOKEN_CACHE_MAX = 200
const tokenCache = new Map<string, Token[]>()

function cachedLex(content: string): Token[] {
  if (!hasMarkdownSyntax(content)) {
    // Fast path: plain text, skip the full GFM parse
    return [{
      type: 'paragraph',
      raw: content,
      text: content,
      tokens: [{ type: 'text', raw: content, text: content } as Token],
    } as Token]
  }
  const hit = tokenCache.get(content)
  if (hit) {
    // Promote to MRU
    tokenCache.delete(content)
    tokenCache.set(content, hit)
    return hit
  }
  const tokens = marked.lexer(content)
  if (tokenCache.size >= TOKEN_CACHE_MAX) {
    tokenCache.delete(tokenCache.keys().next().value!)
  }
  tokenCache.set(content, tokens)
  return tokens
}

interface Props {
  children: string
  dimColor?: boolean
}

export function Markdown({ children, dimColor }: Props) {
  configureMarked()

  const ansiText = useMemo(
    () => cachedLex(children).map(t => formatToken(t)).join('').trimEnd(),
    [children],
  )

  return (
    <Box flexDirection="column">
      <Ansi dimColor={dimColor}>{ansiText}</Ansi>
    </Box>
  )
}
