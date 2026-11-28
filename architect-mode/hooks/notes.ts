import type { Note, NoteKind, PaneState } from '../types'

// The rules of a note: what is accepted and how it reads. No engine calls.

export const KINDS: readonly NoteKind[] = ['decision', 'pattern', 'tree']
export const LIMITS = { title: 80, text: 500, tree: 3000, sources: 3, source: 300, question: 500, answer: 3000 }
// How many of each the pane keeps. The log keeps all of them.
const KEPT = { notes: 20, answers: 5 }

// Control and format characters could disguise what is on screen.
export const clean = (text: string) =>
  text.replace(/\r\n?/g, '\n').replace(/[\p{C}\p{Zl}\p{Zp}]/gu, c => (c === '\n' || c === '\t' ? c : ''))
const oneLine = (text: string) => clean(text).replace(/\s+/g, ' ').trim()

// The host is plain, so no "user@" can pose as it, and no bracket can open a
// second link. Other characters must be percent-encoded.
const LINK = /^https:\/\/[A-Za-z0-9.-]+(?::\d+)?(?:[/?#][A-Za-z0-9\-._~/?#@!$&+,;=%:]*)?$/
// A source the person can check: an https link, or a file and its line.
const isSource = (value: unknown): value is string =>
  typeof value === 'string' &&
  value.length <= LIMITS.source &&
  clean(value) === value &&
  (LINK.test(value) ||/^(?:[A-Za-z]:)?[^\s:<>|`]+:\d+$/.test(value))

// Why the note is refused, or the note.
function judge(value: unknown): { note: Note } | { problem: string } {
  const { kind, title, text, sources } = (value ?? {}) as Record<string, unknown>
  const known = KINDS.find(one => one === kind)
  if (known === undefined) return { problem: `kind must be one of ${KINDS.join(', ')}.` }
  const max = known === 'tree' ? LIMITS.tree : LIMITS.text
  const head = typeof title === 'string' ? oneLine(title) : ''
  const body = typeof text === 'string' ? clean(text).replace(/^\n+|\s+$/g, '') : ''
  if (head === '' || head.length > LIMITS.title) return { problem: `title needs 1 to ${LIMITS.title} characters.` }
  if (body.trim() === '' || body.length > max) return { problem: `text needs 1 to ${max} characters.` }
  if (!Array.isArray(sources) || sources.length === 0 || sources.length > LIMITS.sources || !sources.every(isSource)) {
    return { problem: `give 1 to ${LIMITS.sources} sources, each an https link or a file:line.` }
  }
  return { note: { kind: known, title: head, text: body, sources: [...sources] } }
}

export function readNote(value: unknown): Note | null {
  const judged = judge(value)
  return 'note' in judged ? judged.note : null
}

export function noteProblem(value: unknown): string {
  const judged = judge(value)
  return 'problem' in judged ? judged.problem : ''
}

const HEADING = /^((?:[ \t]|>|[-*+][ \t]+|\d+[.)][ \t]+)*)(?:#{1,6}(?:[ \t]+|$))+/gm

// Removing one mark can uncover another, so repeat until nothing changes.
const unhead = (text: string): string => {
  const next = text.replace(HEADING, '$1')
  return next === text ? text : unhead(next)
}

// Model text, made safe to draw as Markdown: a link shows where it goes, only
// https stays a link, and nothing reads as a heading of the pane.
export const defuse = (text: string) =>
  unhead(clean(text)
    .replace(/\](?=[([:])/g, '] ')
    // No word boundary: "_http://" can still become a link.
    .replace(/(http|file):/gi, '$1 :')
    .replace(/(?<!https:\/\/)(www)\./gi, '$1 .')
    .replace(/<(?=[A-Za-z/!])/g, '< '))
    .replace(/^[ \t>]*(?:=+|-+)[ \t]*$/gm, '')

export const showSources = (sources: string[]) =>
  sources.map(one => (one.startsWith('https://') ? one : `\`${one}\``)).join(' ')

const cell = (text: string) => defuse(oneLine(text)).replace(/\\/g, '\\\\').replace(/\|/g, '\\|')

export const table = (label: string, notes: Note[]) =>
  [
    `| ${label} | Why | Source |`,
    '|---|---|---|',
    ...notes.map(n => `| ${cell(n.title)} | ${cell(n.text)} | ${showSources(n.sources)} |`),
  ].join('\n')

// A fenced block holds no links; the text must not close the fence.
export const fenced = (text: string) => `\`\`\`\n${clean(text).replace(/`{3,}/g, "'''")}\n\`\`\``

export const emptyPane = (epoch = 0): PaneState => ({
  epoch,
  decisions: [],
  patterns: [],
  tree: null,
  answers: [],
  pending: null,
  warning: null,
})

export function withNote(pane: PaneState, note: Note): PaneState {
  if (note.kind === 'tree') return { ...pane, tree: note }
  const list = note.kind === 'decision' ? 'decisions' : 'patterns'
  return { ...pane, [list]: [...pane[list], note].slice(-KEPT.notes) }
}

export const withAnswer = (pane: PaneState, question: string, text: string): PaneState => ({
  ...pane,
  pending: null,
  answers: [...pane.answers, { question, text }].slice(-KEPT.answers),
})

// The same key rule as the backlog (see audit.md).
export const logPath = (data: string, root: string) =>
  `${data.replace(/[\\/]+$/, '')}/projects/${root.replace(/[^A-Za-z0-9]+/g, '-')}/notes.md`

// One entry. The body is quoted, so its text cannot start another entry.
export const logEntry = (label: string, title: string, body: string, sources: string[]) =>
  [
    `## ${label}: ${defuse(oneLine(title))}`,
    '',
    ...body.split('\n').map(line => `> ${line}`),
    '',
    ...(sources.length > 0 ? [`Sources: ${showSources(sources)}`, ''] : []),
    '',
  ].join('\n')

export const questionPrompt = (question: string) =>
  [
    'The user asks about a topic of the work. Answer the user only.',
    'Use plain, simple words. Be brief. Use a table when it helps.',
    'You have no tools. Cite sources as full https links or file:line, only ones you are sure of.',
    'With no source you are sure of, say so.',
    '',
    `Question: ${question}`,
  ].join('\n')
