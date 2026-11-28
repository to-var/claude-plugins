import type { Run } from '../types'

// Pure rules of the edit lock: which paths are approved and which shell
// commands delete files.

const DRIVE = /^[a-z]:/i

// One spelling per file: forward slashes, absolute, no "." or "..", and lower
// case on a Windows drive, where letter case does not tell files apart.
export function resolvePath(path: string, root: string): string {
  const slashed = path.replace(/\\/g, '/')
  const isAbsolute = slashed.startsWith('/') || DRIVE.test(slashed)
  const full = isAbsolute ? slashed : `${root.replace(/\\/g, '/')}/${slashed}`
  const parts: string[] = []
  for (const part of full.split('/')) {
    if (part === '' || part === '.') continue
    if (part !== '..') parts.push(part)
    else if (parts.length > 0 && !DRIVE.test(parts.at(-1)!)) parts.pop()
  }
  const joined = parts.join('/')
  return DRIVE.test(joined) ? joined.toLowerCase() : `/${joined}`
}

// Ignores letter case: some file systems do too, and "inside" is the locked side.
export function isInside(path: string, root: string): boolean {
  const base = resolvePath(root, root).replace(/\/$/, '').toLowerCase()
  const target = resolvePath(path, root).toLowerCase()
  return target === base || target.startsWith(`${base}/`)
}

// "**" spans folders, "*" stays inside one.
function globToRegExp(glob: string): RegExp {
  const source = glob
    .split(/(\*\*\/|\*\*|\*)/)
    .map(piece => {
      if (piece === '**/') return '(?:.*/)?'
      if (piece === '**') return '.*'
      if (piece === '*') return '[^/]*'
      return piece.replace(/[.+?^${}()|[\]\\]/g, '\\$&')
    })
    .join('')
  return new RegExp(`^${source}$`)
}

export function isApproved(path: string, run: Run, root: string): boolean {
  const target = resolvePath(path, root)
  const named = run.changes.some(change =>
    [change.path, change.to].some(p => p !== undefined && resolvePath(p, root) === target),
  )
  if (named) return true
  // A pattern is relative to the project and never reaches outside it.
  const base = resolvePath(root, root).replace(/\/$/, '')
  return run.patterns.some(({ glob }) => globToRegExp(resolvePath(glob, root)).test(target) && target.startsWith(`${base}/`))
}

// Braces and backticks open a new command too: "{ rm a; }", "% { ri $_ }".
const SEPARATOR = /\r?\n|;|&&|\|\||\||&|\(|\{|`/
// Words that only carry the real command.
const PREFIX = /^\s*(?:(?:sudo(?:\s+-[ugp]\s+\S+|\s+-\w+)*|time|then|do|command|env|npx|cmd(?:\.exe)?\s+\/\/?[ck]|(?:ba|z)?sh\s+-c|(?:powershell|pwsh)(?:\.exe)?(?:\s+-(?!c)\w+)*\s+-c(?:ommand)?)\s+["']?|\w+=\S*\s+|\\|(?:\/usr)?\/bin\/)*/i
const GIT = String.raw`^git\s+(?:-C\s+\S+\s+)?`
// Commands that delete files, or throw away work that is not committed.
const DELETE = [
  /^(?:rm|rmdir|rimraf|del|erase|rd|ri|unlink|remove-item)(?:\s|$)/i,
  new RegExp(`${GIT}(?:rm|clean|restore(?!\\s+--staged(?!.*--worktree)))(?:\\s|$)`),
  new RegExp(`${GIT}checkout\\s+(?:.*\\s)?(?:--|\\.)(?:\\s|$)`),
  // A tree and a path, or one name that looks like a file.
  new RegExp(`${GIT}checkout(?!.*\\s(?:-b|-B|-t|--track|--orphan)(?:\\s|$))(?:\\s+-\\S+)*\\s+(?:[^-\\s]\\S*\\s+[^-\\s]|[^-\\s]\\S*\\.[A-Za-z]{1,5}(?:\\s|$))`),
  new RegExp(`${GIT}reset\\s+(?:.*\\s)?--hard(?:\\s|$)`),
  new RegExp(`${GIT}stash(?!\\s+(?:list|show|pop|apply|branch))(?:\\s|$)`),
  /^find\s.*\s(?:-delete|-exec(?:dir)?\s+rm)(?:\s|$)/,
  /^xargs\s+(?:-\S+\s+)*rm(?:\s|$)/,
]
const DOTNET_DELETE = /\[(?:System\.)?IO\.(?:File|Directory)\]::Delete\(/i

// Best effort: a script or a program can still delete files unseen.
export function isDelete(command: string): boolean {
  if (DOTNET_DELETE.test(command)) return true
  return command.split(SEPARATOR).some(segment => {
    const start = segment.replace(PREFIX, '')
    return DELETE.some(pattern => pattern.test(start))
  })
}
