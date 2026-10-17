import { describe, expect, test } from 'claude-code/testing'

import { pick, pickName } from '../hooks/party'

describe('pickName', () => {
  test('takes an unused name', () => {
    expect(pickName(['A', 'B'], ['A'], () => 0)).toBe('B')
  })
  test('repeats only after every name is used', () => {
    expect(pickName(['A', 'B'], ['A', 'B'], () => 0)).toBe('A')
  })
  test('returns null with no names', () => {
    expect(pickName([], [])).toBeNull()
  })
})

describe('pick', () => {
  test('returns undefined for an empty list', () => {
    expect(pick([])).toBeUndefined()
  })
})
