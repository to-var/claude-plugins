import { describe, expect, test } from 'claude-code/testing'

import { parseTheme } from '../hooks/theme-data'

const GOOD = JSON.stringify({
  ok: true,
  data: { name: 'one', label: 'L', verbs: ['v'], announcements: ['a'], names: ['n'] },
})
describe('parseTheme', () => {
  test('reads a good answer', () => {
    expect(parseTheme(GOOD)?.name).toBe('one')
  })
  test('returns null for garbage, not-ok and missing fields', () => {
    expect(parseTheme('oops')).toBeNull()
    expect(parseTheme(JSON.stringify({ ok: false, data: {} }))).toBeNull()
    expect(parseTheme(JSON.stringify({ ok: true, data: { name: 'x' } }))).toBeNull()
  })
})
