import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Action, Change, Mode, Offer, Pattern, Run } from '../types'
import { isApproved, isDelete, isInside } from './lock'
import { PEOPLE, offerOnEdit, offerOnPrompt, statusText } from './offer'
import { place } from './place'

// The edit lock. The module asks the person itself, so the model can never
// approve its own changes.

const START = 'mcp__architect-mode__start'
const PLAN = 'mcp__architect-mode__plan'
const FINISH = 'mcp__architect-mode__finish'
const ACTIONS: readonly Action[] = ['add', 'change', 'delete', 'move', 'rename']

const run = atom({ plugin: 'architect-mode', key: 'run' } as const, null as Run | null)

const offer = atom({ plugin: 'architect-mode', key: 'offer' } as const, 'unasked' as Offer)
const blocked = atom({ plugin: 'architect-mode', key: 'blocked' } as const, [] as string[])

// Every change of the run goes through here, so the status line stays true.
async function setRun($: any, change: (now: Run | null) => Run | null) {
  await update($, run, change)
  await $.ui.status(statusText(await read($, run)))
}

// Notes what the lock refused, for /architect-status, and returns the reason.
async function refuse($: any, what: string, reason: string): Promise<string> {
  await update($, blocked, list => [...list, oneLine(what).slice(0, 200)].slice(-20))
  return said(reason)
}

const said = (text: string) => `architect-mode: ${text}`
// Control, format and line break characters could disguise what is approved.
const HIDDEN = /[\p{C}\p{Zl}\p{Zp}]/u
const oneLine = (text: string) => text.replace(/[\p{C}\p{Zl}\p{Zp}\s]+/gu, ' ').trim()
const isPath = (value: unknown): value is string =>
  typeof value === 'string' &&
  value.trim() !== '' &&
  !HIDDEN.test(value) &&
  !value.split(/[\\/]/).includes('..')
// A pattern names a folder of the project: its first part is literal, and "**"
// is only ever a whole part.
const isGlob = (value: unknown): value is string => {
  if (!isPath(value) || /^([\\/]|[a-z]:)/i.test(value)) return false
  const parts = value.split(/[\\/]/)
  return !parts[0]!.includes('*') && parts[0] !== '.' && parts.every(p => p === '**' || !p.includes('**'))
}

function readChanges(value: unknown): Change[] | null {
  if (!Array.isArray(value)) return null
  const changes: Change[] = []
  for (const item of value) {
    const { path, action, reason, to } = (item ?? {}) as Record<string, unknown>
    const known = ACTIONS.find(one => one === action)
    const needsTarget = known === 'move' || known === 'rename'
    if (!isPath(path) || known === undefined || typeof reason !== 'string') return null
    if (needsTarget ? !isPath(to) : to !== undefined) return null
    changes.push({ path, action: known, reason: oneLine(reason), ...(isPath(to) ? { to } : {}) })
  }
  return changes
}

function readPatterns(value: unknown): Pattern[] | null {
  if (value === undefined) return []
  if (!Array.isArray(value)) return null
  const patterns: Pattern[] = []
  for (const item of value) {
    const { glob, command } = (item ?? {}) as Record<string, unknown>
    if (!isGlob(glob) || typeof command !== 'string') return null
    patterns.push({ glob, command: oneLine(command) })
  }
  return patterns
}

const describeChange = (c: Change) =>
  `${c.action} ${c.path}${c.to === undefined ? '' : ` to ${c.to}`}: ${c.reason}`
const describePattern = (p: Pattern) =>
  `Claude may edit or create any file matching ${p.glob} until the run ends (fix: ${p.command})`

// The item numbers the answer approves. Anything unclear approves nothing.
function chosen(answer: string, count: number): number[] {
  if (answer === 'Approve all') return Array.from({ length: count }, (_, i) => i)
  if (!/^\s*\d+(\s*,\s*\d+)*\s*$/.test(answer)) return []
  const picked = answer.split(',').map(n => Number(n) - 1)
  return picked.every(i => i >= 0 && i < count) ? picked : []
}

// An approved path is kept where it lands, as edits are judged: a link and its
// target are then the same file.
async function landed($: any, change: Change, root: string): Promise<Change> {
  const at = async (path: string) => {
    const full = /^([\\/]|[a-z]:)/i.test(path) ? path : `${root.replace(/[\\/]$/, '')}/${path}`
    return (await place($, full, root)) ?? path
  }
  const path = await at(change.path)
  return change.to === undefined ? { ...change, path } : { ...change, path, to: await at(change.to) }
}

