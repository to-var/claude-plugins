import { expect, mock, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import { BARS } from '../hooks/bars'
import type { Mood } from '../types'

const SURFACES = ['terminal', 'desktop'] as const

const esc = (text: string): string => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

const band = (surface: (typeof SURFACES)[number]) => ({
  plugin: 'tovar-mods',
  surface,
  component: 'AbovePrompt' as const,
  props: {
    hasSurvey: false,
    isWorking: false,
    maxRows: 20,
    bodyColumns: 80,
    scroll: { bodyRows: 20, offset: 0 },
    view: {},
  } as never,
})

const USAGE = { input_tokens: 0, output_tokens: 0, cache_creation_input_tokens: 0, cache_read_input_tokens: 0 }

const TURN_END = { reason: 'answer', answer: 'Fixed the token check.', durationMs: 1000, isAborted: false, turnId: 't1' }

// Waits in real time for work a pending tool call left running, which the
// mocked clock's settle does not wait for.
const until = async (ok: () => boolean): Promise<void> => {
  for (let i = 0; i < 200 && !ok(); i += 1) {
    await new Promise(done => setTimeout(done, 5))
  }
}

const SESSION = { cwd: '/tmp', surface: 'terminal', isInteractive: true }

test('off draws nothing and never calls the model', { options: { bar: 'off' } }, async ($, on) => {
  let calls = 0
  const clock = mock.clock(on)
  on('model.complete', () => {
    calls += 1
    return { value: { isAnswered: true, text: 'x', usage: USAGE } } as never
  })
  on('command.register', ($, e) => ({ value: { command: e.name } }) as never)
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('prompt.submit', ($, e) => ({ text: e.text }))
  on('turn.complete', ($, e) => ({ text: e.answer }))
  // What sits beneath the bar: it draws nothing, so anything found is ours.
  on('ui.render', ($, e) => {
    const { Box } = $.ui.resolve(e)
    return <Box />
  })
  await $.session.start(SESSION as never)
  await $.prompt.submit({ text: 'hi' } as never)
  await $.turn.complete(TURN_END as never)
  await clock.settle()
  for (const surface of SURFACES) {
    const ui = await $.ui.mount(band(surface))
    expect(await ui.find({ type: 'Text', text: / is | says:/ })).toBeUndefined()
    expect(await ui.find({ type: 'Text', text: /tool calls|first prompt/ })).toBeUndefined()
    await ui.unmount()
  }
  const ran = await $.command.run({ command: 'narrate', args: '' } as never)
  expect(ran.text).toContain('No bar is on')
  expect(calls).toBe(0)
})

// The engine itself reads a Bar value outside the manifest's options as the
// default, so a made-up name (or an object key like toString) never reaches
// the plugin; the plugin's own guard is covered in flight.test.ts.
for (const wanted of ['no-such-bar', 'toString']) {
  test(`an unknown Bar value ${wanted} reads as the default bar`, { options: { bar: wanted } }, async $ => {
    const smash = BARS['smash-bros']!.calm.map(c => esc(c.name)).join('|')
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: new RegExp(`(${smash}) is `) })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /undefined/ })).toBeUndefined()
      await ui.unmount()
    }
  })
}

