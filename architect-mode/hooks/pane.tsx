import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { PaneState, Run } from '../types'
import { appendLog } from './log'
import * as notes from './notes'
import { place } from './place'

// The notes pane. It only shows and explains: it never changes the run, so
// nothing here can approve or unlock an edit.

const NOTE = 'mcp__architect-mode__note'
const PANE = 'architect-notes'
const TITLE = 'Architect notes'

const pane = atom({ plugin: 'architect-mode', key: 'pane' } as const, notes.emptyPane())
// Read only: the lock owns it.
const run = atom({ plugin: 'architect-mode', key: 'run' } as const, null as Run | null)

const said = (text: string) => `architect-mode: ${text}`

const WHY: Record<string, string> = {
  'api-error': 'the model service returned an error.',
  'empty-reply': 'the model returned nothing.',
  aborted: 'the call was stopped.',
}

async function save($: any, root: string, entry: string): Promise<boolean> {
  const isSaved = await appendLog($, root, entry)
  await update($, pane, now => ({ ...now, warning: isSaved ? null : 'Log not saved.' }))
  return isSaved
}

// Runs only from the person's submit. The answer goes to the pane and the log,
// never back into the chat.
async function answer($: any, typed: string) {
  const question = notes.clean(typed).replace(/\s+/g, ' ').trim()
  if (question === '') return
  if (question.length > notes.LIMITS.question) {
    await update($, pane, now => ({ ...now, warning: `Keep the question under ${notes.LIMITS.question} characters.` }))
    return
  }
  let isMine = false
  let epoch = 0
  await update($, pane, now => {
    isMine = now.pending === null
    epoch = now.epoch
    return isMine ? { ...now, pending: question, warning: null } : now
  })
  if (!isMine) return
  // Whatever fails, the box must take the next question.
  try {
    await forkAnswer($, question, epoch)
  } catch {
    await update($, pane, now =>
      now.epoch === epoch ? { ...now, pending: null, warning: 'The question failed. Ask again.' } : now,
    )
  }
}

// The project the notes belong to, spelled as a run spells it.
async function logRoot($: any): Promise<string> {
  const current = await read($, run)
  if (current !== null) return current.root
  const root = await $.session.root()
  return (await place($, root, root)) ?? root
}

async function forkAnswer($: any, question: string, epoch: number) {
  // Without the chat the question is still answered, from the notes alone.
  const chat = await $.session.messages({ last: 20 }).catch(() => [])
  const prompt = notes.questionPrompt(question, await read($, pane), Array.isArray(chat) ? chat : [])
  let reply: any
  try {
    reply = await $.model.complete({ model: 'sonnet', prompt, maxTokens: 1500 })
  } catch {
    reply = { isAnswered: false, reason: 'api-error' }
  }
  // A /clear while waiting: the answer belongs to the old session.
  if ((await read($, pane)).epoch !== epoch) return
  const text = reply.isAnswered
    ? notes.clean(String(reply.text)).slice(0, notes.LIMITS.answer)
    : `No answer: ${WHY[reply.reason] ?? 'the call failed.'} Ask again.`
  await update($, pane, now => notes.withAnswer(now, question, text))
  if (!reply.isAnswered) return
  await save($, await logRoot($),notes.logEntry('question', question, notes.defuse(text), []))
}

// A plugin may hook session.start and session.end once, so the lock's hooks
// call these two.
export async function startPane($: any) {
  await $.tool.register({
    name: 'note',
    description:
      'Shows the user a note in the architect pane during a run: a decision, a pattern to follow, a file tree idea, or a coach review of the approach the user wrote. Plain simple words. Every note needs sources the user can check: https links you opened, or file:line.',
    isDeferred: false,
    inputSchema: {
      type: 'object',
      required: ['kind', 'title', 'text', 'sources'],
      properties: {
        kind: { enum: [...notes.KINDS] },
        title: { type: 'string', maxLength: notes.LIMITS.title },
        text: {
          type: 'string',
          description: `Why, in simple words. At most ${notes.LIMITS.text} characters, ${notes.LIMITS.long} for a tree or coach.`,
        },
        sources: { type: 'array', items: { type: 'string' }, minItems: 1, maxItems: notes.LIMITS.sources },
      },
    },
  })
  await $.command.register({ name: PANE, description: 'Show the architect notes pane', immediate: true })
  // A reload drops a waiting question; its flag would block the next one.
  await update($, pane, now => ({ ...now, pending: null }))
}

export async function clearPane($: any) {
  await update($, pane, now => notes.emptyPane(now.epoch + 1))
}

export function registerPane(on: Parameters<Register>[0]) {
  on('command.run', { command: PANE }, async $ => {
    await $.ui.open({ id: PANE, title: TITLE })
    return { text: 'Architect notes pane opened.' }
  })

  on('tool.call', { tool: NOTE }, async ($, e) => {
    if (e.agentId !== undefined) return { deny: said('only the lead sends notes.') }
    const current = await read($, run)
    if (current === null) return { deny: said('no active run, so no note was added.') }
    const note = notes.readNote(e)
    if (note === null) return { deny: said(notes.noteProblem(e)) }
    await update($, pane, now => notes.withNote(now, note))
    // No focus: typing must not move away from a question on screen.
    await $.ui.open({ id: PANE, title: TITLE }).catch(() => undefined)
    const body = note.kind === 'tree' ? notes.fenced(note.text) : notes.defuse(note.text)
    const isSaved = await save($, current.root, notes.logEntry(note.kind, note.title, body, note.sources))
    return { result: isSaved ? 'Note added.' : 'Note added, but the log was not saved.' }
  }).catch(() => ({ deny: said('the note failed. It may show in the pane, so do not send it again.') }))

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Input, Markdown } = $.ui.resolve(e)
    const now: PaneState = await read($, pane)
    const isEmpty = now.decisions.length + now.patterns.length + now.answers.length === 0 && !now.tree && !now.coach

    return (
      <Box flexDirection="column" gap={1}>
        <Text dimColor>Suggestions, not approvals. Check the sources.</Text>
        {isEmpty && <Text dimColor>No notes yet.</Text>}
        {now.coach && <Text bold>COACH</Text>}
        {now.coach && (
          <Markdown
            text={`${notes.defuse(`${now.coach.title}\n\n${now.coach.text}`)}\n\nSources: ${notes.showSources(now.coach.sources)}`}
          />
        )}
        {now.decisions.length > 0 && <Text bold>DECISIONS</Text>}
        {now.decisions.length > 0 && <Markdown text={notes.table('Decision', now.decisions)} />}
        {now.patterns.length > 0 && <Text bold>PATTERNS</Text>}
        {now.patterns.length > 0 && <Markdown text={notes.table('Pattern', now.patterns)} />}
        {now.tree !== null && <Text bold>FILE TREE (idea)</Text>}
        {now.tree !== null && (
          <Markdown
            text={`${notes.fenced(now.tree.text)}\n\nSources: ${notes.showSources(now.tree.sources)}`}
          />
        )}
        {now.answers.length > 0 && <Text bold>ANSWERS (sources not checked)</Text>}
        {now.answers.map(one => (
          <Box flexDirection="column">
            <Text color="cyan">Q: {one.question}</Text>
            <Markdown text={notes.defuse(one.text)} />
          </Box>
        ))}
        {now.pending !== null && <Text dimColor>Thinking: {now.pending}</Text>}
        {now.warning !== null && <Text color="yellow">{now.warning}</Text>}
        <Input key="ask" label="Ask: " placeholder="What do you not understand?" onSubmit={value => answer($, value)} />
      </Box>
    )
  })
}
