import type { Roster } from '../../hooks/character'

// `thinks`: what the character does on screen until their narration arrives.
// Leave it out to use generic ones (thinking, pondering, ...).

// calm: shown when idle. working: shown while Claude works.
// burning: shown after a turn where a tool call failed.
// Each name needs a profile in characters/<name-as-slug>.md.
// TODO(tovar-new-bar): replace these example characters with the real roster.
export const ROSTER: Roster = {
  calm: [{ name: 'Idle Example', thinks: ['sipping tea', 'watching the clouds'] }],
  working: [{ name: 'Busy Example', thinks: ['rolling up their sleeves', 'sharpening pencils'] }],
  burning: [{ name: 'Oops Example', thinks: ['sulking', 'muttering darkly'] }],
}
