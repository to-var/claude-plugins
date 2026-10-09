import { describe, expect, test } from 'claude-code/testing'

import {
  describe as show, emptyView, endTurn, failTool, finishMember, joinParty, startTool, startTurn,
} from '../hooks/mood'

const THEME = { name: 'pokemon', label: 'Pokedex', verbs: ['Evolving'], announcements: ['Go!'], names: ['Pikachu'] }

describe('mood', () => {
  test('a turn goes idle, busy, idle', () => {
    let v = startTurn(emptyView(), 'Evolving')
    expect(v.mood).toBe('busy')
    v = startTool(v, 'Bash')
    expect(v.tool).toBe('Bash')
    v = endTurn(v, 'Go!')
    expect(v).toMatchObject({ mood: 'idle', tool: null, line: 'Go!' })
  })
  test('a failed tool turns the mood down until the turn ends', () => {
    const v = failTool(startTool(startTurn(emptyView(), 'Evolving'), 'Bash'))
    expect(v.mood).toBe('down')
    expect(endTurn(v, 'x').mood).toBe('idle')
  })
  test('the party joins and finishes by id', () => {
    let v = joinParty(emptyView(), { id: 'a', name: 'Pikachu', isDone: false })
    v = finishMember(v, 'a')
    expect(v.party[0]?.isDone).toBe(true)
  })
  test('describe uses the theme words, and a neutral line without a theme', () => {
    const busy = startTool(startTurn(emptyView(), 'Evolving'), 'Bash')
    expect(show(busy, THEME).headline).toContain('Evolving')
    expect(show(busy, THEME).detail).toContain('Bash')
    expect(show(emptyView(), null).title).toBe('Stand')
    expect(show(emptyView(), null).headline).toBe('No Stand theme active.')
  })
})
