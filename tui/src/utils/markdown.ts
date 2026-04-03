/**
 * Markdown token → ANSI string formatter.
 * Adapted from Claude Code's src/utils/markdown.ts — simplified to remove
 * theme system, cliHighlight, and hyperlink dependencies.
 */
import chalk from 'chalk'
import { marked, type Token, type Tokens } from 'marked'

const EOL = '\n'

let configured = false
export function configureMarked(): void {
  if (configured) return
  configured = true
  // Disable strikethrough — '~' often means "approximately" in scientific text
  marked.use({ tokenizer: { del() { return undefined } } })
}

export function formatToken(
  token: Token,
  listDepth = 0,
  orderedListNumber: number | null = null,
  parent: Token | null = null,
): string {
  switch (token.type) {
    case 'blockquote': {
      const inner = (token.tokens ?? []).map(t => formatToken(t)).join('')
      return inner
        .split(EOL)
        .map(line => (line.trim() ? `│ ${chalk.italic(line)}` : line))
        .join(EOL)
    }

    case 'code':
      return (token as Tokens.Code).text + EOL

    case 'codespan':
      return chalk.cyan((token as Tokens.Codespan).text)

    case 'em':
      return chalk.italic(
        (token.tokens ?? []).map(t => formatToken(t, 0, null, parent)).join(''),
      )

    case 'strong':
      return chalk.bold(
        (token.tokens ?? []).map(t => formatToken(t, 0, null, parent)).join(''),
      )

    case 'heading': {
      const text = (token.tokens ?? []).map(t => formatToken(t)).join('')
      const depth = (token as Tokens.Heading).depth
      if (depth === 1) return chalk.bold.underline(text) + EOL + EOL
      return chalk.bold(text) + EOL + EOL
    }

    case 'hr':
      return '─'.repeat(40) + EOL

    case 'image':
      return (token as Tokens.Image).href

    case 'link': {
      const text = (token.tokens ?? [])
        .map(t => formatToken(t, 0, null, token))
        .join('')
      return text || (token as Tokens.Link).href
    }

    case 'list':
      return (token as Tokens.List).items
        .map((item, i) =>
          formatToken(
            item as unknown as Token,
            listDepth,
            (token as Tokens.List).ordered
              ? ((token as Tokens.List).start as number) + i
              : null,
            token,
          ),
        )
        .join('')

    case 'list_item': {
      const indent = '  '.repeat(listDepth)
      return (token.tokens ?? [])
        .map(t => `${indent}${formatToken(t, listDepth + 1, orderedListNumber, token)}`)
        .join('')
    }

    case 'paragraph':
      return (token.tokens ?? []).map(t => formatToken(t)).join('') + EOL

    case 'space':
      return EOL

    case 'br':
      return EOL

    case 'text': {
      if (parent?.type === 'list_item') {
        const bullet = orderedListNumber === null ? '-' : `${orderedListNumber}.`
        const inner = token.tokens
          ? token.tokens.map(t => formatToken(t, listDepth, orderedListNumber, token)).join('')
          : (token as Tokens.Text).text
        return `${bullet} ${inner}${EOL}`
      }
      return token.tokens
        ? token.tokens.map(t => formatToken(t, listDepth, orderedListNumber, token)).join('')
        : (token as Tokens.Text).text
    }

    default:
      return 'raw' in token ? (token as { raw: string }).raw : ''
  }
}
