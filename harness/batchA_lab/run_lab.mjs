// Brief 13's runner: feed lab cuts to GccPhat and Angle2.readUtterance UNCHANGED (or a band copy, cause 4), the way
// harness/starss23/run_schemes.mjs does -- the read starts one 512-sample step before the onset handed over, audio pushed
// in 512-sample chunks -- and record what each read knew, in the batch A record's fields.
//   gcc: angles 1-3 with shares and widths at the lock, the tie flag, and the read's track: its first draw ("43"), the
//        read standing at 100 and 250 ms after the read start, and the lock.
//   a2:  the onset (deg, edge, first_ms and at3_ms from the TRUE onset) and the second family's deg.
//   pause_deg: GccPhat's own textbook read (createStream with no pause before it, so no weighting) of the 0.5 s that ends
//        at the onset handed over: whatever was sounding before the voice.
// Nothing here feeds back into a read.
// usage: node run_lab.mjs cuts.jsonl <schemes dir> [--offset-ms N] [--nopause] [--gcc-only]
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import { pathToFileURL } from 'node:url';

const args = process.argv.slice(2);
const [cutsPath, dir] = args;
const flag = (f) => args.includes(f);
const offIdx = args.indexOf('--offset-ms');
const OFFSET = offIdx >= 0 ? Math.round(Number(args[offIdx + 1]) * 48) : 0;
const load = (f) => import(pathToFileURL(path.resolve(dir, f)).href);
const Gcc = await load('GccPhat.mjs');
const A2 = await load('Angle2.mjs');
Gcc.setLog(() => {}); A2.setLog(() => {});
const PREROLL = 512, CHUNK = 512, PAUSE_N = 24000;
const TRACK = [['100', 100], ['250', 250]];
const i16 = (b64) => { const b = Buffer.from(b64, 'base64'); return new Int16Array(b.buffer, b.byteOffset, b.length / 2); };

function gccRead(L, R, base, readFrom, startAt = 0) {
  // readFrom null: the stream starts at the first sample pushed and has no pause to weigh against
  const s = Gcc.createStream(base, readFrom === null ? { reread: false } : { readFrom, reread: false });
  const track = { '43': null, '100': null, '250': null, lock: null };
  const t0 = readFrom === null ? startAt : readFrom;
  let o = null;
  for (let i = startAt; i < L.length; i += CHUNK) {
    o = s.push(L.subarray(i, i + CHUNK), R.subarray(i, i + CHUNK), i === startAt ? startAt : null);
    const p = o.positions[0], ms = (Math.min(i + CHUNK, L.length) - t0) / 48;
    if (p && track['43'] === null) track['43'] = p.deg;
    for (const [k, t] of TRACK) if (track[k] === null && ms >= t && p) track[k] = p.deg;
    if (p && p.locked) { track.lock = p.deg; break; }
  }
  const ps = o ? o.positions : [];
  if (!ps.length) return { track, angles: [] };
  return { track, angles: ps.map((p) => p.deg), shares: ps.map((p) => Number((p.hits / 500).toFixed(3))),
           widths: ps.map((p) => p.width), tie: !!(ps[1] && ps[1].tie), locked: !!ps[0].locked };
}

const rl = readline.createInterface({ input: fs.createReadStream(cutsPath), crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  const c = JSON.parse(line), L = i16(c.L), R = i16(c.R), base = c.baseline_m, on = c.onset_sample + OFFSET;
  const out = { id: c.id };
  try {
    const g = flag('--nopause') ? gccRead(L, R, base, null, on - PREROLL) : gccRead(L, R, base, on - PREROLL);
    out.gcc = { angles: g.angles, shares: g.shares ?? [], widths: g.widths ?? [], tie: g.tie ?? false, track: g.track };
  } catch (e) { out.gcc_err = String(e); }
  try {
    const p = gccRead(L.subarray(0, on), R.subarray(0, on), base, null, on - NFFT_PAUSE());
    out.pause_deg = p.angles.length ? p.angles[0] : null;
    out.pause_share = p.shares && p.shares.length ? p.shares[0] : null;
  } catch (e) { out.pause_err = String(e); }
  if (!flag('--gcc-only')) {
    try {
      const r = A2.readUtterance(L, R, on, base);
      out.a2 = r ? { deg: r.onset.deg, edge: r.onset.edge ?? null, first_ms: (r.onset.first - c.onset_sample) / 48,
                     at3_ms: (r.onset.at3 - c.onset_sample) / 48, second_deg: r.refl ? r.refl.deg : null } : null;
    } catch (e) { out.a2_err = String(e); }
  }
  process.stdout.write(JSON.stringify(out) + '\n');
}
// the pause read's span: 47 frames starting in 0.5 s, so the last ends at the onset
function NFFT_PAUSE() { return PAUSE_N + Gcc.NFFT; }
