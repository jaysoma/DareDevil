// Brief 21's reads on each utterance cut, from the schemes unchanged plus the harness copy's span read:
//   track   GccPhat's stream as shipped: its angle 1 after every 512-sample push (the dot settling), until the lock
//   a2      Angle2.readUtterance at the onset: its onset deg and when it recurred (at3)
//   pause   the pause read before the onset (deg, share), for the dim rule
//   slides  a half-second GccPhat read ending at every STEP from the lock on: deg, share and margin (angle-1 share
//           minus angle-2 share), weighted by the utterance's own onset pause
// usage: node run_reads.mjs utt.jsonl src/schemes   (one JSON line per cut; times in s from the onset)
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import { pathToFileURL } from 'node:url';

const [cutsPath, dir] = process.argv.slice(2);
const Gcc = await import(pathToFileURL(path.resolve(dir, 'GccPhat.mjs')).href);
const A2 = await import(pathToFileURL(path.resolve(dir, 'Angle2.mjs')).href);
const Span = await import(pathToFileURL(path.resolve(path.dirname(new URL(import.meta.url).pathname), 'GccPhatSpan.mjs')).href);
for (const m of [Gcc, A2, Span]) m.setLog(() => {});
const SR = 48000, HOP = 512, CHUNK = 512, STEP = 0.25, SPAN = Math.round(Gcc.LOCK_S * SR);
const i16 = (b64) => { const b = Buffer.from(b64, 'base64'); return new Int16Array(b.buffer, b.byteOffset, b.length / 2); };
const r3 = (v) => (v === null || v === undefined ? null : Number(v.toFixed(3)));
const margin = (q) => q.angles.length > 1 ? q.angles[0].share - q.angles[1].share : q.angles[0].share;

const rl = readline.createInterface({ input: fs.createReadStream(cutsPath), crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  const c = JSON.parse(line), L = i16(c.L), R = i16(c.R), on = c.onset_sample, base = c.baseline_m;
  const out = { id: c.id, track: [] };
  const s = Gcc.createStream(base, { readFrom: on - HOP });
  let lockT = null;
  for (let i = 0; i < L.length; i += CHUNK) {
    const o = s.push(L.subarray(i, i + CHUNK), R.subarray(i, i + CHUNK), i === 0 ? 0 : null);
    const p = o.positions[0];
    const t = (i + CHUNK - on) / SR;
    if (p) out.track.push([r3(t), p.deg]);
    if (p && p.locked) { lockT = t; out.lock = { t: r3(t), deg: p.deg, margin: r3(o.positions.length > 1 ? (p.hits - o.positions[1].hits) / 500 : p.hits / 500) }; break; }
  }
  // the span read at the lock's place must be the stream's own lock
  const self = Span.readSpan(L, R, on - HOP, on, base);
  out.span_matches_lock = !!(self && out.lock && self.deg === out.lock.deg);
  const pr = Span.readPause(L, R, on, base);
  out.pause = pr ? { deg: pr.deg, share: pr.share } : null;
  const ua = A2.readUtterance(L, R, on, base);
  out.a2 = ua ? { deg: r3(ua.onset.deg), at3: r3((ua.onset.at3 - on) / SR), edge: ua.onset.edge ?? null } : null;
  out.slides = [];
  if (lockT !== null) {
    const end = on + Math.round(c.dur_s * SR);
    for (let t = lockT + STEP; on + Math.round(t * SR) <= end + 1; t += STEP) {
      const stop = on + Math.round(t * SR), from = stop - SPAN - (2048 - HOP);   // its last frame ends at `stop`
      const q = from >= 0 ? Span.readSpan(L, R, from, on, base) : null;
      if (q) out.slides.push([r3(t), q.deg, r3(q.share), r3(margin(q))]);
    }
  }
  process.stdout.write(JSON.stringify(out) + '\n');
}
