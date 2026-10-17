import type { Roster } from '../../hooks/character'

// One legendary bird per mood: calm when idle, working while Claude works,
// burning after a turn where a tool call failed.
export const ROSTER: Roster = {
  calm: [{ name: 'Articuno', thinks: ['gazing at the falling snow', 'drifting on cold winds'] }],
  working: [{ name: 'Zapdos', thinks: ['crackling with static', 'storing up thunder'] }],
  burning: [{ name: 'Moltres', thinks: ['smoldering quietly', 'circling the volcano'] }],
}
