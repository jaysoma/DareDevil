// Brief H's CdrRange test (2026-10-24): fixture.json (make_fixture.py) through src/schemes/CdrRange.js, read the way
// MathPass reads it (regress.mjs). Exits non-zero on any failure.
//
//     node harness/rotation/inapp/test_cdrrange.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadScheme, read } from './regress.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const fx = JSON.parse(fs.readFileSync(path.join(here, 'fixture.json'), 'utf8'));
const scheme = path.join(here, '../../../src/schemes/CdrRange.js');
let failed = 0;
const check = (ok, what) => { if (!ok) failed++; console.log(`${ok ? 'ok  ' : 'FAIL'} ${what}`); };
const near = (a, b, tol) => a !== null && b !== null && Math.abs(a - b) <= tol;
const byOnset = (utts) => new Map(utts.filter((u) => u.S !== null).map((u) => [Math.round(u.onset_s * 1000) / 1000, u]));

// 1. The fixture as the Conductor handed it.
const got = byOnset(read(loadScheme(scheme), fx.stream));
for (const e of fx.expect) {
  const u = got.get(e.onset_s), at = `${e.onset_s} s`;
  if (!u) { check(false, `${at}: drawn`); continue; }
  check(near(u.S, e.S, 0.005), `${at}: the 0.5 s statistic ${u.S.toFixed(4)} dB, Python ${e.S}`);
  check(u.facing === e.facing, `${at}: facing ${u.facing}, expected ${e.facing}`);
  if (e.facing) check(near(u.contrast, e.contrast, 0.01), `${at}: contrast ${u.contrast.toFixed(3)} dB, Python ${e.contrast}`);
  check(near(u.corr, e.corr, 0.01), `${at}: correction ${u.corr.toFixed(4)} dB, expected ${e.corr}`);
  check(u.draws.length === e.draws, `${at}: the dot moved ${u.draws.length} time(s), expected ${e.draws}`);
  const first = u.draws[0], last = u.draws[u.draws.length - 1];
  check(near(first[0] - e.onset_s, (42 * 512 + 2048) / 48000, 0.002), `${at}: first draw on hop 42 (${(first[0] - e.onset_s).toFixed(4)} s after the onset)`);
  check(near(first[1], e.u_at_0_5, 2e-3 * e.u_at_0_5), `${at}: u at 0.5 s ${first[1].toFixed(5)}, expected ${e.u_at_0_5}`);
  check(near(last[1], e.u_final, 2e-3 * e.u_final), `${at}: u held ${last[1].toFixed(5)}, expected ${e.u_final}`);
  if (e.draws === 2) check(near(last[0] - e.onset_s, (183 * 512 + 2048) / 48000, 0.002), `${at}: the correction on hop 183 (${(last[0] - e.onset_s).toFixed(4)} s)`);
}

// 2. The turned utterance cut before its 2 s frame: no call, no correction, drawn once.
const turned = fx.expect.find((e) => e.facing === 'turned');
const cut = fx.stream.map((it) => (it.to === 'range'
  ? { ...it, frames: it.frames.filter((f) => !(f.t >= turned.onset_s && f.t - turned.onset_s > 1.99)) } : it));
const c = byOnset(read(loadScheme(scheme), cut)).get(turned.onset_s);
check(c && c.facing === null && c.corr === 0 && c.draws.length === 1, `${turned.onset_s} s cut at 1.99 s: facing ${c && c.facing}, drawn ${c && c.draws.length} time(s)`);

// 3. A v13 stream (six values, frames to 0.5 s): the same range, and never a call.
const v13 = fx.stream.map((it) => (it.to === 'range'
  ? { ...it, frames: it.frames.filter((f) => f.t - (fx.expect.find((e) => f.t >= e.onset_s && f.t < e.onset_s + 3) || { onset_s: -9 }).onset_s <= 0.5).map((f) => ({ ...f, cdrf: f.cdrf.slice(0, 6) })) } : it));
const g = byOnset(read(loadScheme(scheme), v13));
for (const e of fx.expect) {
  const u = g.get(e.onset_s);
  check(u && near(u.S, e.S, 0.005) && u.facing === null && u.draws.length === 1, `${e.onset_s} s on a v13 stream: same statistic, no call, drawn once`);
}

console.log(failed ? `${failed} failed` : 'all passed');
process.exit(failed ? 1 : 0);
