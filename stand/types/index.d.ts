export type Mood = 'idle' | 'busy' | 'down'

export type Member = { id: string; name: string; isDone: boolean }

export type View = {
  mood: Mood
  verb: string
  tool: string | null
  line: string
  party: Member[]
}

export type ThemeData = {
  name: string
  label: string
  verbs: string[]
  announcements: string[]
  names: string[]
}

declare module 'claude-code' {
  interface PluginState {
    stand: { view: View }
  }
}
