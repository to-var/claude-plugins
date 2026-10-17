import { describe, expect, test } from 'claude-code/testing'

const themeOutput = (names: string[]) =>
  JSON.stringify({
    ok: true,
    data: { name: 'one', label: 'L', verbs: ['Evolving'], announcements: ['Go!'], names },
  })

const answer = (on: any, names: string[]) =>
  on('process.run', () => ({
    value: { exitCode: 0, stdout: themeOutput(names), stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
  }))

const noTheme = (on: any) =>
  on('process.run', () => ({
    value: { exitCode: 1, stdout: '', stderr: 'No tovar theme is active.', isStdoutTruncated: false, isStderrTruncated: false },
  }))

const quietLog = (on: any) => on('ui.log', () => ({ value: undefined }))

const spawnAgent = async ($: any, description: string) => {
  try {
    await $.tool.call({ tool: 'Agent', description, prompt: 'x' })
  } catch {
    // the test hook below denies the call, so a rejection is expected
  }
}

const watchAgents = (on: any) => {
  const seen: string[] = []
  on('tool.call', { tool: 'Agent' }, (_$: any, e: any) => {
    seen.push(e.description)
    return { deny: 'test stops here' }
  })
  return seen
}

describe('sub-agent names', () => {
  test('each sub-agent gets a different name from the theme', async ($, on) => {
    answer(on, ['Pikachu', 'Eevee'])
    quietLog(on)
    const seen = watchAgents(on)
    await spawnAgent($, 'fix bug')
    await spawnAgent($, 'fix other bug')
    expect(seen.length).toBe(2)
    expect(['Pikachu', 'Eevee']).toContain(seen[0])
    expect(['Pikachu', 'Eevee']).toContain(seen[1])
    expect(seen[0]).not.toBe(seen[1])
  })

  test('names repeat only after every name was used', async ($, on) => {
    answer(on, ['Pikachu'])
    quietLog(on)
    const seen = watchAgents(on)
    await spawnAgent($, 'a')
    await spawnAgent($, 'b')
    expect(seen).toEqual(['Pikachu', 'Pikachu'])
  })

  test('with no names, the description is left alone', async ($, on) => {
    answer(on, [])
    quietLog(on)
    const seen = watchAgents(on)
    await spawnAgent($, 'fix bug')
    expect(seen).toEqual(['fix bug'])
  })

  test('with no active theme, the description is left alone', async ($, on) => {
    noTheme(on)
    quietLog(on)
    const seen = watchAgents(on)
    await spawnAgent($, 'fix bug')
    expect(seen).toEqual(['fix bug'])
  })

  test('a session start asks the engine for the active theme and registers no command', async ($, on) => {
    const asked: string[][] = []
    const commands: string[] = []
    on('process.run', (_$: any, e: any) => {
      asked.push([...e.argv])
      return {
        value: { exitCode: 0, stdout: themeOutput(['Pikachu']), stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
      }
    })
    on('command.register', (_$: any, e: any) => {
      commands.push(e.name)
      return { value: undefined }
    })
    quietLog(on)
    on('session.start', (_$: any, e: any) => ({ cwd: e.cwd }))
    await ($ as any).session.start({ cwd: '/' })
    expect(commands).toEqual([])
    expect(asked.length).toBe(1)
    expect(asked[0]?.[0]).toBe('python3')
    expect(asked[0]?.[1]).toMatch(/\/scripts\/tovar\.py$/)
    expect(asked[0]?.slice(2)).toEqual(['theme', 'active', '--json'])
  })
})
