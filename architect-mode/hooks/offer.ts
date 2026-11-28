import { atom, read, update } from 'claude-code'

import type { Offer, Run } from '../types'
import { isInside } from './lock'
import { place } from './place'

// Offers architect mode for big work typed without the command. An offer that
// fails stays out of the way: only a run may block what was not agreed to.

const offer = atom({ plugin: 'architect-mode', key: 'offer' } as const, 'unasked' as Offer)

const QUESTION = 'Use architect mode?'
const ANSWERS = ['Yes', 'No', 'Not this session']
// The small model sees only these words, so each says what it covers.
const BIG = 'new product direction, a large refactor, or an audit with many fixes'
const KINDS = [BIG, 'a small or routine code change', 'a follow-up on the current work', 'something else']
const USE_IT =
  'The user wants architect mode for this task. Use the skill architect-mode:architect before changing any file. If it is already running, call mcp__architect-mode__start first.'
const DECLINED =
  'The user declined architect mode for this task. Do not use the skill architect-mode:architect unless they ask for it.'
// Prompt origins that are the user: terminal, remote control and the desktop app.
export const PEOPLE = ['composer', 'bridge', 'sdk']

const noted = (e: any, note: string) => ({ ...e, context: [...(e.context ?? []), note] })

export function statusText(run: Run | null): string | undefined {
  if (run === null) return undefined
  return `architect: ${run.mode}, ${run.changes.length + run.patterns.length} approved`
}

// Asks and remembers the answer. A dismissed question counts as "No".
async function ask($: any): Promise<Offer> {
  const answer = await $.ui.ask(QUESTION, ANSWERS).catch(() => 'No')
  const next: Offer = answer === 'Yes' ? 'accepted' : answer === 'Not this session' ? 'muted' : 'declined'
  await update($, offer, () => next)
  return next
}

// The prompt to pass on, with a note for the model when the user said yes.
export async function offerOnPrompt($: any, e: any): Promise<any> {
  const isTyped = e.command === undefined && !e.isMeta && !e.text.trimStart().startsWith('/')
  if (!isTyped || !PEOPLE.includes(e.origin?.kind)) return e
  try {
    let state: Offer = await read($, offer)
    if (state !== 'muted') {
      const kind = await $.model.classify(e.text, KINDS)
      if (kind === BIG) state = await ask($)
      if (kind === BIG && state === 'accepted') return noted(e, USE_IT)
    }
    return state === 'declined' || state === 'muted' ? noted(e, DECLINED) : e
  } catch {
    return e
  }
}

// Why an edit made with no run may not happen yet, or null when it may. Edits
// wait only after a yes; an edit never asks on its own.
export async function offerOnEdit($: any, path: string): Promise<string | null> {
  const wait = `architect-mode: ${USE_IT} The user can type /architect-off to skip it.`
  try {
    if ((await read($, offer)) !== 'accepted') return null
    const sessionRoot = await $.session.root()
    const root = await place($, sessionRoot, sessionRoot)
    // A path that cannot be placed waits like any project file.
    if (root === null) return wait
    const target = await place($, path, root)
    return target === null || isInside(target, root) ? wait : null
  } catch {
    return null
  }
}