// Why the edit may not happen, or null when it may.
async function judgeEdit($: any, path: string, isOffering: boolean): Promise<string | null> {
  const current = await read($, run)
  if (current === null) return isOffering ? offerOnEdit($, path) : null
  const target = await place($, path, current.root)
  if (target === null) {
    return refuse($, path, `cannot tell where ${path} lands. Use the full, plain path of the file.`)
  }
  // The session can move (a worktree). Where the run started stays locked.
  const here = await place($, await $.session.root(), current.root)
  const roots = here === null ? [current.root] : [current.root, here]
  if (!roots.some(root => isInside(target, root)) || isApproved(target, current, current.root)) return null
  if (current.mode === 'strict') {
    return refuse($, target, `${target} is not approved. Send a new change list with ${PLAN}.`)
  }
  const answer = await $.ui.ask(`${target} is not approved. Allow the edit?`, ['Allow once', 'Add to list', 'No'])
  if (answer === 'Allow once') return null
  if (answer !== 'Add to list') return refuse($, target, `the user refused the edit of ${target}.`)
  const added: Change = { path: target, action: 'change', reason: 'added at the warning' }
  await setRun($, now => (now === null ? now : { ...now, changes: [...now.changes, added] }))
  return null
}

async function judgeCommand($: any, command: string): Promise<string | null> {
  if ((await read($, run)) === null || !isDelete(command)) return null
  const question = `This command deletes files or discards work:\n${command}\nAllow it?`
  const answer = await $.ui.ask(question, ['Allow once', 'No'])
  return answer === 'Allow once' ? null : refuse($, command, 'the user refused this delete.')
}

