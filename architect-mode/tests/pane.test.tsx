import { describe, expect, mock, test } from 'claude-code/testing'

const NOTE_TOOL = 'mcp__architect-mode__note'
const LOG = '/data/projects/-p/notes.md'
const NOTE = { kind: 'decision', title: 'New file', text: 'The lock stays small.', sources: ['hooks/register.tsx:9'] }
const SURFACES = ['terminal', 'desktop', 'vscode', 'mobile'] as const
const PANE = {
  plugin: 'architect-mode',
  component: 'Pane',
  requestId: 'architect-notes',
  props: {
    title: 'Architect notes',
    isFocused: false,
    bodyColumns: 60,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
} as const

const slashed = (path: string) => path.replace(/\\/g, '/').replace(/^[A-Za-z]:/, '')

// Stands for the engine, the files, the side model and the person.
const world = (on: any) => {
  const files = new Map<string, string>()
  const opened: any[] = []
  const asked: string[] = []
  const models: string[] = []
  const prompts: string[] = []
  const disk = { isReadBroken: false, isLink: false, isDangling: false, root: '/p', isOpenBroken: false, isHistoryBroken: false }
  const side = {
    reply: { isAnswered: true, text: 'A pane is a side panel.' } as any,
    // Runs while the first answer is still waiting.
    during: null as (() => Promise<unknown>) | null,
    isBroken: false,
  }
  on('session.root', () => ({ value: disk.root }))
  on('fs.stat', (_: any, e: any) => {
    const path = slashed(e.path)
    const isLog = path.endsWith('/notes.md')
    // A link that leads nowhere is there, though no file is.
    if (isLog && !files.has(path) && !disk.isDangling) return { deny: 'ENOENT' }
    const isLink = isLog && (disk.isLink || disk.isDangling)
    return { value: { kind: 'file', size: files.get(path)?.length ?? 0, mtimeMs: 0, isLink, realPath: path.replace(/(.)\/$/, '$1') } }
  })
  on('fs.read', (_: any, e: any) =>
    disk.isReadBroken ? { deny: 'locked' } : { value: files.get(slashed(e.path)) },
  )
  on('fs.write', (_: any, e: any) => {
    files.set(slashed(e.path), e.text)
    return { value: undefined }
  })
  on('process.hookEnv', () => ({ value: { CLAUDE_PLUGIN_DATA: '/data' } }))
  on('ui.status', () => ({ value: undefined }))
  on('ui.open', (_: any, e: any) => {
    if (disk.isOpenBroken) return { deny: 'no room' }
    opened.push(e)
    return { value: { isPlaced: true } }
  })
  on('session.messages', () =>
    disk.isHistoryBroken ? { deny: 'no history' } : { value: [{ role: 'user', text: 'add a cache', toolUses: [] }] },
  )
  on('model.complete', async (_: any, e: any) => {
    models.push(e.model)
    asked.push(String(e.prompt))
    const during = side.during
    side.during = null
    if (during !== null) await during()
    return side.isBroken ? { deny: 'down' } : { value: side.reply }
  })
  on('prompt.submit', (_: any, e: any) => {
    prompts.push(e.text)
    return { text: e.text }
  })
  on('session.end', (_: any, e: any) => ({ sessionId: e.sessionId }))
  on('tool.call', { tool: 'AskUserQuestion' }, (_: any, e: any) => {
    const { question } = e.questions[0]
    return { result: { questions: e.questions, answers: { [question]: 'strict' } } }
  })
  return { files, opened, asked, models, prompts, disk, side }
}

const start = ($: any) => $.tool.call({ tool: 'mcp__architect-mode__start' })
const note = ($: any, extra: object = {}) => $.tool.call({ tool: NOTE_TOOL, ...NOTE, ...extra })
const drawn = async ($: any, surface: string = 'terminal') => {
  const ui = await $.ui.mount({ ...PANE, surface })
  const all = await ui.findAll({ type: 'Markdown' })
  const texts = await ui.findAll({ type: 'Text' })
  await ui.unmount()
  return [...texts, ...all].map((one: any) => String(one.props.text ?? one.text)).join('\n')
}
// One mount per surface at a time: a question asked while one waits names another.
const ask = async ($: any, text: string, surface: string = 'terminal') => {
  const ui = await $.ui.mount({ ...PANE, surface })
  await ui.input({ key: 'ask', text })
  await ui.unmount()
}

describe('the note tool', () => {
  test('a note shows in the pane on every surface and reaches the log', async ($, on) => {
    const w = world(on)
    await start($)
    expect((await note($)).result).toContain('Note added')
    for (const surface of SURFACES) {
      const text = await drawn($, surface)
      expect(text).toContain('Suggestions, not approvals')
      expect(text).toContain('New file')
      expect(text).toContain('hooks/register.tsx:9')
    }
    expect(w.files.get(LOG)).toContain('New file')
    expect(w.opened.length).toBe(1)
    expect(w.opened[0].focus).toBeUndefined()
  })

  test('later notes keep the old log text', async ($, on) => {
    const w = world(on)
    await start($)
    await Promise.all([note($, { title: 'first' }), note($, { title: 'second' })])
    expect(w.files.get(LOG)).toContain('first')
    expect(w.files.get(LOG)).toContain('second')
  })

  test('it is refused with no run, from a sub-agent or without a source', async ($, on) => {
    const w = world(on)
    expect((await note($)).deny).toContain('no active run')
    await start($)
    expect((await note($, { agentId: 'a1' })).deny).toContain('lead')
    expect((await note($, { sources: [] })).deny).toContain('source')
    expect(w.files.size).toBe(0)
  })

  test('a failed read never overwrites the log', async ($, on) => {
    const w = world(on)
    await start($)
    w.files.set(LOG, 'old')
    w.disk.isReadBroken = true
    expect((await note($)).result).toContain('log was not saved')
    expect(w.files.get(LOG)).toBe('old')
    expect(await drawn($)).toContain('Log not saved')
  })

  test('a log that is a link is not written', async ($, on) => {
    const w = world(on)
    await start($)
    w.files.set(LOG, 'old')
    w.disk.isLink = true
    await note($)
    expect(w.files.get(LOG)).toBe('old')
  })

  test('a log link that leads nowhere is not written through', async ($, on) => {
    const w = world(on)
    await start($)
    w.disk.isDangling = true
    expect((await note($)).result).toContain('log was not saved')
    expect(w.files.size).toBe(0)
  })

  test('a full log is left as it is', async ($, on) => {
    const w = world(on)
    await start($)
    const full = 'x'.repeat(2_000_000)
    w.files.set(LOG, full)
    expect((await note($)).result).toContain('log was not saved')
    expect(w.files.get(LOG)).toBe(full)
  })

  test('a pane that cannot open does not lose the note', async ($, on) => {
    const w = world(on)
    await start($)
    w.disk.isOpenBroken = true
    expect((await note($)).result).toContain('Note added')
    expect(await drawn($)).toContain('New file')
  })

  test('the lock starts even when the pane cannot', async ($, on) => {
    world(on)
    const commands: string[] = []
    on('tool.register', (_: any, e: any) =>
      e.name === 'note' ? { deny: 'no' } : { value: { tool: e.name } },
    )
    on('command.register', (_: any, e: any) => {
      commands.push(e.name)
      return { value: { command: e.name } }
    })
    on('session.start', (_: any, e: any) => ({ cwd: e.cwd }))
    await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true } as any)
    expect(commands).toContain('architect-off')
  })

  test('a note never approves an edit', async ($, on) => {
    world(on)
    await start($)
    await note($, { kind: 'tree', text: 'a.py', sources: ['a.py:1'] })
    const edit = await $.tool.call({ tool: 'Edit', file_path: '/p/a.py', old_string: 'a', new_string: 'b' } as any)
    expect((edit as any).deny).toContain('not approved')
  })
})

