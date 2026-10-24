// rotation_labels.mjs: what each rotation walk IS, for the orientation work (Jay, 2026-10-23: "There's ones where I rotate
// while talking, and ones where I rotate while holding a vowel. Those are important"). Writes `experiment`, `held_voice_s`
// and a `note` into DareDevil's library.json, sets walk-223157 to rotation (its consonants), and explains both fields in
// the README. Labels come from each walk's decode; held_voice_s from the sound (held_sounds.py: steady-pitch runs of
// >= 1.5 s), which is how walk-213304's held vowels show -- its decode has no words for them.
import { readFileSync, writeFileSync } from 'node:fs';
const OUT = 'C:/Projects/GithubRoot/geonar-truth';
const T = (s) => `walk-${s}`;
const EXPERIMENT = {
  talking: ['030615', '044350', '122038', '125621', '160546', '161331', '171645', '171930', '172045', '211436', '215800', '221126',
    '224302', '224459', '020305', '171542', '234455', '213304'],
  'same phrase': ['231705', '231921', '140956'],
  consonants: ['223157'],
  'walking, facing away': ['234212'],
};
const HELD = { '161331': 1.8, '171930': 4.2, '172045': 1.8, '215800': 1.6, '231705': 1.9, '231921': 1.6, '223157': 1.9 };
const NOTES = {
  '213304': 'talking between distance and turn calls; the 77 s once counted as held vowels was room rumble (held_sounds.py fixed 2026-10-24)',
  '231705': 'repeats "there\'s 6 fresh beers in the fridge" as he turns',
  '231921': 'repeats "there\'s 6 fresh beers in the fridge" as he turns',
  '140956': 'reads the same text (the Second Amendment) as he turns',
  '223157': 'says consonants as he turns; the decode garbles them ("POP-T-T-T-T", "F... F...") and "rotate clockwise" ("wind road clock")',
  '020305': 'a much smaller, carpeted room (as the decode describes it)',
  '234212': 'walks away from the phone facing away from it, then turns around to face it',
  '171542': '"I\'m talking while rotating"',
};
const ROOMS = { '234455': 'bedroom office' };
const label = {};
for (const [kind, list] of Object.entries(EXPERIMENT)) for (const s of list) label[T(s)] = kind;
const lib = JSON.parse(readFileSync(`${OUT}/library.json`, 'utf8'));
let n = 0;
for (const t of lib.tapes) {
  const s = t.name.slice(5);
  if (!label[t.name]) continue;
  t.rotation = true;
  t.experiment = label[t.name];
  t.held_voice_s = HELD[s] ?? 0;
  if (NOTES[s]) t.note = NOTES[s];
  if (ROOMS[s] && !t.room) t.room = ROOMS[s];
  n++;
}
const missing = Object.keys(label).filter((w) => !lib.tapes.some((t) => t.name === w));
lib.updated = new Date().toISOString();
writeFileSync(`${OUT}/library.json`, JSON.stringify(lib, null, 1) + '\n');
let readme = readFileSync(`${OUT}/README.md`, 'utf8');
const SECTION = `
Each rotation walk carries \`experiment\`, what Jay does as he turns: \`talking\`, \`same phrase\` (one sentence or text over
and over: "there's 6 fresh beers in the fridge", the Second Amendment), \`consonants\`, \`held vowel\`, or \`walking, facing
away\`. They are read off the decode, except held vowels: Whisper writes nothing for a sustained vowel, so those come from
the sound. \`held_voice_s\` is the seconds of voice that hold one steady pitch for 1.5 s or more (50 ms frames, the lag of
the autocorrelation peak within 8% of its median, the frames voiced against the tape's own level range); talking rarely
gets past a second or two, walk-213304 has 77 s.
`;
if (!readme.includes('`held_voice_s`')) readme = readme.replace(/(\n## Rotation walks\n[\s\S]*?instead of 157 mm\.\n)/, `$1${SECTION}`);
writeFileSync(`${OUT}/README.md`, readme);
console.log(`labelled ${n} rotation walks${missing.length ? '; NOT in library: ' + missing.join(', ') : ''}; `
  + `${lib.tapes.filter((t) => t.rotation).length} rotation of ${lib.tapes.length}; README ${readme.includes('`held_voice_s`') ? 'updated' : 'NOT updated'}`);
