import type { Flight, Mood } from '../types'
import type { Roster } from './character'

export const START = (bar: string): Flight => ({
  bar,
  mood: 'calm',
  tools: 0,
  failures: 0,
  seconds: null,
  pick: 0,
  thought: 0,
  decks: { calm: [], working: [], burning: [] },
  last: { calm: -1, working: -1, burning: -1 },
  scene: 0,
  narration: null,
  ran: null,
})

export const MOODS: readonly Mood[] = ['calm', 'working', 'burning']

const whole = (value: unknown, fallback: number): number =>
  typeof value === 'number' && Number.isInteger(value) ? value : fallback

const wholes = (value: unknown): number[] =>
  Array.isArray(value) ? value.filter((n): n is number => typeof n === 'number' && Number.isInteger(n)) : []

const perMood = <T,>(make: (mood: Mood) => T): Record<Mood, T> =>
  ({ calm: make('calm'), working: make('working'), burning: make('burning') })

// Saved state can come from an older version or another bar: fill what is
// missing, and start the rounds fresh when the bar changed.
export const fill = (saved: Partial<Flight>, bar: string): Flight => {
  const sameBar = saved.bar === bar
  return {
    bar,
    mood: saved.mood === 'working' || saved.mood === 'burning' ? saved.mood : 'calm',
    tools: whole(saved.tools, 0),
    failures: whole(saved.failures, 0),
    seconds: typeof saved.seconds === 'number' ? saved.seconds : null,
    pick: sameBar ? whole(saved.pick, 0) : 0,
    thought: whole(saved.thought, 0),
    decks: perMood(mood => (sameBar ? wholes(saved.decks?.[mood]) : [])),
    last: perMood(mood => (sameBar ? whole(saved.last?.[mood], -1) : -1)),
    scene: whole(saved.scene, 0),
    narration:
      sameBar && typeof saved.narration === 'string' && saved.narration.trim() !== '' ? saved.narration : null,
    ran: typeof saved.ran === 'string' && saved.ran !== '' ? saved.ran : null,
  }
}

const swap = (list: number[], a: number, b: number): void => {
  const held = list[a]!
  list[a] = list[b]!
  list[b] = held
}

// A fresh round for one mood: every character once, in random order, never
// opening on the character that closed the round before.
const shuffled = (size: number, avoid: number, roll: () => number): number[] => {
  const order = Array.from({ length: size }, (_, i) => i)
  for (let i = size - 1; i > 0; i -= 1) {
    swap(order, i, roll() % (i + 1))
  }
  if (size > 1 && order[0] === avoid) {
    swap(order, 0, 1)
  }
  return order
}

// Moves to `mood` with the next character of its round and a fresh thinking
// action, so no state change ever shows the same character twice in a row.
export const draw = (now: Flight, mood: Mood, roster: Roster, roll: () => number): Flight => {
  const size = roster[mood].length
  const kept = now.decks[mood].filter(i => i < size)
  const [pick = 0, ...rest] = kept.length > 0 ? kept : shuffled(size, now.last[mood], roll)
  return {
    ...now,
    mood,
    pick,
    thought: roll(),
    decks: { ...now.decks, [mood]: rest },
    last: { ...now.last, [mood]: pick },
    scene: now.scene + 1,
  }
}

// The bar a Bar setting names, or null when it is off or names no bar in the
// list (an inherited object key such as toString counts as no bar).
export const chosen = (wanted: unknown, bars: Record<string, Roster>): string | null =>
  typeof wanted === 'string' && wanted !== 'off' && Object.hasOwn(bars, wanted) ? wanted : null
