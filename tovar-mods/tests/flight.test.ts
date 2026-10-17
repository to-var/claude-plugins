import { describe, expect, test } from 'claude-code/testing'

import { chosen, draw, fill } from '../hooks/flight'
import type { Roster } from '../hooks/character'

const ROSTER: Roster = {
  calm: [{ name: 'A' }, { name: 'B' }, { name: 'C' }],
  working: [{ name: 'W' }],
  burning: [{ name: 'X' }],
}
let n = 0
const roll = (): number => (n += 7)

describe('bar state', () => {
  test('state from another bar starts fresh', () => {
    const saved = { bar: 'old', mood: 'calm', decks: { calm: [9, 9], working: [], burning: [] }, last: { calm: 9, working: -1, burning: -1 }, pick: 9 }
    const now = fill(saved as never, 'new')
    expect(now.bar).toBe('new')
    expect(now.decks.calm).toEqual([])
    expect(now.last.calm).toBe(-1)
    expect(now.pick).toBe(0)
  })

  test('state with missing fields fills in, never undefined', () => {
    const now = fill({ mood: 'calm', tools: 3 } as never, 'new')
    expect(now.narration).toBe(null)
    expect(now.scene).toBe(0)
    expect(now.decks.working).toEqual([])
  })

  test('a round shows every character once, never twice in a row', () => {
    let now = fill({}, 'b')
    const shown: number[] = []
    for (let i = 0; i < 9; i += 1) {
      now = draw(now, 'calm', ROSTER, roll)
      shown.push(now.pick)
    }
    expect(new Set(shown.slice(0, 3)).size).toBe(3)
    expect(new Set(shown.slice(3, 6)).size).toBe(3)
    shown.slice(1).forEach((p, i) => expect(p).not.toBe(shown[i]))
  })

  test('indexes past the end of a shorter roster are dropped', () => {
    const now = draw({ ...fill({}, 'b'), decks: { calm: [7, 1], working: [], burning: [] } }, 'calm', ROSTER, roll)
    expect(now.pick).toBe(1)
  })

  test('only a bar the list really holds is on', () => {
    const bars = { real: ROSTER }
    expect(chosen('real', bars)).toBe('real')
    expect(chosen('off', bars)).toBe(null)
    expect(chosen('no-such-bar', bars)).toBe(null)
    expect(chosen('toString', bars)).toBe(null)
    expect(chosen('__proto__', bars)).toBe(null)
    expect(chosen(undefined, bars)).toBe(null)
  })
})
