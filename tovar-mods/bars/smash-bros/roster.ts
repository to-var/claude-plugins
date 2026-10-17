import type { Roster } from '../../hooks/character'

// calm: shown when idle. working: shown while Claude works.
// burning: shown after a turn where a tool call failed.
// Each name needs a profile in characters/<name-as-slug>.md.
// Idle shows neutral fighters, work shows heroes, a failed turn shows villains.
export const ROSTER: Roster = {
  calm: [
    { name: 'Wario', thinks: ['counting his coins', 'munching on garlic'] },
    { name: 'King Dedede', thinks: ['snacking on the royal pantry', 'plotting against Kirby'] },
    { name: 'Meta Knight', thinks: ['brooding on a cliff', 'polishing Galaxia'] },
    { name: 'Mewtwo', thinks: ['meditating', 'reading your mind'] },
    { name: 'Bayonetta', thinks: ['twirling a lollipop', 'admiring her guns'] },
    { name: 'Mr. Game & Watch', thinks: ['flipping pancakes', 'beeping softly'] },
    { name: 'R.O.B.', thinks: ['computing', 'spinning its gyro'] },
    { name: 'Steve', thinks: ['punching a tree', 'crafting at the table'] },
  ],
  working: [
    { name: 'Captain Falcon', thinks: ['revving the Blue Falcon', 'striking a pose'] },
    { name: 'Link', thinks: ['checking the Sheikah Slate', 'cooking by the fire'] },
    { name: 'Pikachu', thinks: ['charging its cheeks', 'hugging a ketchup bottle'] },
    { name: 'Samus', thinks: ['scanning with her visor', 'rolling in Morph Ball'] },
    { name: 'Mario', thinks: ['hopping in place', 'checking the warp pipes'] },
    { name: 'Kirby', thinks: ['napping on a cloud', 'eating a Maxim Tomato'] },
    { name: 'Ryu', thinks: ['meditating', 'training in silence'] },
    { name: 'Cloud', thinks: ['brooding', 'leaning on his Buster Sword'] },
    { name: 'Sora', thinks: ['thinking of his friends', 'twirling his Keyblade'] },
    { name: 'Fox', thinks: ['scanning the radar', 'tuning his Arwing'] },
  ],
  burning: [
    { name: 'Bowser', thinks: ['plotting a kidnapping', 'stomping around the castle'] },
    { name: 'Ganondorf', thinks: ['brooding on his throne', 'scheming in the dark'] },
    { name: 'Sephiroth', thinks: ['watching from the shadows', 'contemplating despair'] },
    { name: 'Ridley', thinks: ['circling overhead', 'sharpening his claws'] },
    { name: 'King K. Rool', thinks: ['scheming', 'polishing his crown'] },
    { name: 'Wolf', thinks: ['lurking in the asteroids', 'sharpening his claws'] },
    { name: 'Kazuya', thinks: ['glaring silently', 'cracking his knuckles'] },
  ],
}