for (const bar of Object.keys(BARS)) {
  const roster = BARS[bar]!
  const anyOf = (mood: Mood): string => `(${roster[mood].map(c => esc(c.name)).join('|')})`
  const CALM = anyOf('calm')
  const WORKING = anyOf('working')
  const BURNING = anyOf('burning')
  const CALM_SIZE = roster.calm.length

  test(`${bar}: an idle character thinks before the first prompt`, { options: { bar } }, async $ => {
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: new RegExp(`${CALM} is `) })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /waiting for your first prompt/ })).toBeDefined()
      await ui.unmount()
    }
  })

  test(`${bar}: a working character shows while a turn runs`, { options: { bar } }, async ($, on) => {
    mock.clock(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    await $.prompt.submit({ text: 'hi' } as never)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: new RegExp(`${WORKING} is `) })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /0 tool calls so far/ })).toBeDefined()
      await ui.unmount()
    }
  })

  test(`${bar}: a failed tool call brings on a burning character`, { options: { bar, narrate: false } }, async ($, on) => {
    mock.clock(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('tool.call', () => ({ result: 'exit 1', isError: true }) as never)
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'run the tests' } as never)
    await $.tool.call({ tool: 'Bash', command: 'false', tool_use_id: 'u1' } as never)
    await $.turn.complete(TURN_END as never)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: new RegExp(`${BURNING} is `) })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /1 of 1 tool calls failed last turn/ })).toBeDefined()
      await ui.unmount()
    }
  })

  test(`${bar}: the character narrates the turn on a second line`, { options: { bar } }, async ($, on) => {
    const asked: string[] = []
    on('fs.read', () => ({ value: '# Someone\n\n- **Emoji:** 🧪\n- **Color:** #123456\n- **Speaks:** yes' }) as never)
    const clock = mock.clock(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('model.complete', ($, e) => {
      asked.push(String(e.prompt))
      return { value: { isAnswered: true, text: '"Bug squashed, hooray!"', usage: USAGE } } as never
    })
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'fix the login bug' } as never)
    await $.turn.complete(TURN_END as never)
    await clock.settle()
    expect(asked[0]).toContain('**Color:** #123456')
    expect(asked[0]).toContain('Last exchange:')
    expect(asked[0]).toContain('User: fix the login bug')
    expect(asked[0]).toContain('Assistant: Fixed the token check.')
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      const said = await ui.find({ type: 'Text', text: /“Bug squashed, hooray!”/ })
      const name = await ui.find({ type: 'Text', text: / says:/ })
      expect(said?.props.color).toBe('#123456')
      expect(name?.props.color).toBe('#123456')
      expect(await ui.find({ type: 'Text', text: /🧪/ })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: new RegExp(`${CALM} says:`) })).toBeDefined()
      await ui.unmount()
    }
  })

  test(`${bar}: the look comes from the bar's own profile files`, { options: { bar } }, async ($, on) => {
    const paths: string[] = []
    on('fs.read', ($, e) => {
      paths.push(String(e.path))
      return { value: '# Someone\n\n- **Emoji:** 🦉\n- **Color:** #abcdef\n- **Speaks:** yes' } as never
    })
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      const line = await ui.find({ type: 'Text', text: new RegExp(`${CALM} is `) })
      expect(line?.props.color).toBe('#abcdef')
      expect(String(line?.text)).toContain('🦉')
      await ui.unmount()
    }
    expect(paths.length).toBeGreaterThan(0)
    expect(paths.every(p => new RegExp(`/bars/${esc(bar)}/characters/[a-z0-9-]+\\.md$`).test(p))).toBe(true)
  })

  test(`${bar}: narration stays off when the setting is off`, { options: { bar, narrate: false } }, async ($, on) => {
    let calls = 0
    const clock = mock.clock(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('model.complete', () => {
      calls += 1
      return { value: { isAnswered: true, text: 'nope', usage: USAGE } } as never
    })
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'hi' } as never)
    await $.turn.complete(TURN_END as never)
    await clock.settle()
    expect(calls).toBe(0)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: new RegExp(`${CALM} is `) })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: / says:/ })).toBeUndefined()
      await ui.unmount()
    }
  })

  test(`${bar}: /tovar-mods:narrate recaps the whole session in the character voice`, { options: { bar } }, async ($, on) => {
    const asked: string[] = []
    on('session.messages', () => ({
      value: [
        { role: 'user', text: 'fix the login bug', toolUses: [] },
        { role: 'assistant', text: 'Fixed the token check.', toolUses: [] },
      ],
    }) as never)
    on('model.complete', ($, e) => {
      asked.push(String(e.prompt))
      return { value: { isAnswered: true, text: 'What a session it was!', usage: USAGE } } as never
    })
    const ran = await $.command.run({ command: 'narrate', args: '' } as never)
    expect(ran.text).toMatch(new RegExp(`${CALM}: What a session it was!$`))
    expect(asked[0]).toContain('Session so far:')
    expect(asked[0]).toContain('User: fix the login bug')
  })

  test(`${bar}: /tovar-mods:narrate with an empty session has nothing to say`, { options: { bar } }, async ($, on) => {
    let calls = 0
    on('session.messages', () => ({ value: [] }) as never)
    on('model.complete', () => {
      calls += 1
      return { value: { isAnswered: true, text: 'x', usage: USAGE } } as never
    })
    const ran = await $.command.run({ command: 'narrate', args: '' } as never)
    expect(ran.text).toMatch(new RegExp(`${CALM} has nothing to narrate yet\\.$`))
    expect(calls).toBe(0)
  })

  test(`${bar}: state saved by an older version never shows "undefined"`, { options: { bar } }, async ($, on) => {
    const old = { mood: 'calm', tools: 3, failures: 0, seconds: 12 }
    on('state.get', () => ({ value: { value: old, version: 1 } }) as never)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: /undefined/ })).toBeUndefined()
      expect(await ui.find({ type: 'Text', text: /last turn 12s, 3 tool calls/ })).toBeDefined()
      await ui.unmount()
    }
  })

  test(`${bar}: state saved by another bar never leaks in`, { options: { bar } }, async ($, on) => {
    const other = {
      bar: 'some-other-bar',
      mood: 'calm',
      pick: 99,
      decks: { calm: [99], working: [], burning: [] },
      last: { calm: 99, working: -1, burning: -1 },
      narration: 'A line from another bar.',
    }
    on('state.get', () => ({ value: { value: other, version: 1 } }) as never)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: new RegExp(`${CALM} is `) })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /undefined/ })).toBeUndefined()
      expect(await ui.find({ type: 'Text', text: /another bar/ })).toBeUndefined()
      await ui.unmount()
    }
  })

  // Each session start reads `opening` (fresh state, or state another bar
  // left behind), then the bar reads back what the plugin wrote.
  const startsFrom = async ($: Parameters<TestBody>[0], on: Parameters<TestBody>[1], opening: () => unknown): Promise<string[]> => {
    let stored: unknown
    let version = 0
    on('state.get', () => ({ value: { value: stored, version } }) as never)
    on('state.set', ($, e) => {
      stored = (e as { value: unknown }).value
      version += 1
      return { value: { isSet: true, version } } as never
    })
    on('session.start', ($, e) => ({ cwd: e.cwd }))
    on('command.register', ($, e) => ({ value: { command: e.name } }) as never)
    const firsts: string[] = []
    for (let i = 0; i < 20; i += 1) {
      stored = opening()
      await $.session.start(SESSION as never)
      const names: string[] = []
      for (const surface of SURFACES) {
        const ui = await $.ui.mount(band(surface))
        const line = await ui.find({ type: 'Text', text: new RegExp(`${CALM} is `) })
        expect(line).toBeDefined()
        names.push(String(line?.text).split(' is ')[0]?.replace(/^\S+ /, '') ?? '')
        await ui.unmount()
      }
      expect(names[1]).toBe(names[0])
      firsts.push(names[0] ?? '')
    }
    return firsts
  }

  test(`${bar}: a new session starts on a random character`, { options: { bar } }, async ($, on) => {
    const firsts = await startsFrom($, on, () => ({ bar }))
    // A roster with one idle character has nothing to randomize.
    if (CALM_SIZE > 1) {
      expect(new Set(firsts).size).toBeGreaterThan(1)
    } else {
      expect(new Set(firsts).size).toBe(1)
    }
  })

  test(`${bar}: switching bars mid-session opens on a random character of the new bar`, { options: { bar } }, async ($, on) => {
    const finished = {
      bar: 'some-other-bar',
      mood: 'calm',
      tools: 2,
      failures: 0,
      seconds: 12,
      pick: 3,
      decks: { calm: [1, 2], working: [], burning: [] },
      last: { calm: 3, working: -1, burning: -1 },
      scene: 5,
      narration: null,
    }
    const firsts = await startsFrom($, on, () => structuredClone(finished))
    if (CALM_SIZE > 1) {
      expect(new Set(firsts).size).toBeGreaterThan(1)
    }
  })

  test(`${bar}: each state change shows the next character of a shuffled round`, { options: { bar, narrate: false } }, async ($, on) => {
    mock.clock(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('turn.complete', ($, e) => ({ text: e.answer }))
    const idle: string[] = []
    for (let i = 0; i < CALM_SIZE * 2; i += 1) {
      await $.prompt.submit({ text: `task ${i}` } as never)
      await $.turn.complete(TURN_END as never)
      const names: string[] = []
      for (const surface of SURFACES) {
        const ui = await $.ui.mount(band(surface))
        const line = await ui.find({ type: 'Text', text: / is / })
        names.push(String(line?.text).split(' is ')[0] ?? '')
        await ui.unmount()
      }
      expect(names[1]).toBe(names[0])
      idle.push(names[0] ?? '')
    }
    expect(new Set(idle.slice(0, CALM_SIZE)).size).toBe(CALM_SIZE)
    expect(new Set(idle.slice(CALM_SIZE)).size).toBe(CALM_SIZE)
    if (CALM_SIZE > 1) {
      idle.slice(1).forEach((who, i) => expect(who).not.toBe(idle[i]))
    }
  })

  test(`${bar}: silent characters make sounds, then think the summary on the next line`, { options: { bar } }, async ($, on) => {
    const rules: string[] = []
    const clock = mock.clock(on)
    on('fs.read', () => ({ value: '# Someone\n\n- **Emoji:** 🗡️\n- **Color:** #2e9e44\n- **Speaks:** NO. Out loud, sounds only.' }) as never)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('model.complete', ($, e) => {
      rules.push(String(e.system))
      return { value: { isAnswered: true, text: '"Hup! Hyaah!"\n\nThe login bug is fixed.\nThe tests pass.', usage: USAGE } } as never
    })
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'fix it' } as never)
    await $.turn.complete(TURN_END as never)
    await clock.settle()
    expect(rules[0]).toContain('Second line: their thoughts')
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      const said = await ui.find({ type: 'Text', text: /^“Hup! Hyaah!”$/ })
      const thought = await ui.find({ type: 'Text', text: /^The login bug is fixed\. The tests pass\.$/ })
      expect(said?.props.color).toBe('#2e9e44')
      expect(thought?.props.color).toBe('#2e9e44')
      await ui.unmount()
    }
  })

  test(`${bar}: a speaking character always gets one quoted paragraph`, { options: { bar } }, async ($, on) => {
    const clock = mock.clock(on)
    on('fs.read', () => ({ value: '# Someone\n\n- **Emoji:** 👊\n- **Color:** #3a6fd6\n- **Speaks:** yes' }) as never)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('model.complete', () => ({ value: { isAnswered: true, text: 'Show me your moves!\nThe tests pass!', usage: USAGE } }) as never)
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'fix it' } as never)
    await $.turn.complete(TURN_END as never)
    await clock.settle()
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: /^“Show me your moves! The tests pass!”$/ })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /^The tests pass/ })).toBeUndefined()
      await ui.unmount()
    }
  })

  test(`${bar}: the character thinking is the one who gives the summary`, { options: { bar } }, async ($, on) => {
    const clock = mock.clock(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('model.complete', async () => {
      await clock.sleep(3000)
      return { value: { isAnswered: true, text: 'All done here.', usage: USAGE } } as never
    })
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'fix it' } as never)
    await $.turn.complete(TURN_END as never)
    const thinkers: string[] = []
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      const line = await ui.find({ type: 'Text', text: new RegExp(`${CALM} is `) })
      thinkers.push(String(line?.text).split(' is ')[0] ?? '')
      expect(await ui.find({ type: 'Text', text: / says:/ })).toBeUndefined()
      expect(await ui.find({ type: 'Text', text: /last turn \d+s, 0 tool calls/ })).toBeDefined()
      await ui.unmount()
    }
    await clock.advance(3000)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      const speaking = String((await ui.find({ type: 'Text', text: / says:/ }))?.text).split(' says:')[0]
      expect(await ui.find({ type: 'Text', text: /All done here\./ })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: / is / })).toBeUndefined()
      expect(speaking).toBe(thinkers[0])
      await ui.unmount()
    }
    expect(thinkers[1]).toBe(thinkers[0])
  })

  test(`${bar}: a helper agent finishing changes nothing on the bar`, { options: { bar } }, async ($, on) => {
    let calls = 0
    const clock = mock.clock(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('model.complete', () => {
      calls += 1
      return { value: { isAnswered: true, text: 'Too early.', usage: USAGE } } as never
    })
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'fix it' } as never)
    const before: string[] = []
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      before.push(String((await ui.find({ type: 'Text', text: / is / }))?.text))
      await ui.unmount()
    }
    await $.turn.complete({ ...TURN_END, agentId: 'helper-1' } as never)
    await clock.settle()
    for (const [i, surface] of SURFACES.entries()) {
      const ui = await $.ui.mount(band(surface))
      expect(String((await ui.find({ type: 'Text', text: / is / }))?.text)).toBe(before[i])
      expect(await ui.find({ type: 'Text', text: new RegExp(`${WORKING} is `) })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /tool calls so far/ })).toBeDefined()
      await ui.unmount()
    }
    expect(calls).toBe(0)
  })

  test(`${bar}: a late narration never lands under a newer character`, { options: { bar } }, async ($, on) => {
    const clock = mock.clock(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('model.complete', async () => {
      await clock.sleep(3000)
      return { value: { isAnswered: true, text: 'Old news.', usage: USAGE } } as never
    })
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'first' } as never)
    await $.turn.complete(TURN_END as never)
    await $.prompt.submit({ text: 'second' } as never)
    await clock.advance(3000)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: /Old news/ })).toBeUndefined()
      expect(await ui.find({ type: 'Text', text: new RegExp(`${WORKING} is `) })).toBeDefined()
      await ui.unmount()
    }
  })
  test(`${bar}: a model that gives no answer keeps the facts line`, { options: { bar } }, async ($, on) => {
    const clock = mock.clock(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('model.complete', () => ({
      value: { isAnswered: false, reason: 'api-error', status: 529, error: 'overloaded', usage: USAGE },
    }) as never)
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'fix it' } as never)
    await $.turn.complete(TURN_END as never)
    await clock.settle()
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: new RegExp(`${CALM} is `) })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /last turn \d+s, 0 tool calls/ })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: / says:/ })).toBeUndefined()
      expect(await ui.find({ type: 'Text', text: /undefined|null/ })).toBeUndefined()
      await ui.unmount()
    }
  })

  test(`${bar}: a model call that fails outright keeps the facts line and the turn`, { options: { bar } }, async ($, on) => {
    const clock = mock.clock(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('model.complete', () => ({ deny: 'no network in this test' }))
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'fix it' } as never)
    const done = await $.turn.complete(TURN_END as never)
    await clock.settle()
    expect((done as { text?: string }).text).toBe(TURN_END.answer)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: /last turn \d+s, 0 tool calls/ })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: / says:/ })).toBeUndefined()
      expect(await ui.find({ type: 'Text', text: /undefined|null/ })).toBeUndefined()
      await ui.unmount()
    }
  })

  test(`${bar}: an empty or quotes-only answer keeps the facts line`, { options: { bar } }, async ($, on) => {
    const clock = mock.clock(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('model.complete', () => ({ value: { isAnswered: true, text: ' "" ', usage: USAGE } }) as never)
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'fix it' } as never)
    await $.turn.complete(TURN_END as never)
    await clock.settle()
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: /last turn \d+s, 0 tool calls/ })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: / says:/ })).toBeUndefined()
      expect(await ui.find({ type: 'Text', text: /“”/ })).toBeUndefined()
      await ui.unmount()
    }
  })

  test(`${bar}: a missing profile file falls back to the default emoji and mood color`, { options: { bar } }, async ($, on) => {
    const asked: string[] = []
    const clock = mock.clock(on)
    on('fs.read', () => ({ deny: 'no such file' }))
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('model.complete', ($, e) => {
      asked.push(String(e.prompt))
      return { value: { isAnswered: true, text: 'Done.', usage: USAGE } } as never
    })
    on('turn.complete', ($, e) => ({ text: e.answer }))
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      const line = await ui.find({ type: 'Text', text: new RegExp(`${CALM} is `) })
      expect(String(line?.text)).toMatch(/^🎮 /)
      expect(line?.props.color).toBe('#5fb4ff')
      await ui.unmount()
    }
    await $.prompt.submit({ text: 'fix it' } as never)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      const line = await ui.find({ type: 'Text', text: new RegExp(`${WORKING} is `) })
      expect(line?.props.color).toBe('#f8d030')
      await ui.unmount()
    }
    await $.turn.complete(TURN_END as never)
    await clock.settle()
    expect(asked[0]).toMatch(new RegExp(`Character profile:\\n# ${CALM}\\n`))
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: /^“Done\.”$/ })).toBeDefined()
      await ui.unmount()
    }
  })

  test(`${bar}: a very long narration is clipped`, { options: { bar } }, async ($, on) => {
    const clock = mock.clock(on)
    on('fs.read', () => ({ value: '# Someone\n\n- **Emoji:** 👊\n- **Color:** #3a6fd6\n- **Speaks:** yes' }) as never)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('model.complete', () => ({ value: { isAnswered: true, text: 'word '.repeat(300), usage: USAGE } }) as never)
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'fix it' } as never)
    await $.turn.complete(TURN_END as never)
    await clock.settle()
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      const said = String((await ui.find({ type: 'Text', text: /^“word/ }))?.text)
      expect(said.endsWith('…”')).toBe(true)
      expect(said.length).toBe(362)
      await ui.unmount()
    }
  })

  test(`${bar}: markdown and wrapping quotes from the model are tidied away`, { options: { bar } }, async ($, on) => {
    const clock = mock.clock(on)
    on('fs.read', () => ({ value: '# Someone\n\n- **Emoji:** 👊\n- **Color:** #3a6fd6\n- **Speaks:** yes' }) as never)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('model.complete', () => ({
      value: { isAnswered: true, text: '“**Wahoo!** The `login` bug\n- is _fixed_, and *all* tests pass.”', usage: USAGE },
    }) as never)
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'fix it' } as never)
    await $.turn.complete(TURN_END as never)
    await clock.settle()
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: /^“Wahoo! The login bug is fixed, and all tests pass\.”$/ })).toBeDefined()
      await ui.unmount()
    }
  })

  test(`${bar}: the bar steps aside while a survey shows`, { options: { bar } }, async ($, on) => {
    on('ui.render', ($, e) => {
      const { Box } = $.ui.resolve(e)
      return <Box />
    })
    for (const surface of SURFACES) {
      const target = band(surface) as { props: Record<string, unknown> }
      const ui = await $.ui.mount({ ...band(surface), props: { ...target.props, hasSurvey: true } } as never)
      expect(await ui.find({ type: 'Text', text: / is | says:/ })).toBeUndefined()
      expect(await ui.find({ type: 'Text', text: /first prompt/ })).toBeUndefined()
      await ui.unmount()
    }
  })

  test(`${bar}: a denied tool call counts as a call, not a failure`, { options: { bar, narrate: false } }, async ($, on) => {
    mock.clock(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('tool.call', () => ({ deny: 'not allowed' }))
    on('turn.complete', ($, e) => ({ text: e.answer }))
    await $.prompt.submit({ text: 'run it' } as never)
    try {
      await $.tool.call({ tool: 'Bash', command: 'rm -rf /', tool_use_id: 'u1' } as never)
    } catch {
      // denied on purpose
    }
    await $.turn.complete(TURN_END as never)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: new RegExp(`${CALM} is `) })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /failed/ })).toBeUndefined()
      expect(await ui.find({ type: 'Text', text: /^last turn \d+s, 1 tool calls$/ })).toBeDefined()
      await ui.unmount()
    }
  })

  test(`${bar}: a session start registers /tovar-mods:narrate`, { options: { bar } }, async ($, on) => {
    const names: string[] = []
    on('session.start', ($, e) => ({ cwd: e.cwd }))
    on('command.register', ($, e) => {
      names.push(e.name)
      return { value: { command: e.name } } as never
    })
    await $.session.start(SESSION as never)
    expect(names).toEqual(['narrate'])
  })

  test(`${bar}: a command that prints output gets a summary`, { options: { bar } }, async ($, on) => {
    const asked: string[] = []
    const clock = mock.clock(on)
    on('command.run', () => ({ text: 'Compacted (ctrl+o to see full summary)' }))
    on('model.complete', ($, e) => {
      asked.push(String(e.prompt))
      return { value: { isAnswered: true, text: 'All tidy now.', usage: USAGE } } as never
    })
    await $.command.run({ command: 'compact', args: '' } as never)
    await clock.settle()
    expect(asked[0]).toContain('User ran: /compact')
    expect(asked[0]).toContain('Compacted (ctrl+o to see full summary)')
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: new RegExp(`${CALM} says:`) })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /“All tidy now\.”/ })).toBeDefined()
      await ui.unmount()
    }
  })

  test(`${bar}: the facts line names the command that ran`, { options: { bar, narrate: false } }, async ($, on) => {
    let calls = 0
    on('command.run', () => ({ text: 'Compacted' }))
    on('model.complete', () => {
      calls += 1
      return { value: { isAnswered: true, text: 'x', usage: USAGE } } as never
    })
    await $.command.run({ command: 'compact', args: '' } as never)
    expect(calls).toBe(0)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(band(surface))
      expect(await ui.find({ type: 'Text', text: new RegExp(`${CALM} is `) })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /ran \/compact/ })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /first prompt/ })).toBeUndefined()
      await ui.unmount()
    }
  })

  test(`${bar}: a command that shows no text changes nothing`, { options: { bar } }, async ($, on) => {
    let calls = 0
    const clock = mock.clock(on)
    on('command.run', () => ({}))
    on('model.complete', () => {
      calls += 1
      return { value: { isAnswered: true, text: 'x', usage: USAGE } } as never
    })
    await $.command.run({ command: 'config', args: '' } as never)
    await clock.settle()
    expect(calls).toBe(0)
    const ui = await $.ui.mount(band('terminal'))
    expect(await ui.find({ type: 'Text', text: /waiting for your first prompt/ })).toBeDefined()
    await ui.unmount()
  })

  test(`${bar}: typing a command never brings on a working character by itself`, { options: { bar } }, async ($, on) => {
    on('prompt.submit', ($, e) => ({ text: e.text }))
    await $.prompt.submit({ text: '/compact', command: { name: 'compact', args: '' } } as never)
    const ui = await $.ui.mount(band('terminal'))
    expect(await ui.find({ type: 'Text', text: new RegExp(`${CALM} is `) })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /tool calls so far/ })).toBeUndefined()
    await ui.unmount()
  })

  test(`${bar}: a command that asks the model shows a working character`, { options: { bar } }, async ($, on) => {
    mock.clock(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    on('turn.start', ($, e) => ({ turnId: e.turnId }))
    await $.prompt.submit({ text: '/review', command: { name: 'review', args: '' } } as never)
    await $.turn.start({ text: '', turnId: 't1' } as never)
    const ui = await $.ui.mount(band('terminal'))
    expect(await ui.find({ type: 'Text', text: new RegExp(`${WORKING} is `) })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /0 tool calls so far/ })).toBeDefined()
    await ui.unmount()
  })

  const QUESTIONS = [
    {
      question: 'Which database should we use?',
      header: 'Database',
      multiSelect: false,
      options: [
        { label: 'Postgres (Recommended)', description: 'Solid and well known.' },
        { label: 'SQLite', description: 'One file, no server.' },
      ],
    },
  ]
  const dialog = (surface: (typeof SURFACES)[number], questions: unknown[] = QUESTIONS) => ({
    plugin: 'tovar-mods',
    surface,
    component: 'AskUserQuestion' as const,
    props: { tool: 'AskUserQuestion', questions } as never,
  })
  // Stands for the engine's own dialog beneath the plugin.
  const engineDialog = (on: Parameters<TestBody>[1]) => on('ui.render', () => ({ type: 'engine', ref: 0 }) as never)
  // Nothing of the plugin's around the dialog: the engine's own is drawn.
  const leftAlone = async ($: Parameters<TestBody>[0], surface: (typeof SURFACES)[number]): Promise<void> => {
    let error = ''
    try {
      const ui = await $.ui.mount(dialog(surface))
      error = String(await ui.find({ type: 'Text', text: / says:| is reading/ }))
      await ui.unmount()
    } catch (e) {
      error = String(e)
    }
    expect(error).toMatch(/drew nothing|undefined/)
  }

  test(`${bar}: the character reasons about the recommended option above a question`, { options: { bar } }, async ($, on) => {
    const asked: string[] = []
    const clock = mock.clock(on)
    engineDialog(on)
    let answer = (): void => undefined
    on('tool.call', () => new Promise(done => { answer = () => done({ result: 'Postgres' } as never) }))
    on('model.complete', ($, e) => {
      asked.push(String(e.prompt))
      return { value: { isAnswered: true, text: 'Postgres, a sturdy pick!', usage: USAGE } } as never
    })
    const call = $.tool.call({ tool: 'AskUserQuestion', questions: QUESTIONS, tool_use_id: 'q1' } as never)
    await until(() => asked.length > 0)
    await clock.settle()
    expect(asked[0]).toContain('Question: Which database should we use?')
    expect(asked[0]).toContain('Postgres (Recommended)')
    expect(asked[0]).toContain('One option is recommended')
    for (const surface of SURFACES) {
      const ui = await $.ui.mount(dialog(surface))
      expect(await ui.find({ type: 'Text', text: new RegExp(`${WORKING} says:|${CALM} says:`) })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /“Postgres, a sturdy pick!”/ })).toBeDefined()
      await ui.unmount()
    }
    answer()
    await call
    await leftAlone($, 'terminal')
  })

  test(`${bar}: with no recommended option the character says a line for the moment`, { options: { bar } }, async ($, on) => {
    const asked: string[] = []
    const clock = mock.clock(on)
    engineDialog(on)
    on('tool.call', () => new Promise(() => undefined))
    on('model.complete', ($, e) => {
      asked.push(String(e.prompt))
      return { value: { isAnswered: true, text: 'Choose wisely.', usage: USAGE } } as never
    })
    const open = QUESTIONS.map(q => ({ ...q, options: q.options.map(o => ({ ...o, label: o.label.replace(' (Recommended)', '') })) }))
    void $.tool.call({ tool: 'AskUserQuestion', questions: open, tool_use_id: 'q2' } as never)
    await until(() => asked.length > 0)
    await clock.settle()
    expect(asked[0]).toContain('No option is recommended')
    const ui = await $.ui.mount(dialog('terminal', open))
    expect(await ui.find({ type: 'Text', text: /“Choose wisely\.”/ })).toBeDefined()
    await ui.unmount()
  })

  test(`${bar}: the character reads the question until their take arrives`, { options: { bar } }, async ($, on) => {
    mock.clock(on)
    engineDialog(on)
    on('tool.call', () => new Promise(() => undefined))
    let calls = 0
    on('model.complete', () => {
      calls += 1
      return new Promise(() => undefined)
    })
    void $.tool.call({ tool: 'AskUserQuestion', questions: QUESTIONS, tool_use_id: 'q3' } as never)
    await until(() => calls > 0)
    const ui = await $.ui.mount(dialog('terminal'))
    expect(await ui.find({ type: 'Text', text: / is reading the question/ })).toBeDefined()
    await ui.unmount()
  })

  test(`${bar}: with Narrate off the question dialog is left alone`, { options: { bar, narrate: false } }, async ($, on) => {
    let calls = 0
    const clock = mock.clock(on)
    engineDialog(on)
    on('tool.call', () => new Promise(() => undefined))
    on('model.complete', () => {
      calls += 1
      return { value: { isAnswered: true, text: 'x', usage: USAGE } } as never
    })
    void $.tool.call({ tool: 'AskUserQuestion', questions: QUESTIONS, tool_use_id: 'q4' } as never)
    await new Promise(done => setTimeout(done, 50))
    await clock.settle()
    expect(calls).toBe(0)
    await leftAlone($, 'terminal')
  })

  test(`${bar}: /tovar-mods:narrate says so when the model gives no answer`, { options: { bar } }, async ($, on) => {
    on('session.messages', () => ({ value: [{ role: 'user', text: 'fix the login bug', toolUses: [] }] }) as never)
    on('model.complete', () => ({ value: { isAnswered: false, reason: 'aborted', usage: USAGE } }) as never)
    const ran = await $.command.run({ command: 'narrate', args: '' } as never)
    expect(ran.text).toMatch(new RegExp(`${CALM} lost their voice\\. Try again\\.$`))
    expect(ran.text).not.toMatch(/undefined|null/)
  })

  test(`${bar}: /tovar-mods:narrate says so when the model call fails outright`, { options: { bar } }, async ($, on) => {
    on('session.messages', () => ({ value: [{ role: 'user', text: 'fix the login bug', toolUses: [] }] }) as never)
    on('model.complete', () => ({ deny: 'no network in this test' }))
    const ran = await $.command.run({ command: 'narrate', args: '' } as never)
    expect(ran.text).toMatch(new RegExp(`${CALM} lost their voice\\. Try again\\.$`))
  })

  test(`${bar}: /tovar-mods:narrate gives a silent character sounds, then thoughts`, { options: { bar } }, async ($, on) => {
    on('fs.read', () => ({ value: '# Someone\n\n- **Emoji:** 🗡️\n- **Color:** #2e9e44\n- **Speaks:** NO. Sounds only.' }) as never)
    on('session.messages', () => ({ value: [{ role: 'user', text: 'fix the login bug', toolUses: [] }] }) as never)
    on('model.complete', () => ({ value: { isAnswered: true, text: 'Hup! Hyaah!\nThe bug is gone.\nAll green.', usage: USAGE } }) as never)
    const ran = await $.command.run({ command: 'narrate', args: '' } as never)
    expect(ran.text).toMatch(new RegExp(`^🗡️ ${CALM}: “Hup! Hyaah!”\\nThe bug is gone\\. All green\\.$`))
  })

  test(`${bar}: /tovar-mods:narrate still recaps when Narrate is off`, { options: { bar, narrate: false } }, async ($, on) => {
    on('session.messages', () => ({ value: [{ role: 'user', text: 'fix the login bug', toolUses: [] }] }) as never)
    on('model.complete', () => ({ value: { isAnswered: true, text: 'A fine session.', usage: USAGE } }) as never)
    const ran = await $.command.run({ command: 'narrate', args: '' } as never)
    expect(ran.text).toMatch(new RegExp(`${CALM}: A fine session\\.$`))
  })
}
