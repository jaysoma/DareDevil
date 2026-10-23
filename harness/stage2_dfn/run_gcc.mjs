// Brief 16: GccPhat on one recording's cuts, in the variants a DFN pass makes possible, fed as the Conductor feeds it
// (read start one 512-sample step before the onset, 512-sample pushes), as harness/batchA_lab/run_lab.mjs does.
//   raw   the shipped scheme (src/schemes/GccPhat.mjs) on the raw pair
//   dfn   the shipped scheme on the DFN pair (Jay's shared operator: one mask and deep filter on both channels)
//   mix   harness/fixes/GccPhatMask.mjs on the raw pair, votes weighted by the mask DFN computed from the L+R mixdown
//   cap   the same, the mask DFN computed from one capsule (L) alone
// Each read: angles 1-3, shares, widths, tie, and the track (first draw "43", 100 ms, 250 ms, lock), as batch A records.
// usage: node run_gcc.mjs cuts.jsonl raw,dfn,mix,cap
import fs from 'node:fs';
import readline from 'node:readline';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const Gcc = await import(path.resolve(here, '../../src/schemes/GccPhat.mjs'));
const Gm = await import(path.resolve(here, '../fixes/GccPhatMask.mjs'));
Gcc.setLog(() => {}); Gm.setLog(() => {});
const [cutsPath, which] = process.argv.slice(2);
const VARIANTS = which.split(',');
const PREROLL = 512, CHUNK = 512;
const i16 = (b64) => { const b = Buffer.from(b64, 'base64'); return new Int16Array(b.buffer, b.byteOffset, b.length / 2); };

function read(mod, L, R, base, on, voteMask = null) {
  const s = mod.createStream(base, { readFrom: on - PREROLL, ...(voteMask ? { voteMask } : {}) });
  const track = { '43': null, '100': null, '250': null, lock: null };
  let o = null;
  for (let i = 0; i < L.length; i += CHUNK) {
    o = s.push(L.subarray(i, i + CHUNK), R.subarray(i, i + CHUNK), i === 0 ? 0 : null);
    const p = o.positions[0], ms = (Math.min(i + CHUNK, L.length) - (on - PREROLL)) / 48;
    if (p && track['43'] === null) track['43'] = p.deg;
    if (p && track['100'] === null && ms >= 100) track['100'] = p.deg;
    if (p && track['250'] === null && ms >= 250) track['250'] = p.deg;
    if (p && p.locked) { track.lock = p.deg; break; }
  }
  const ps = o ? o.positions : [];
  if (!ps.length) return null;
  return { angles: ps.map((p) => p.deg), shares: ps.map((p) => Number((p.hits / 500).toFixed(3))),
           widths: ps.map((p) => p.width), tie: !!(ps[1] && ps[1].tie), track };
}

const rl = readline.createInterface({ input: fs.createReadStream(cutsPath), crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  const c = JSON.parse(line), on = c.onset_sample, base = c.baseline_m, out = { id: c.id };
  for (const v of VARIANTS) {
    try {
      if (v === 'raw') out[v] = read(Gcc, i16(c.L), i16(c.R), base, on);
      else if (v === 'dfn') out[v] = read(Gcc, i16(c.DL), i16(c.DR), base, on);
      else if (v === 'mix' || v === 'cap') out[v] = read(Gm, i16(c.L), i16(c.R), base, on, Float64Array.from(c[`w${v}`]));
    } catch (e) { out[`${v}_err`] = String(e); }
  }
  process.stdout.write(JSON.stringify(out) + '\n');
}
