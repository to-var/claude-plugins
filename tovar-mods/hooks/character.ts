import type { Mood } from '../types'

// `thinks`: what the character does on screen until their narration arrives.
// Leave it out to use generic ones (thinking, pondering, ...).
export type Character = { name: string; thinks?: string[] }

// calm: shown when idle. working: while Claude works. burning: after a turn
// where a tool call failed.
export type Roster = Record<Mood, Character[]>
