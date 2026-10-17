import type { Register } from 'claude-code'

import type { ThemeData } from '../types'
import { pickName } from './party'
import { parseTheme } from './theme-data'

// Gives each sub-agent a name from the active theme's names list.

let theme: ThemeData | null = null
let loading: Promise<void> | null = null
const used: string[] = []

async function ensureTheme($: any): Promise<void> {
  loading ??= (async () => {
    try {
      const run = await $.process.run([
        'python3', `${$.plugin.root}/scripts/tovar.py`, 'theme', 'active', '--json',
      ])
      theme = run.exitCode === 0 ? parseTheme(run.stdout) : null
    } catch {
      theme = null
    }
    $.ui.log(
      theme === null ? 'tovar: no active tovar theme, sub-agents keep their names' : `tovar: theme ${theme.name}`,
      { to: 'debug' },
    )
  })()
  return loading
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await ensureTheme($)
    used.length = 0
    return next(e)
  })

  on('tool.call', { tool: 'Agent' }, async ($, e, next) => {
    await ensureTheme($)
    const name = pickName(theme?.names ?? [], used)
    if (name === null) return next(e)
    used.push(name)
    return next({ ...e, description: name })
  })
}
