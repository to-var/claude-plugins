export type Mode = 'strict' | 'warn'
export type Action = 'add' | 'change' | 'delete' | 'move' | 'rename'
export type Change = { path: string; action: Action; reason: string; to?: string }
export type Pattern = { glob: string; command: string }
// root is where the run started, as the file system resolves it.
export type Run = { mode: Mode; root: string; changes: Change[]; patterns: Pattern[] }

// Where the offer of architect mode stands for the current task.
export type Offer = 'unasked' | 'declined' | 'accepted' | 'muted'

export type NoteKind = 'decision' | 'pattern' | 'tree'
export type Note = { kind: NoteKind; title: string; text: string; sources: string[] }
export type Answer = { question: string; text: string }
// What the notes pane shows. epoch grows at /clear, so a late answer is dropped.
export type PaneState = {
  epoch: number
  decisions: Note[]
  patterns: Note[]
  tree: Note | null
  answers: Answer[]
  pending: string | null
  warning: string | null
}

declare module 'claude-code' {
  interface PluginState {
    'architect-mode': { run: Run | null; offer: Offer; blocked: string[]; pane: PaneState }
  }
}
