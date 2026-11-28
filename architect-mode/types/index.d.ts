export type Mode = 'strict' | 'warn'
export type Action = 'add' | 'change' | 'delete' | 'move' | 'rename'
export type Change = { path: string; action: Action; reason: string; to?: string }
export type Pattern = { glob: string; command: string }
// root is where the run started, as the file system resolves it.
export type Run = { mode: Mode; root: string; changes: Change[]; patterns: Pattern[] }

// Where the offer of architect mode stands for the current task.
export type Offer = 'unasked' | 'declined' | 'accepted' | 'muted'

declare module 'claude-code' {
  interface PluginState {
    'architect-mode': { run: Run | null; offer: Offer; blocked: string[] }
  }
}
