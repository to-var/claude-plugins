import { describe, expect, test } from 'claude-code/testing'

import { statusText } from '../hooks/offer'

const SKILL = 'architect-mode:architect'

// Stands for the engine, the small model and the person.
const world = (on: any) => {
  const replies: (string | null)[] = []
  const asked: string[] = []
  const ran: string[] = []
  const entered: any[] = []
  const shown: (string | undefined)[] = []
  const model = { label: 'new-code-task' as string | null, calls: 0 }
  on('session.root', () => ({ value: '/p' }))
  on('fs.stat', (_: any, e: any) => {
    const realPath = e.path.replace(/\\/g, '/').replace(/^[A-Za-z]:/, '').replace(/(.)\/$/, '$1')
    return { value: { kind: 'file', size: 0, mtimeMs: 0, isLink: false, realPath } }
  })
  on('ui.status', (_: any, e: any) => {
    shown.push(e.text)
    return { value: undefined }
  })
  on('model.classify', () => {
    model.calls += 1
    return model.label === null ? { deny: 'model down' } : { value: model.label }
  })
  on('session.end', (_: any, e: any) => ({ sessionId: e.sessionId }))
  on('prompt.submit', (_: any, e: any) => {
    entered.push(e)
    return { text: e.text }
  })
  on('tool.call', { tool: 'AskUserQuestion' }, (_: any, e: any) => {
    const { question } = e.questions[0]
    asked.push(question)
    const reply = replies.shift() ?? null
    if (reply === null) return { deny: 'dismissed' }
    return { result: { questions: e.questions, answers: { [question]: reply } } }
  })
  on('tool.call', { tool: 'Edit' }, (_: any, e: any) => {
    ran.push(e.file_path)
    return { result: {} }
  })
  return { replies, asked, ran, entered, shown, model }
}

const say = ($: any, text: string, extra: object = {}) =>
  $.prompt.submit({ text, origin: { kind: 'composer' }, wait: false, ...extra })
const edit = ($: any, file_path = '/p/a.py') =>
  $.tool.call({ tool: 'Edit', file_path, old_string: 'a', new_string: 'b' })
const context = (w: any) => (w.entered.at(-1).context ?? []).join('\n')
const clear = ($: any) => $.session.end({ reason: 'clear', sessionId: 's', resume: {} as any })

describe('offer on the prompt', () => {
  test('a new code task asks once, and yes points at the skill', async ($, on) => {
    const w = world(on)
    w.replies.push('Yes')
    await say($, 'add a login page')
    expect(w.asked).toEqual(['Use architect mode?'])
    expect(context(w)).toContain(SKILL)
    expect(w.entered.at(-1).text).toBe('add a login page')
  })

  test('after yes, edits wait for the run to start', async ($, on) => {
    const w = world(on)
    w.replies.push('Yes')
    await say($, 'add a login page')
    expect((await edit($)).deny).toContain(SKILL)
    expect(w.ran).toEqual([])
    expect(w.asked.length).toBe(1)
  })

  test('follow-ups and other prompts do not ask', async ($, on) => {
    const w = world(on)
    for (const label of ['follow-up', 'other']) {
      w.model.label = label
      await say($, 'hi')
    }
    expect(w.asked).toEqual([])
  })

  test('no keeps the skill away and the next edit passes unasked', async ($, on) => {
    const w = world(on)
    w.replies.push('No')
    await say($, 'add a page')
    expect(context(w)).toContain('declined architect mode')
    w.model.label = 'follow-up'
    await say($, 'make it blue')
    expect(context(w)).toContain('declined architect mode')
    await edit($)
    expect(w.ran).toEqual(['/p/a.py'])
    expect(w.asked.length).toBe(1)
  })

  test('after no, the next new task asks again', async ($, on) => {
    const w = world(on)
    w.replies.push('No', 'No')
    await say($, 'add a page')
    await say($, 'add another')
    expect(w.asked.length).toBe(2)
  })

  test('not this session stops both moments until /clear', async ($, on) => {
    const w = world(on)
    w.replies.push('Not this session')
    await say($, 'add a page')
    await say($, 'add another')
    expect(context(w)).toContain('declined architect mode')
    await edit($)
    expect(w.asked.length).toBe(1)
    await clear($)
    await edit($)
    expect(w.asked.length).toBe(2)
  })

  test('slash commands, hidden prompts and other senders are skipped', async ($, on) => {
    const w = world(on)
    await say($, '/help')
    await say($, 'x', { isMeta: true })
    await say($, 'x', { origin: { kind: 'plugin', name: 'y' } })
    await say($, 'x', { origin: { kind: 'task-notification' } })
    expect(w.model.calls).toBe(0)
    expect(w.entered.length).toBe(4)
  })

  test('a failing model or a dismissed question lets the prompt pass', async ($, on) => {
    const w = world(on)
    w.model.label = null
    await say($, 'add a page')
    expect(w.entered.length).toBe(1)
    w.model.label = 'new-code-task'
    await say($, 'add another')
    expect(w.entered.length).toBe(2)
    await edit($)
    expect(w.ran).toEqual(['/p/a.py'])
  })

  test('the setting off never calls the model or asks', { options: { ask: 'off' } }, async ($, on) => {
    const w = world(on)
    await say($, 'add a page')
    await edit($)
    expect(w.model.calls).toBe(0)
    expect(w.asked).toEqual([])
    expect(w.ran).toEqual(['/p/a.py'])
  })
})