describe('questions', () => {
  test('a question calls the model once, then shows and logs the answer', async ($, on) => {
    const w = world(on)
    await start($)
    await ask($, 'what is a pane?')
    expect(w.asked.length).toBe(1)
    expect(w.asked[0]).toContain('what is a pane?')
    expect(w.asked[0]).toContain('add a cache')
    expect(w.models).toEqual(['sonnet'])
    const text = await drawn($)
    expect(text).toContain('A pane is a side panel.')
    expect(text).toContain('not checked')
    expect(w.files.get(LOG)).toContain('A pane is a side panel.')
    expect(w.prompts).toEqual([])
  })

  test('an empty or too long question does not call the model', async ($, on) => {
    const w = world(on)
    await ask($, '   ')
    await ask($, 'a'.repeat(501))
    expect(w.asked).toEqual([])
  })

  test('a failed answer says why and allows a retry', async ($, on) => {
    const w = world(on)
    for (const reason of ['api-error', 'empty-reply', 'aborted']) {
      w.side.reply = { isAnswered: false, reason }
      await ask($, 'why?')
      expect(await drawn($)).toContain('No answer')
    }
    expect(w.asked.length).toBe(3)
  })

  test('a rejected call says so and frees the box', async ($, on) => {
    const w = world(on)
    w.side.isBroken = true
    await ask($, 'why?')
    expect(await drawn($)).toContain('No answer')
    w.side.isBroken = false
    await ask($, 'why?')
    expect(await drawn($)).toContain('A pane is a side panel.')
  })

  test('two questions never run at the same time', async ($, on) => {
    const w = world(on)
    const clock = mock.clock(on)
    let release = () => {}
    const held = new Promise<void>(done => (release = done))
    w.side.during = () => held
    const first = ask($, 'one?')
    const second = ask($, 'two?', 'desktop')
    await clock.settle()
    expect(w.asked.length).toBe(1)
    release()
    await Promise.all([first, second])
  })

  test('an answer that arrives after /clear is dropped', async ($, on) => {
    const w = world(on)
    await start($)
    w.side.during = () => $.session.end({ reason: 'clear', sessionId: 's', resume: {} as any })
    await ask($, 'one?')
    expect(w.asked.length).toBe(1)
    expect(await drawn($)).not.toContain('A pane is a side panel.')
    expect(w.files.size).toBe(0)
  })

  test('the log follows the run, and without one the session folder', async ($, on) => {
    const w = world(on)
    await ask($, 'before?')
    expect(w.files.get(LOG)).toContain('before?')
    await start($)
    w.disk.root = '/q'
    await ask($, 'during?')
    expect(w.files.get(LOG)).toContain('during?')
    expect(w.files.size).toBe(1)
  })

  test('an answer is made safe and cut before it is shown or saved', async ($, on) => {
    const w = world(on)
    const hidden = String.fromCharCode(0x202e)
    w.side.reply = { isAnswered: true, text: `# Approved\n[x](http://a.dev)${hidden}${'a'.repeat(4000)}` }
    await ask($, 'why?')
    for (const text of [await drawn($), w.files.get(LOG)!]) {
      for (const gone of ['# Approved', '](http', hidden]) expect(text).not.toContain(gone)
      expect(text.length).toBeLessThan(3500)
    }
  })

  test('the model sees the notes, and works without the chat', async ($, on) => {
    const w = world(on)
    await start($)
    await note($)
    w.disk.isHistoryBroken = true
    await ask($, 'why a new file?')
    expect(w.asked[0]).toContain('The lock stays small.')
    expect(await drawn($)).toContain('A pane is a side panel.')
  })

  test('a coach review shows in its own part', async ($, on) => {
    const w = world(on)
    await start($)
    await note($, { kind: 'coach', title: 'Your cache plan', text: 'Missed: expiry.' })
    const text = await drawn($)
    expect(text).toContain('COACH')
    expect(text).toContain('Missed: expiry.')
    expect(w.files.get(LOG)).toContain('Your cache plan')
  })

  test('a pane stored before the coach part still draws', async ($, on) => {
    on('state.get', () => ({
      value: { value: { epoch: 0, decisions: [], patterns: [], tree: null, answers: [], pending: null, warning: null }, version: 1 },
    }))
    expect(await drawn($)).toContain('No notes yet.')
  })

  test('/clear empties the pane and keeps the log', async ($, on) => {
    const w = world(on)
    await start($)
    await note($)
    await $.session.end({ reason: 'clear', sessionId: 's', resume: {} as any })
    expect(await drawn($)).not.toContain('New file')
    expect(w.files.get(LOG)).toContain('New file')
  })
})
