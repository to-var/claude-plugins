// Every bar, by the name the Bar setting uses. Written by tools/tovar-mods.py.
import type { Roster } from './character'
import { ROSTER as bar0 } from '../bars/legendary-birds/roster'
import { ROSTER as bar1 } from '../bars/smash-bros/roster'

export const BARS: Record<string, Roster> = {
  'legendary-birds': bar0,
  'smash-bros': bar1,
}
