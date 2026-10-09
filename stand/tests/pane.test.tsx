import { describe, expect, test } from 'claude-code/testing'

import type { View } from '../types'

const PANE = { title: 'Stand', isFocused: false, bodyColumns: 40, placement: 'dock' } as never

const watchView = (on: any) => {
  const writes: View[] = []
  on('state.set', { plugin: 'stand', key: 'view' }, (_$: any, e: any) => {
    writes.push(e.value)
    return { value: { isSet: true, version: writes.length } }
  })
  on('state.get', { plugin: 'stand', key: 'view' }, () => ({
    value: { value: writes[writes.length - 1], version: writes.length },
  }))
}

const answer = (on: any, names: string[]) =>
  on('process.run', () => ({
    value: {
      exitCode: 0,
      stdout: JSON.stringify({
        ok: true,
        data: { name: 'one', label: 'L', verbs: ['Evolving'], announcements: ['Go!'], names },
      }),
      stderr: '',
      isStdoutTruncated: false,
      isStderrTruncated: false,
    },
  }))

describe('stand pane', () => {
  test('draws the neutral state with no theme', async ($, on) => {
    watchView(on)
    on('process.run', () => ({ deny: 'no python in this test' }))
    const ui = await $.ui.mount({
      plugin: 'stand', surface: 'terminal', component: 'Pane', props: PANE, requestId: 'stand',
    })
    expect(await ui.find({ type: 'Text', text: /No Stand theme active/ })).toBeDefined()
    await ui.unmount()
  })

  test('draws the theme name and the party after a sub-agent call', async ($, on) => {
    watchView(on)
    answer(on, ['Pikachu'])
    on('tool.call', { tool: 'Agent' }, () => ({ deny: 'test stops here' }))
    try {
      await $.tool.call({ tool: 'Agent', description: 'fix bug', prompt: 'x' })
    } catch {
      // denied on purpose
    }
    const ui = await $.ui.mount({
      plugin: 'stand', surface: 'terminal', component: 'Pane', props: PANE, requestId: 'stand',
    })
    expect(await ui.find({ type: 'Text', text: /one/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Pikachu/ })).toBeDefined()
    await ui.unmount()
  })
})
