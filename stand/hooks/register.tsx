import { atom, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { ThemeData } from '../types'
import { emptyView, endTurn, failTool, finishMember, joinParty, startTool, startTurn } from './mood'
import { pick, pickName } from './party'
import { parseTheme } from './theme-data'

export const view = atom({ plugin: 'stand', key: 'view' } as const, emptyView())

let theme: ThemeData | null = null
let loading: Promise<void> | null = null
const used: string[] = []

async function ensureTheme($: any): Promise<void> {
  loading ??= (async () => {
    try {
      const run = await $.process.run([
        'python3', `${$.plugin.root}/scripts/stand.py`, 'theme', 'active', '--json',
      ])
      theme = run.exitCode === 0 ? parseTheme(run.stdout) : null
    } catch {
      theme = null
    }
    $.ui.log(theme === null ? 'stand: no active Stand theme, the pane stays neutral' : `stand: theme ${theme.name}`)
  })()
  return loading
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await ensureTheme($)
    used.length = 0
    return next(e)
  })

  on('turn.start', async ($, e, next) => {
    await ensureTheme($)
    await update($, view, v => startTurn(v, pick(theme?.verbs ?? []) ?? 'Working'))
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    await update($, view, v => endTurn(v, pick(theme?.announcements ?? []) ?? ''))
    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    await update($, view, v => startTool(v, e.tool))
    const ran = await next(e)
    if (ran.deny === undefined && ran.isError === true) await update($, view, v => failTool(v))
    return ran
  })

  on('tool.call', { tool: 'Agent' }, async ($, e, next) => {
    await ensureTheme($)
    const name = pickName(theme?.names ?? [], used)
    if (name === null) return next(e)
    used.push(name)
    const id = e.tool_use_id
    await update($, view, v => joinParty(v, { id, name, isDone: false }))
    try {
      return await next({ ...e, description: name })
    } finally {
      await update($, view, v => finishMember(v, id))
    }
  })
}
