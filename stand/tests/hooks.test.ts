import { describe, expect, test } from 'claude-code/testing'

import type { View } from '../types'

// The test engine has no $.state, so the view is read from the writes the plugin makes.
const watchView = (on: any) => {
  const writes: View[] = []
  on('state.set', { plugin: 'stand', key: 'view' }, (_$: any, e: any) => {
    writes.push(e.value)
    return { value: { isSet: true, version: writes.length } }
  })
  on('state.get', { plugin: 'stand', key: 'view' }, () => ({
    value: { value: writes[writes.length - 1], version: writes.length },
  }))
  return writes
}

const themeOutput = (names: string[]) =>
  JSON.stringify({
    ok: true,
    data: { name: 'one', label: 'L', verbs: ['Evolving'], announcements: ['Go!'], names },
  })

const answer = (on: any, names: string[]) =>
  on('process.run', () => ({
    value: { exitCode: 0, stdout: themeOutput(names), stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
  }))

const startSession = (on: any) => {
  on('command.register', () => ({ value: undefined }))
  on('ui.log', () => ({ value: undefined }))
  on('session.start', (_$: any, e: any) => ({ cwd: e.cwd }))
}

const spawnAgent = async ($: any, description: string) => {
  try {
    await $.tool.call({ tool: 'Agent', description, prompt: 'x' })
  } catch {
    // the test hook below denies the call, so a rejection is expected
  }
}

describe('stand pane hooks', () => {
  test('a tool call records the tool name in the view', async ($, on) => {
    answer(on, ['Pikachu'])
    const writes = watchView(on)
    on('tool.call', { tool: 'Bash' }, () => ({ deny: 'test stops here' }))
    try {
      await $.tool.call({ tool: 'Bash', command: 'echo hi' })
    } catch {
      // denied on purpose
    }
    expect(writes[writes.length - 1]?.tool).toBe('Bash')
  })

  test('an Agent call gets a theme name and the party records it', async ($, on) => {
    answer(on, ['Pikachu', 'Eevee'])
    const writes = watchView(on)
    const seen: string[] = []
    on('tool.call', { tool: 'Agent' }, (_$, e) => {
      seen.push((e as any).description)
      return { deny: 'test stops here' }
    })
    await spawnAgent($, 'fix bug')
    await spawnAgent($, 'fix other bug')
    expect(seen.length).toBe(2)
    expect(['Pikachu', 'Eevee']).toContain(seen[0])
    expect(['Pikachu', 'Eevee']).toContain(seen[1])
    expect(seen[0]).not.toBe(seen[1])
    const party = writes[writes.length - 1]?.party ?? []
    expect(party.map(m => m.name).sort()).toEqual(['Eevee', 'Pikachu'])
  })

  test('with no names, the Agent description is left alone', async ($, on) => {
    answer(on, [])
    const seen: string[] = []
    on('tool.call', { tool: 'Agent' }, (_$, e) => {
      seen.push((e as any).description)
      return { deny: 'test stops here' }
    })
    await spawnAgent($, 'fix bug')
    expect(seen).toEqual(['fix bug'])
  })

  test('a sub-agent turn ending does not reset the main mood', async ($, on) => {
    answer(on, ['Pikachu'])
    const writes = watchView(on)
    on('turn.start', (_$: any, e: any) => ({ turnId: e.turnId }))
    on('turn.complete', () => ({ text: '' }))
    await ($ as any).turn.start({ text: 'hi', turnId: 't1' })
    expect(writes[writes.length - 1]?.mood).toBe('busy')
    await ($ as any).turn.complete({
      answer: '', durationMs: 1, isAborted: false, turnId: 't2', agentId: 'sub1', reason: 'answer',
    })
    expect(writes[writes.length - 1]?.mood).toBe('busy')
  })

  test('a sub-agent tool call does not change the main tool', async ($, on) => {
    answer(on, ['Pikachu'])
    const writes = watchView(on)
    on('tool.call', { tool: 'Bash' }, () => ({ deny: 'test stops here' }))
    try {
      await $.tool.call({ tool: 'Bash', command: 'echo hi', agentId: 'sub1' } as any)
    } catch {
      // denied on purpose
    }
    expect(writes.at(-1)?.tool ?? null).toBeNull()
  })

  test('the pane is not opened unasked without a theme', async ($, on) => {
    on('process.run', () => ({ deny: 'no python in this test' }))
    const opened: string[] = []
    on('ui.open', (_$: any, e: any) => {
      opened.push(e.id)
      return { value: { isPlaced: false, reason: 'test' } }
    })
    startSession(on)
    await ($ as any).session.start({ cwd: '/' })
    expect(opened).toEqual([])
  })

  test('the pane is opened unasked with a theme', async ($, on) => {
    answer(on, ['Pikachu'])
    const opened: string[] = []
    on('ui.open', (_$: any, e: any) => {
      opened.push(e.id)
      return { value: { isPlaced: false, reason: 'test' } }
    })
    startSession(on)
    await ($ as any).session.start({ cwd: '/' })
    expect(opened).toEqual(['stand'])
  })
})