describe('offer on the first edit', () => {
  test('yes blocks that edit and points at the skill', async ($, on) => {
    const w = world(on)
    w.replies.push('Yes')
    expect((await edit($)).deny).toContain(SKILL)
    expect(w.ran).toEqual([])
  })

  test('no passes and does not ask again', async ($, on) => {
    const w = world(on)
    w.replies.push('No')
    await edit($)
    await edit($, '/p/b.py')
    expect(w.ran).toEqual(['/p/a.py', '/p/b.py'])
    expect(w.asked.length).toBe(1)
  })

  test('a dismissed question lets the edit pass', async ($, on) => {
    const w = world(on)
    await edit($)
    expect(w.ran).toEqual(['/p/a.py'])
  })

  test('files outside the project do not ask', async ($, on) => {
    const w = world(on)
    await edit($, '/elsewhere/a.py')
    expect(w.asked).toEqual([])
  })
})

describe('after yes', () => {
  test('a path the plugin cannot place waits too', async ($, on) => {
    const w = world(on)
    w.replies.push('Yes')
    await say($, 'add a login page')
    expect((await edit($, '/p/x/../a.py')).deny).toContain('mcp__architect-mode__start')
    expect(w.ran).toEqual([])
  })
})

describe('proof that it is on', () => {
  test('the status text', () => {
    expect(statusText(null)).toBeUndefined()
    const change = { path: 'a', action: 'change', reason: 'r' } as const
    expect(statusText({ mode: 'strict', root: '/p', changes: [change, change], patterns: [{ glob: 's/*', command: 'x' }] }))
      .toBe('architect: strict, 3 approved')
  })

  test('the status line and /architect-status follow the run', async ($, on) => {
    const w = world(on)
    const status = () =>
      $.command.run({ command: 'architect-status', args: '', origin: { kind: 'composer' } } as any)
    expect((await status()).text).toContain('off')
    w.replies.push('strict', 'Approve all')
    await $.tool.call({ tool: 'mcp__architect-mode__start' })
    await $.tool.call({
      tool: 'mcp__architect-mode__plan',
      changes: [{ path: 'a.py', action: 'change', reason: 'r' }],
    } as any)
    expect(w.shown.at(-1)).toBe('architect: strict, 1 approved')
    await edit($, '/p/secret.py')
    const { text } = await status()
    expect(text).toContain('strict')
    expect(text).toContain('a.py')
    expect(text).toContain('/p/secret.py')
    w.replies.push('Yes')
    await $.tool.call({ tool: 'mcp__architect-mode__finish' })
    expect(w.shown.at(-1)).toBeUndefined()
    await edit($, '/p/later.py')
    expect(w.ran).toEqual(['/p/later.py'])
  })
})