export const register: Register = (on, options) => {
  const preferred: Mode = options.lock === 'warn' ? 'warn' : 'strict'
  const isOffering = options.ask !== 'off'

  on('session.start', async ($, e, next) => {
    await $.tool.register({
      name: 'start',
      description: 'Starts an architect run and locks project edits. The user picks the lock mode. Call it once, before the change list.',
      isDeferred: false,
    })
    await $.tool.register({
      name: 'plan',
      description: 'Sends the change list of the run to the user for approval. Only approved items can be edited. For move and rename, give "to". Use patterns only for linter or formatter fixes.',
      isDeferred: false,
      inputSchema: {
        type: 'object',
        required: ['changes'],
        properties: {
          changes: {
            type: 'array',
            items: {
              type: 'object',
              required: ['path', 'action', 'reason'],
              properties: {
                path: { type: 'string' },
                action: { enum: [...ACTIONS] },
                reason: { type: 'string' },
                to: { type: 'string' },
              },
            },
          },
          patterns: {
            type: 'array',
            items: {
              type: 'object',
              required: ['glob', 'command'],
              properties: { glob: { type: 'string' }, command: { type: 'string' } },
            },
          },
        },
      },
    })
    await $.tool.register({
      name: 'finish',
      description: 'Ends the architect run. The user confirms before the lock turns off.',
      isDeferred: false,
    })
    await $.command.register({
      name: 'architect-off',
      description: 'Turn the architect edit lock off',
      immediate: true,
    })
    await $.command.register({
      name: 'architect-status',
      description: 'Show the architect lock, what is approved and what was blocked',
      immediate: true,
    })
    await $.ui.status(statusText(await read($, run)))
    return next(e)
  })

  on('prompt.submit', async ($, e, next) => {
    if (!isOffering || (await read($, run)) !== null) return next(e)
    return next(await offerOnPrompt($, e))
  }).catch(($, e, next) => next(e))

  on('command.run', { command: 'architect-status' }, async $ => {
    const current = await read($, run)
    const refusals = await read($, blocked)
    const approved =
      current === null ? [] : [...current.changes.map(describeChange), ...current.patterns.map(describePattern)]
    return {
      text: [
        current === null ? 'Architect lock is off.' : `${statusText(current)}, in ${current.root}`,
        ...(approved.length > 0 ? ['Approved:', ...approved.map(line => `- ${line}`)] : []),
        ...(refusals.length > 0 ? ['Blocked:', ...refusals.map(line => `- ${line}`)] : []),
      ].join('\n'),
    }
  })

  on('session.end', async ($, e, next) => {
    if (e.reason === 'clear') {
      await setRun($, () => null)
      await update($, offer, () => 'unasked' as Offer)
      await update($, blocked, () => [])
    }
    return next(e)
  })

  on('command.run', { command: 'architect-off' }, async ($, e) => {
    if (!PEOPLE.includes(e.origin.kind)) {
      return { text: 'Only you can turn the lock off. Type /architect-off.' }
    }
    await setRun($, () => null)
    // The user chose to work without it: edits no longer wait or ask.
    await update($, offer, now => (now === 'muted' ? now : ('declined' as const)))
    return { text: 'Architect lock is off.' }
  })

  on('tool.call', { tool: START }, async $ => {
    const isActive = said('a run is already active. Its lock mode stays.')
    if ((await read($, run)) !== null) return { deny: isActive }
    const sessionRoot = await $.session.root()
    const root = await place($, sessionRoot, sessionRoot)
    if (root === null) return { deny: said(`cannot resolve the project folder ${sessionRoot}, so no run started.`) }
    const modes: Mode[] = preferred === 'warn' ? ['warn', 'strict'] : ['strict', 'warn']
    const answer = await $.ui.ask(`Which edit lock? The project is ${root}.`, modes)
    const mode = modes.find(one => one === answer)
    if (mode === undefined) return { deny: said('no lock mode picked, so no run started.') }
    await setRun($, now => now ?? { mode, root, changes: [], patterns: [] })
    // The offer is answered: once this run ends, edits do not wait for another.
    await update($, offer, now => (now === 'muted' ? now : ('declined' as const)))
    return { result: `Run started with the ${mode} lock. Send the change list with ${PLAN}.` }
  }).catch(() => ({ deny: said('no lock mode picked, so no run started.') }))

  on('tool.call', { tool: PLAN }, async ($, e) => {
    if ((await read($, run)) === null) return { deny: said(`no active run. Call ${START} first.`) }
    const input = e as unknown as Record<string, unknown>
    const changes = readChanges(input.changes)
    const patterns = readPatterns(input.patterns)
    if (changes === null || patterns === null || changes.length + patterns.length === 0) {
      return { deny: said('the change list is empty or not valid.') }
    }
    const lines = [...changes.map(describeChange), ...patterns.map(describePattern)]
    const question = ['Approve these changes?', ...lines.map((line, i) => `${i + 1}. ${line}`)].join('\n')
    const picked = new Set(chosen(await $.ui.ask(question, ['Approve all', 'Reject']), lines.length))
    if (picked.size === 0) return { result: 'Nothing was approved.' }
    const { root } = (await read($, run))!
    const approved = await Promise.all(changes.filter((_, i) => picked.has(i)).map(c => landed($, c, root)))
    await setRun($, now =>
      now === null
        ? now
        : {
            ...now,
            changes: [...now.changes, ...approved],
            patterns: [...now.patterns, ...patterns.filter((_, i) => picked.has(changes.length + i))],
          },
    )
    return { result: ['Approved:', ...lines.filter((_, i) => picked.has(i))].join('\n') }
  }).catch(() => ({ deny: said('nothing was approved.') }))

  on('tool.call', { tool: FINISH }, async $ => {
    if ((await read($, run)) === null) return { result: 'No run is active.' }
    if ((await $.ui.ask('End the run and unlock?', ['Yes', 'No'])) !== 'Yes') {
      return { result: 'The run stays active.' }
    }
    await setRun($, () => null)
    return { result: 'Run ended. The lock is off.' }
  }).catch(() => ({ deny: said('the run stays active.') }))

  // A guard that fails refuses the call, unless the call already ran.
  const failed = said('the edit lock could not check this call, so it is refused.')

  on('tool.call', { tool: 'Edit' }, async ($, e, next) => {
    const deny = await judgeEdit($, e.file_path, isOffering)
    return deny === null ? next(e) : { deny }
  }).catch(($, e, next) => (next.called ? next(e) : { deny: failed }))

  on('tool.call', { tool: 'Write' }, async ($, e, next) => {
    const deny = await judgeEdit($, e.file_path, isOffering)
    return deny === null ? next(e) : { deny }
  }).catch(($, e, next) => (next.called ? next(e) : { deny: failed }))

  on('tool.call', { tool: 'NotebookEdit' }, async ($, e, next) => {
    const deny = await judgeEdit($, e.notebook_path, isOffering)
    return deny === null ? next(e) : { deny }
  }).catch(($, e, next) => (next.called ? next(e) : { deny: failed }))

  // Commands are judged at the permission check: a tool.call hook on a shell
  // would stop commands from moving to the background, run or no run.
  const refused = { decision: 'deny', reason: failed } as const

  on('tool.check', { tool: 'Bash' }, async ($, e, next) => {
    const deny = await judgeCommand($, String((e.input as { command?: unknown }).command))
    return deny === null ? next(e) : { decision: 'deny', reason: deny }
  }).catch(() => refused)

  on('tool.check', { tool: 'PowerShell' }, async ($, e, next) => {
    const deny = await judgeCommand($, String((e.input as { command?: unknown }).command))
    return deny === null ? next(e) : { decision: 'deny', reason: deny }
  }).catch(() => refused)
}
