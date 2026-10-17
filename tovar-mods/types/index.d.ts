export type Mood = 'calm' | 'working' | 'burning'

export type Flight = {
  // The bar this state belongs to; another bar starts fresh.
  bar: string
  mood: Mood
  tools: number
  failures: number
  seconds: number | null
  pick: number
  // Picks the thinking action shown until the narration arrives.
  thought: number
  // Per mood: the characters still to show this round, and the last one shown.
  decks: Record<Mood, number[]>
  last: Record<Mood, number>
  // Bumped each time a new character comes on screen, so a narration only
  // ever lands under the character it was asked from.
  scene: number
  narration: string | null
  // The slash command that ran last, shown on the facts line until the next
  // turn; null after a model turn.
  ran: string | null
}

// The character's take on an open question dialog.
export type Ask = {
  // Bumped per question, so a late take never lands on a newer one.
  id: number
  open: boolean
  // The scene the take was asked from: it shows only under that character.
  scene: number
  text: string | null
}

declare module 'claude-code' {
  interface PluginState {
    'tovar-mods': { flight: Flight; ask: Ask }
  }
}
