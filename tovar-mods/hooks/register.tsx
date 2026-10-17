import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Ask, Flight, Mood } from '../types'
import { BARS } from './bars'
import type { Character, Roster } from './character'
import { chosen, draw, fill, START } from './flight'
import { ASK_RULES, RECAP_RULES, TURN_RULES, caption, clip, isSilent, lookIn, questionsOf, shape, slug, thinking, transcript } from './narration'
import type { Look } from './narration'

const roll = (): number => crypto.getRandomValues(new Uint32Array(1))[0] ?? 0

const flight = atom({ plugin: 'tovar-mods', key: 'flight' } as const, START('smash-bros'))
const ask = atom({ plugin: 'tovar-mods', key: 'ask' } as const, { id: 0, open: false, scene: 0, text: null } as Ask)
// Counts questions in this load, so each one gets its own id.
let questions = 0

// The bar the Bar setting picked when this module loaded; a change reloads it.
let bar = 'smash-bros'
let roster: Roster = BARS['smash-bros']!

const pick = (pool: Character[], n: number): Character => pool[n % pool.length] ?? pool[0]!
const whoOf = (now: Flight): Character => pick(roster[now.mood], now.pick)

async function land($: EngineInterface): Promise<Flight> {
  return fill(await read($, flight), bar)
}

// Profiles read this session; a reload starts fresh, so edits to a file show
// after /reload-plugins.
const profiles = new Map<string, string>()

async function profileOf($: EngineInterface, who: Character): Promise<string> {
  const key = `${bar}/${who.name}`
  const known = profiles.get(key)
  if (known !== undefined) {
    return known
  }
  try {
    const text = await $.fs.read(`${$.plugin.root}/bars/${bar}/characters/${slug(who.name)}.md`)
    if (typeof text !== 'string') {
      return `# ${who.name}`
    }
    profiles.set(key, text)
    return text
  } catch {
    return `# ${who.name}`
  }
}

async function lookOf($: EngineInterface, who: Character, mood: Mood): Promise<Look> {
  return lookIn(await profileOf($, who), mood)
}

async function voice(
  $: EngineInterface,
  who: Character,
  rules: string,
  context: string,
  maxTokens: number,
): Promise<string | null> {
  const profile = await profileOf($, who)
  // A failed call (no network, a denied call) counts as no answer, so the
  // facts line stays and /tovar-mods:narrate says the voice was lost.
  try {
    const r = await $.model.complete({
      model: 'haiku',
      system: rules,
      prompt: `Character profile:\n${profile}\n\n${context}`,
      maxTokens,
      timeoutMs: 20000,
    })
    return r.isAnswered ? r.text : null
  } catch {
    return null
  }
}

async function narrate($: EngineInterface, who: Character, scene: number, outcome: string, exchange: string): Promise<void> {
  const text = await voice($, who, TURN_RULES, `Outcome: ${outcome}\n\nLast exchange:\n${exchange}`, 220)
  if (text === null) {
    return
  }
  const silent = isSilent(await profileOf($, who))
  await update($, flight, (state): Flight => {
    const now = fill(state, bar)
    // Only the character who was asked may speak: once another one is on
    // screen, this narration is dropped.
    return now.scene === scene ? { ...now, narration: shape(text, silent, 360) } : now
  })
}

// The character's take on an open question; dropped if a newer question
// opened or this one closed first.
async function takeOn($: EngineInterface, who: Character, id: number, context: string): Promise<void> {
  const text = await voice($, who, ASK_RULES, context, 160)
  if (text === null) {
    return
  }
  const silent = isSilent(await profileOf($, who))
  await update($, ask, (now): Ask => (now.id === id && now.open ? { ...now, text: shape(text, silent, 220) } : now))
}

// A working character comes on with fresh counts; resolves when the work began.
async function startWork($: EngineInterface): Promise<number> {
  await update($, flight, (saved): Flight => ({
    ...draw(fill(saved, bar), 'working', roster, roll),
    tools: 0,
    failures: 0,
    seconds: null,
    narration: null,
    ran: null,
  }))
  return $.clock.now()
}

