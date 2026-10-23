// Batch A's per-read record, from the schemes as they stand in src/schemes/, unchanged. Nothing here feeds back into
// an angle: the schemes run exactly as harness/starss23/run_schemes.mjs runs them (the read starts one 512-sample step
// before the onset, audio pushed in 512-sample chunks), and everything else is read alongside.
//
//   gcc.angles/shares/widths/tie   GccPhat's positions at the lock (hits = share x 500, so share = hits / 500)
//   gcc.track                      GccPhat's angle 1 as the sum grew: the first draw (43 ms of audio from the read
//                                  start), then once the sum holds 100 ms and 250 ms, then the lock
//   gcc.votes                      the vote total after pause weighting: GccPhat's own sums rebuilt here (same frames,
//                                  same weights) and handed to its exported readSum; that read must equal the stream's
//   pause_deg                      readSum over the 0.5 s before the onset, unweighted: what was sounding before the voice
//   a2                             Angle2.readUtterance: the onset's deg, edge, first and at3 (ms from the onset) and the
//                                  second family's deg
// usage: node record_reads.mjs cuts.jsonl <folder holding GccPhat.mjs and Angle2.mjs>   (one JSON line per cut, by id)
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import { pathToFileURL } from 'node:url';

const [cutsPath, dir] = process.argv.slice(2);
const load = (f) => import(pathToFileURL(path.resolve(dir, f)).href);
const Gcc = await load('GccPhat.mjs');
const A2 = await load('Angle2.mjs');
const quiet = () => {};
Gcc.setLog(quiet); A2.setLog(quiet);                     // their zero/no-peak console logs: not part of the record
const PREROLL = 512, CHUNK = 512, SR = 48000, C = 343, PAUSE_S = 0.5;
const { NFFT, HOP, LO_HZ, HI_HZ, TAUS, PAUSE_MS, LOCK_S } = Gcc;
const i16 = (b64) => { const b = Buffer.from(b64, 'base64'); return new Int16Array(b.buffer, b.byteOffset, b.length / 2); };
const r2 = (v) => (v === null || v === undefined ? null : Number(v.toFixed(2)));

// GccPhat's sums, rebuilt with its own constants (steerOf and addFrame are not exported)
const K0 = Math.ceil(LO_HZ * NFFT / SR), K1 = Math.floor(HI_HZ * NFFT / SR), NB = K1 - K0 + 1;
const HANN = Float64Array.from({ length: NFFT }, (_, i) => 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (NFFT - 1)));
const BITS = Math.round(Math.log2(NFFT)), REV = new Uint32Array(NFFT), FC = new Float64Array(NFFT / 2), FS = new Float64Array(NFFT / 2);
for (let i = 0; i < NFFT; i++) { let r = 0; for (let b = 0; b < BITS; b++) r |= ((i >> b) & 1) << (BITS - 1 - b); REV[i] = r; }
for (let k = 0; k < NFFT / 2; k++) { FC[k] = Math.cos(2 * Math.PI * k / NFFT); FS[k] = -Math.sin(2 * Math.PI * k / NFFT); }
function fft(re, im) {
  for (let i = 0; i < NFFT; i++) { const j = REV[i]; if (j > i) { let t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; } }
  for (let size = 2; size <= NFFT; size <<= 1) {
    const half = size >> 1, step = NFFT / size;
    for (let s = 0; s < NFFT; s += size) for (let k = 0; k < half; k++) {
      const wr = FC[k * step], wi = FS[k * step], a = s + k, b = a + half;
      const xr = re[b] * wr - im[b] * wi, xi = re[b] * wi + im[b] * wr;
      re[b] = re[a] - xr; im[b] = im[a] - xi; re[a] += xr; im[a] += xi;
    }
  }
}
const STEERS = new Map();
function steerOf(d) {
  if (STEERS.has(d)) return STEERS.get(d);
  const tmax = d / C, J = TAUS - 1, cos = new Float64Array(TAUS * NB), sin = new Float64Array(TAUS * NB);
  const tau = new Float64Array(TAUS), deg = new Float64Array(TAUS);
  for (let j = 0; j <= J; j++) {
    tau[j] = -tmax + 2 * tmax * j / J;
    deg[j] = Math.asin(Math.max(-1, Math.min(1, -tau[j] * C / d))) * 180 / Math.PI;
    for (let b = 0; b < NB; b++) { const a = 2 * Math.PI * tau[j] * (K0 + b) * SR / NFFT; cos[j * NB + b] = Math.cos(a); sin[j * NB + b] = Math.sin(a); }
  }
  const s = { cos, sin, tau, deg };
  STEERS.set(d, s);
  return s;
}
const lr = new Float64Array(NFFT), li = new Float64Array(NFFT), rr = new Float64Array(NFFT), ri = new Float64Array(NFFT);
function addFrame(L, R, s, re, im, pw = null) {
  const scale = 1 / 32768;
  for (let i = 0; i < NFFT; i++) { lr[i] = L[s + i] * scale * HANN[i]; li[i] = 0; rr[i] = R[s + i] * scale * HANN[i]; ri[i] = 0; }
  fft(lr, li); fft(rr, ri);
  for (let b = 0; b < NB; b++) {
    const k = K0 + b;
    re[b] += lr[k] * rr[k] + li[k] * ri[k]; im[b] += li[k] * rr[k] - lr[k] * ri[k];
    if (pw) pw[b] += (lr[k] * lr[k] + li[k] * li[k] + rr[k] * rr[k] + ri[k] * ri[k]) / 2;
  }
}
// the lock as createStream builds it: frames from the read start every HOP that start inside LOCK_S, weighted by the
// PAUSE_MS before the onset (the read start + one step)
function gccLock(L, R, from, st) {
  const need = Math.round(LOCK_S * SR), pauseN = Math.round(PAUSE_MS * SR / 1000);
  const re = new Float64Array(NB), im = new Float64Array(NB), pw = new Float64Array(NB);
  let frames = 0;
  for (let s = from; s - from < need && s + NFFT <= L.length; s += HOP) { addFrame(L, R, s, re, im, pw); frames++; }
  let wt = null;
  const a = from + HOP - pauseN - NFFT / 2, b = from + HOP + NFFT / 2;
  if (a >= 0) {
    const nre = new Float64Array(NB), nim = new Float64Array(NB), npw = new Float64Array(NB);
    let k = 0;
    for (let s0 = a; s0 + NFFT <= b; s0 += HOP) { addFrame(L, R, s0, nre, nim, npw); k++; }
    wt = Float64Array.from(npw, (n, i) => Math.max(0, Math.min(1, 1 - (n / Math.max(k, 1)) / Math.max(pw[i] / frames, 1e-30))));
  }
  return { read: Gcc.readSum(re, im, st, wt), votes: wt ? wt.reduce((x, v) => x + v, 0) : NB };
}
// what was sounding before the voice: the unweighted sum of the frames inside the PAUSE_S before the onset
function pauseRead(L, R, on, st) {
  const re = new Float64Array(NB), im = new Float64Array(NB);
  let n = 0;
  for (let s = on - Math.round(PAUSE_S * SR); s >= 0 && s + NFFT <= on; s += HOP) { addFrame(L, R, s, re, im); n++; }
  return n ? Gcc.readSum(re, im, st, null) : null;
}

