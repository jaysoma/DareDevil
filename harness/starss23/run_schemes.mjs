// Feed STARSS23 cuts to Jay's bearing schemes, unchanged, the way the Conductor does: the read starts one
// 512-sample step before the onset, audio pushed in 512-sample chunks.
// usage: node run_schemes.mjs cuts.jsonl <folder holding GccPhat.mjs and Angle2.mjs>
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import { pathToFileURL } from 'node:url';

const [cutsPath, dir] = process.argv.slice(2);
const load = (f) => import(pathToFileURL(path.resolve(dir, f)).href);
const Gcc = await load('GccPhat.mjs');
const A2 = await load('Angle2.mjs');
const PREROLL = 512, CHUNK = 512;
const i16 = (b64) => { const b = Buffer.from(b64, 'base64'); return new Int16Array(b.buffer, b.byteOffset, b.length / 2); };

const rl = readline.createInterface({ input: fs.createReadStream(cutsPath), crlfDelay: Infinity });
let k = 0;
for await (const line of rl) {
  if (!line.trim()) continue;
  const c = JSON.parse(line), L = i16(c.L), R = i16(c.R), on = c.onset_sample, base = c.baseline_m;
  const out = { idx: k++, file: c.file, onset_s: c.onset_s };
  // GccPhat: textbook sum over the first half second, its three angles at the lock
  try {
    const s = Gcc.createStream(base, { readFrom: on - PREROLL });
    let o = null;
    for (let i = 0; i < L.length; i += CHUNK) o = s.push(L.subarray(i, i + CHUNK), R.subarray(i, i + CHUNK), i === 0 ? 0 : null);
    out.gcc = o && o.positions.length ? o.positions.map((p) => p.deg) : null;
  } catch (e) { out.gcc_err = String(e); }
  // Angle2.readUtterance: the first direction to recur, and the next (onset + first reflection)
  try {
    const r = A2.readUtterance(L, R, on, base);
    out.a2 = r ? [r.onset.deg, r.refl ? r.refl.deg : null] : null;
  } catch (e) { out.a2_err = String(e); }
  process.stdout.write(JSON.stringify(out) + '\n');
}