export const register: Register = (on, options) => {
  const wanted = typeof options.bar === 'string' ? options.bar : 'smash-bros'
  // Bar off (or a bar this version does not ship): every hook steps aside and
  // /tovar-mods:narrate says how to turn one on.
  const picked = chosen(wanted, BARS)
  const isOn = picked !== null
  if (picked !== null) {
    bar = picked
    roster = BARS[picked]!
  }
  const isNarrating = options.narrate !== false
  let startedAt = 0
  let asked = ''
  let toolsUsed: string[] = []

  on('session.start', async ($, e, next) => {
    if (!isOn) {
      await $.command.register({ name: 'narrate', description: 'The character above the prompt narrates the session' })
      return next(e)
    }
    // Start on a random character, not the first in the list: before the
    // first turn, or when the saved state belongs to another bar (the Bar
    // setting changed mid-session). Otherwise a reload keeps the character
    // on screen.
    await update($, flight, (saved): Flight => {
      const now = fill(saved, bar)
      const isFresh = now.seconds === null && now.mood === 'calm'
      return isFresh || saved.bar !== bar ? draw({ ...now, mood: 'calm' }, 'calm', roster, roll) : now
    })
    await $.command.register({
      name: 'narrate',
      description: 'The character above the prompt narrates the whole session so far',
    })
    return next(e)
  })

  on('command.run', { command: 'narrate' }, async $ => {
    if (!isOn) {
      return { text: 'No bar is on. Pick one with the Bar setting in /config.' }
    }
    const now = await land($)
    const who = whoOf(now)
    const { emoji } = await lookOf($, who, now.mood)
    const messages = await $.session.messages()
    const story = Array.isArray(messages) ? transcript(messages, 12000) : ''
    if (story === '') {
      return { text: `${emoji} ${who.name} has nothing to narrate yet.` }
    }
    const text = await voice($, who, RECAP_RULES, `Session so far:\n${story}`, 400)
    if (text === null) {
      return { text: `${emoji} ${who.name} lost their voice. Try again.` }
    }
    const [said, thought] = shape(text, isSilent(await profileOf($, who)), 700).split('\n')
    return { text: `${emoji} ${who.name}: ${thought === undefined ? said : `“${said}”\n${thought}`}` }
  })

  on('prompt.submit', async ($, e, next) => {
    // A slash command line is not work yet: a command that asks the model
    // starts a turn (below), and one that runs alone is met at command.run.
    if (!isOn || e.command !== undefined) {
      return next(e)
    }
    startedAt = await startWork($)
    asked = e.text
    toolsUsed = []
    return next(e)
  }).catch(($, e, next) => next(e))

  on('turn.start', async ($, e, next) => {
    // A turn with no plain prompt before it, such as a command that asks the
    // model. Helper agents' turns are not the user's.
    if (isOn && e.agentId === undefined && (await land($)).mood !== 'working') {
      startedAt = await startWork($)
      asked = e.text
      toolsUsed = []
    }
    return next(e)
  })

  // Built-in commands such as /compact run no model turn, so no turn ends.
  // When one prints output, the idle character sums it up.
  on('command.run', async ($, e, next) => {
    const ran = await next(e)
    if (!isOn || e.command === 'narrate' || typeof ran.text !== 'string' || ran.text.trim() === '') {
      return ran
    }
    try {
      const line = `/${e.command}${e.args === '' ? '' : ` ${e.args}`}`
      await update($, flight, (saved): Flight => {
        const now = fill(saved, bar)
        return { ...draw(now, now.failures > 0 ? 'burning' : 'calm', roster, roll), narration: null, ran: line }
      })
      if (isNarrating) {
        const shown = await land($)
        const exchange = clip(`User ran: ${line}\nOutput: ${ran.text}`, 4000)
        void narrate($, whoOf(shown), shown.scene, 'the command finished', exchange).catch(() => undefined)
      }
    } catch {
      // The bar is decoration: a failure here never touches the command.
    }
    return ran
  })

  // A question dialog: the character on screen reads it and gives a take on
  // the recommended option, or a line for the moment when none is.
  on('tool.call', { tool: 'AskUserQuestion' }, async ($, e, next) => {
    const { text, hasPick } = questionsOf((e as { questions?: unknown }).questions)
    if (!isOn || !isNarrating || text === '') {
      return next(e)
    }
    questions += 1
    const id = questions
    const shown = await land($)
    await update($, ask, (): Ask => ({ id, open: true, scene: shown.scene, text: null }))
    const context = `${hasPick ? 'One option is recommended.' : 'No option is recommended.'}\n\n${text}`
    void takeOn($, whoOf(shown), id, context).catch(() => undefined)
    try {
      return await next(e)
    } finally {
      try {
        await update($, ask, (now): Ask => (now.id === id ? { ...now, open: false, text: null } : now))
      } catch {
        // The take stays until the next question; the answer is what matters.
      }
    }
  })

  on('tool.call', async ($, e, next) => {
    if (!isOn) {
      return next(e)
    }
    toolsUsed.push(e.tool)
    const ran = await next(e)
    const hasFailed = ran.deny === undefined && ran.isError === true
    await update($, flight, (saved): Flight => {
      const now = fill(saved, bar)
      return { ...now, tools: now.tools + 1, failures: now.failures + (hasFailed ? 1 : 0) }
    })
    return ran
  }).catch(($, e, next) => next(e))

  on('turn.complete', async ($, e, next) => {
    // A helper agent finishing is not the end of the user's turn.
    if (!isOn || e.agentId !== undefined) {
      return next(e)
    }
    const seconds = Math.round(((await $.clock.now()) - startedAt) / 1000)
    await update($, flight, (saved): Flight => {
      const now = fill(saved, bar)
      return draw({ ...now, seconds }, now.failures > 0 ? 'burning' : 'calm', roster, roll)
    })
    const done = await next(e)
    if (isNarrating && e.answer.trim() !== '') {
      const tools = toolsUsed.length > 0 ? ` [tools: ${[...new Set(toolsUsed)].join(', ')}]` : ''
      const exchange = clip(`User: ${asked}\nAssistant: ${e.answer}${tools}`, 4000)
      const shown = await land($)
      const outcome =
        shown.failures > 0 ? `${shown.failures} of ${shown.tools} tool calls failed` : `success, ${shown.tools} tool calls`
      void narrate($, whoOf(shown), shown.scene, outcome, exchange).catch(() => undefined)
    }
    return done
  })

  on('ui.render', { component: 'AskUserQuestion' }, async ($, e, next) => {
    const dialog = await next(e)
    if (!isOn || !isNarrating) {
      return dialog
    }
    const now = await read($, ask)
    if (!now.open) {
      return dialog
    }
    const shown = await land($)
    const who = whoOf(shown)
    const look = await lookOf($, who, shown.mood)
    const [said, thought] = now.text !== null && now.scene === shown.scene ? now.text.split('\n') : []
    const { Box, Text } = $.ui.resolve(e)
    return (
      <Box flexDirection="column">
        <Text color={look.color} bold>
          {look.emoji} {who.name} {said === undefined ? 'is reading the question' : 'says:'}
        </Text>
        {said !== undefined && <Text color={look.color}>   “{said}”</Text>}
        {thought !== undefined && <Text color={look.color}>   {thought}</Text>}
        {dialog}
      </Box>
    )
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (!isOn || e.props.hasSurvey) {
      return next(e)
    }

    const now = await land($)
    const who = whoOf(now)
    const look = await lookOf($, who, now.mood)
    const { Box, Text } = $.ui.resolve(e)
    return (
      <Box flexDirection="column">
        <Text color={look.color} bold>
          {look.emoji} {who.name} {now.narration === null ? `is ${thinking(who, now.thought)}` : 'says:'}
        </Text>
        <Box paddingLeft={3}>
          {now.narration === null ? (
            <Text dimColor>{caption(now)}</Text>
          ) : (
            <Box flexDirection="column">
              <Text color={look.color}>“{now.narration.split('\n')[0]}”</Text>
              {now.narration.includes('\n') && <Text color={look.color}>{now.narration.split('\n')[1]}</Text>}
            </Box>
          )}
        </Box>
      </Box>
    )
  })
}
