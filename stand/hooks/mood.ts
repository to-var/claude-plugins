import type { Member, ThemeData, View } from '../types'

const DOWN = 'Down, but not out.'

export const emptyView = (): View => ({ mood: 'idle', verb: '', tool: null, line: '', party: [] })

export const startTurn = (v: View, verb: string): View => ({ ...v, mood: 'busy', verb, tool: null })
export const startTool = (v: View, tool: string): View => ({ ...v, tool })
export const failTool = (v: View): View => ({ ...v, mood: 'down' })
export const endTurn = (v: View, line: string): View => ({ ...v, mood: 'idle', tool: null, line })
export const joinParty = (v: View, m: Member): View => ({ ...v, party: [...v.party, m].slice(-12) })
export const finishMember = (v: View, id: string): View => ({
  ...v,
  party: v.party.map(m => (m.id === id ? { ...m, isDone: true } : m)),
})

export const describe = (v: View, t: ThemeData | null) => {
  if (t === null) {
    return { title: 'Stand', headline: 'No Stand theme active.', detail: '', party: [] as string[] }
  }
  const headline = v.mood === 'idle' ? v.line : v.mood === 'down' ? DOWN : `${v.verb}...`
  return {
    title: t.name,
    headline,
    detail: v.tool === null ? '' : `using ${v.tool}`,
    party: v.party.map(m => `${m.isDone ? 'done' : 'busy'} ${m.name}`),
  }
}
