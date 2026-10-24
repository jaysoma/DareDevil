// add_rotation.mjs: rotation walks into DareDevil (Jay 2026-10-23: "Need rotation walk data checked into GitHub with all
// the same data as the ones that are in the cloud now"). The same files per tape as build_dataset.mjs wrote for the first
// 29 -- transcript.json and audio-input.json here, odas.json from odas_rot.mjs -- added to library.json and poses.json
// without rebuilding either. None of these walks has a truth file, so each pose is null and says why.
//   node add_rotation.mjs walk-030615 walk-044350 ...
import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
const CAP = 'C:/Projects/GithubRoot/Dictate/captures/geonar', OUT = 'C:/Projects/GithubRoot/geonar-truth';
const TAPES = process.argv.slice(2);
const J = (p) => JSON.parse(readFileSync(p, 'utf8'));
const put = (p, o) => { mkdirSync(p.slice(0, p.lastIndexOf('/')), { recursive: true }); writeFileSync(p, JSON.stringify(o, null, 1) + '\n'); };
const MON = { Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6, Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12 };
const idx = J(`${CAP}/tape_index.json`), IDX = Array.isArray(idx) ? idx : (idx.tapes || Object.values(idx));
const pad = (n) => String(n).padStart(2, '0');
// RECORDED, as build_dataset.mjs: the day from tape_index, the time of day from the walk's own name, stepped back a day
// when tape_index stamped the import day. A walk tape_index never saw takes its day from its own earliest file.
function recordedOf(w) {
  const e = IDX.find((x) => x && x.name === w) || {}, m = String(e.date_str || '').match(/([A-Z][a-z]{2})\w*\s+(\d+)/);
  const files = [...(existsSync(`${CAP}/${w}`) ? readdirSync(`${CAP}/${w}`).map((n) => `${CAP}/${w}/${n}`) : []),
    `${CAP}/tapes/${w}.raw`, `${CAP}/tapes/${w}.wav`].filter(existsSync);
  const earliest = Math.min(...files.map((f) => statSync(f).mtimeMs));
  const hh = w.slice(5, 7), mm = w.slice(7, 9), ss = w.slice(9, 11);
  let day, note = null;
  if (m) day = `2026-${pad(MON[m[1]])}-${pad(+m[2])}`;
  else {
    day = new Date(earliest - 5 * 3600e3).toISOString().slice(0, 10);
    note = `${e.name ? 'no date in tape_index' : 'not in tape_index'}: the day is its tape file's`;
  }
  let ms = Date.parse(`${day}T${hh}:${mm}:${ss}-05:00`);
  if (m && ms > earliest + 120e3) { ms -= 86400e3; note = 'tape_index date is the import day; stepped back one day'; }
  return { iso: `${new Date(ms - 5 * 3600e3).toISOString().slice(0, 19)}-05:00`, note };
}
function audioOf(w) {
  const raw = `${CAP}/tapes/${w}.raw`, wav = `${CAP}/tapes/${w}.wav`, f = existsSync(raw) ? raw : wav, b = readFileSync(f);
  const sha256 = createHash('sha256').update(b).digest('hex');
  if (f === raw) return { file: `Dictate/captures/geonar/tapes/${w}.raw`, format: 'raw PCM, no header: signed 16-bit little-endian, 2 channels interleaved',
    sample_rate: 48000, channels: 2, bits: 16, frames: b.length / 4, duration_s: +(b.length / 4 / 48000).toFixed(3), bytes: b.length, sha256 };
  let p = 12, fmt = null, data = null;
  while (p + 8 <= b.length) { const id = b.toString('ascii', p, p + 4), n = b.readUInt32LE(p + 4);
    if (id === 'fmt ') fmt = { ch: b.readUInt16LE(p + 10), sr: b.readUInt32LE(p + 12), bits: b.readUInt16LE(p + 22) };
    if (id === 'data') { data = n; break; } p += 8 + n + (n & 1); }
  const fr = data / (fmt.ch * fmt.bits / 8);
  return { file: `Dictate/captures/geonar/tapes/${w}.wav`, format: `WAV (RIFF), signed ${fmt.bits}-bit little-endian, ${fmt.ch} channels interleaved`,
    sample_rate: fmt.sr, channels: fmt.ch, bits: fmt.bits, frames: fr, duration_s: +(fr / fmt.sr).toFixed(3), bytes: b.length, sha256 };
}
// A folded walk's pair is the chord 157 sin(fold / 2), as the Conductor and odas_rot.mjs work it out.
function foldOf(w) {
  const f = `${CAP}/${w}/fold.json`;
  if (!existsSync(f)) return null;
  const deg = Number(J(f).fold_deg ?? 180);
  return { deg, mm: Math.round(1570 * Math.sin((deg * Math.PI) / 360)) / 10 };
}
const lib = J(`${OUT}/library.json`), poses = J(`${OUT}/truth_inputs/poses.json`);
for (const w of TAPES) {
  const e = IDX.find((x) => x && x.name === w) || {}, fold = foldOf(w);
  const rec = recordedOf(w), au = audioOf(w), ws = J(`${CAP}/${w}-whisper.json`);
  put(`${OUT}/tapes/${w}/transcript.json`, { name: w, source: `Dictate/captures/geonar/${w}-whisper.json (geonar/whisper_tape.py) -- the decode the Truth page shows`,
    model: ws.model, language: ws.language, duration_s: ws.duration, segments: (ws.segments || []).map((s) => ({ t0: s.t0 ?? s.start, t1: s.t1 ?? s.end, text: s.text })) });
  put(`${OUT}/tapes/${w}/audio-input.json`, { name: w, recorded: rec.iso, ...au,
    phone: fold ? `Samsung Galaxy Z Flip4, folded at ${fold.deg} deg (its fold.json)` : 'Samsung Galaxy Z Flip4, unfolded flat',
    capsules: fold ? `top and bottom microphones, ${fold.mm} mm apart (the 157 mm pair folded to its chord; the pair ODAS reads)`
      : 'top and bottom microphones, 157 mm apart (the pair ODAS reads)',
    channel_order: 'which capsule is the left channel varies by tape (top mostly left) -- see truth_inputs/poses.json mirror',
    note: 'metadata only; the audio stays on the recording machine at the path in file' });
  poses.poses[w] = { phone: null, phone_h_m: null, mirror: null,
    status: 'no pose: this walk has no truth file, so the phone\'s place, facing and capsule order were never marked'
      + (e.room === 'bedroom office' ? ' (recorded in the bedroom office, which is not on this map)' : ''),
    source_file: null };
  lib.tapes = lib.tapes.filter((t) => t.name !== w);
  lib.tapes.push({ name: w, recorded: rec.iso, ...(rec.note ? { recorded_note: rec.note } : {}), duration_s: au.duration_s, rotation: true,
    ...(e.room ? { room: e.room } : {}), ...(fold ? { folded_deg: fold.deg } : {}), decode_model: ws.model,
    files: ['transcript.json', 'odas.json', 'audio-input.json'].map((n) => `tapes/${w}/${n}`) });
  console.log(`${w}: ${rec.iso}${rec.note ? ` (${rec.note})` : ''}, ${au.duration_s} s${e.room ? ', ' + e.room : ''}${fold ? `, folded ${fold.deg} deg` : ''}`);
}
lib.tapes.sort((a, b) => a.name.localeCompare(b.name));
lib.updated = new Date().toISOString();
put(`${OUT}/library.json`, lib);
put(`${OUT}/truth_inputs/poses.json`, poses);
const readme = readFileSync(`${OUT}/README.md`, 'utf8');
if (!readme.includes('## Rotation walks')) writeFileSync(`${OUT}/README.md`, readme.trimEnd() + `

## Rotation walks

Every walk whose decode has Jay rotating (rotate, clockwise, 90, facing away), found by grepping the transcripts on
2026-10-23, is \`rotation: true\` in library.json. The ones added that day have no truth files, so their poses are null
and say so; \`room\` is the room tape_index read off the decode, where it caught one (the bedroom office is not on this
map). A folded walk (\`folded_deg\`) had its ODAS run on the folded chord instead of 157 mm.
`);
console.log(`library: ${lib.tapes.length} tapes, ${lib.tapes.filter((t) => t.rotation).length} rotation`);