const rl = readline.createInterface({ input: fs.createReadStream(cutsPath), crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  const c = JSON.parse(line), L = i16(c.L), R = i16(c.R), on = c.onset_sample, base = c.baseline_m;
  const out = { id: c.id };
  try {
    const s = Gcc.createStream(base, { readFrom: on - PREROLL });
    const track = { 43: null, 100: null, 250: null, lock: null };
    let o = null;
    for (let i = 0; i < L.length; i += CHUNK) {
      o = s.push(L.subarray(i, i + CHUNK), R.subarray(i, i + CHUNK), i === 0 ? 0 : null);
      const p = o.positions[0];
      if (!p) continue;
      const ms = ((p.frames - 1) * HOP + NFFT) / 48;                // audio the sum holds, from the read start
      if (track[43] === null) track[43] = p.deg;
      if (track[100] === null && ms >= 100) track[100] = p.deg;
      if (track[250] === null && ms >= 250) track[250] = p.deg;
      if (p.locked) { track.lock = p.deg; break; }
    }
    const ps = o ? o.positions : [];
    const st = steerOf(base), rep = gccLock(L, R, on - PREROLL, st);
    const agree = !!rep.read && ps.length > 0 && rep.read.deg === ps[0].deg;
    out.gcc = ps.length ? {
      angles: ps.map((p) => p.deg), shares: ps.map((p) => Number((p.hits / 500).toFixed(3))), widths: ps.map((p) => p.width),
      tie: ps.some((p) => p.tie === true), votes: Number(rep.votes.toFixed(2)), track } : null;
    out.gcc_replica_agrees = agree;
    const pr = pauseRead(L, R, on, st);
    out.pause_deg = pr ? pr.deg : null;
  } catch (e) { out.gcc_err = String(e); }
  try {
    const r = A2.readUtterance(L, R, on, base);
    out.a2 = r ? { deg: r2(r.onset.deg), edge: r.onset.edge ?? null, first_ms: r2((r.onset.first - on) / 48),
                   at3_ms: r2((r.onset.at3 - on) / 48), second_deg: r.refl ? r2(r.refl.deg) : null } : null;
  } catch (e) { out.a2_err = String(e); }
  process.stdout.write(JSON.stringify(out) + '\n');
}
