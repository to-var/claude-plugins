import type { Register } from 'claude-code'

import type { ThemeData } from '../types'
import { parseTheme } from './theme-data'

export const register: Register = on => {
  let theme: ThemeData | null = null

  on('session.start', async ($, e, next) => {
    try {
      const run = await $.process.run([
        'python3', `${$.plugin.root}/scripts/stand.py`, 'theme', 'active', '--json',
      ])
      theme = run.exitCode === 0 ? parseTheme(run.stdout) : null
    } catch {
      theme = null
    }
    $.ui.log(theme === null ? 'stand: no active Stand theme, the pane stays neutral' : `stand: theme ${theme.name}`)
    return next(e)
  })
}
