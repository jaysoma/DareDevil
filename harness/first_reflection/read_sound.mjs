// Angle2.readSound on cuts (dEchorate or LOCATA format), unchanged, with s at the sound's first frame.
// The sound is found by Angle2's own stream, as the math host would run it: the cut pushed in 512-sample chunks from
// sample 0, the read starting one step before the onset; its first sound (out.sounds[0]) is the frame where the
// 1.1-8 kHz level first clears SOUND_DB over its floor. readSound is then called on that frame for every field, which
// must match what the stream read there.
// usage: node read_sound.mjs cuts.jsonl <folder holding Angle2.mjs>   (one JSON line per cut, by id)
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import { pathToFileURL } from 'node:url';

const [cutsPath, dir] = process.argv.slice(2);
const A2 = await import(pathToFileURL(path.resolve(dir, 'Angle2.mjs')).href);
A2.setLog(() => {});
const PREROLL = 512, CHUNK = 512;
const i16 = (b64) => { const b = Buffer.from(b64, 'base64'); return new Int16Array(b.buffer, b.byteOffset, b.length / 2); };
const r = (v, d = 3) => (v === null || v === undefined ? null : Number(v.toFixed(d)));

const rl = readline.createInterface({ input: fs.createReadStream(cutsPath), crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  const c = JSON.parse(line), L = i16(c.L), R = i16(c.R), on = c.onset_sample, base = c.baseline_m;
  const out = { id: c.id };
  try {
    const st = A2.createStream(base, { readFrom: on - PREROLL });
    let o = null;
    for (let i = 0; i < L.length; i += CHUNK) o = st.push(L.subarray(i, i + CHUNK), R.subarray(i, i + CHUNK), i === 0 ? 0 : null);
    const first = o.sounds[0];
    if (!first) { out.sound = null; process.stdout.write(JSON.stringify(out) + '\n'); continue; }
    const s = first.at, q = A2.readSound(L, R, s, base);
    out.sound = { s_ms: r((s - on) / 48, 2), sounds: o.sounds.length };
    if (q) {
      out.decided = q.decided;
      out.onset = { deg: r(q.onset.deg, 2), tau_ms: r(q.onset.tau_ms, 4), share: r(q.onset.share) };
      out.refl = q.refl ? { deg: r(q.refl.deg, 2), tau_ms: r(q.refl.tau_ms, 4), fit: r(q.refl.fit), gain: r(q.refl.gain) } : null;
      out.gap_ms = r(q.gap_ms, 4);
      out.other_deg = q.other ? r(q.other.deg, 2) : null;
      out.why = q.why ?? null;
      out.matches_stream = first.decided === q.decided && first.onset === r(q.onset.deg, 1);
    } else out.decided = null;
  } catch (e) { out.err = String(e); }
  process.stdout.write(JSON.stringify(out) + '\n');
}
