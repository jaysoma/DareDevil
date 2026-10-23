// Batch A runner: both schemes, unchanged, fed the way the Conductor feeds them (the read starts one 512-sample step
// before the onset, audio pushed in 512-sample chunks, as harness/starss23/run_schemes.mjs), plus what each read knew
// at the time. Nothing here feeds back into an angle.
//
// Per read, in the shared batch A format (cloud_sessions.md):
//   gcc:  angles 1-3 with share and width, the tie flag, the vote total after pause weighting, and the read at the
//         first draw (43 ms of audio from the read start), at 100 ms, at 250 ms and at the lock;
//   a2:   readUtterance's onset (deg, edge, first and at3 in ms from the onset) and its second family;
//   pause_deg: GccPhat's readSum of the 0.5 s before the onset, unweighted;
//   snr_db: voice over pause in 300-1100 Hz, 1.1-3 kHz, 3-8 kHz (the lock's frames against the pause's frames);
//   voice_bands (extra): each third-octave band's share of the voice's power over the pause, for the aliasing class.
// The vote total, pause read and band levels come from a harness copy of GccPhat's sum (same frames, window, scale,
// steering and pause weighting), checked against the stream on every read: gcc.replica_ok says the copy's lock read
// equals the stream's.
// usage: node runner.mjs <schemes dir> < cuts.jsonl > raw.jsonl     (cuts from cut_all.py or sphere_grid.py)
import path from 'node:path';
import readline from 'node:readline';
import { pathToFileURL } from 'node:url';

const dir = process.argv[2];
const load = (f) => import(pathToFileURL(path.resolve(dir, f)).href);
const Gcc = await load('GccPhat.mjs');
const A2 = await load('Angle2.mjs');
let noPeak = 0, a2Zero = 0;
Gcc.setLog((tag) => { if (tag.includes('no peak')) noPeak++; });   // keep stdout and stderr clean; count flat scans
if (A2.setLog) A2.setLog(() => { a2Zero++; });
const SR = 48000, C = 343, PREROLL = 512, CHUNK = 512;
const { NFFT, HOP, LO_HZ, HI_HZ, TAUS, PAUSE_MS, LOCK_S } = Gcc;
const K0 = Math.ceil(LO_HZ * NFFT / SR), K1 = Math.floor(HI_HZ * NFFT / SR), NB = K1 - K0 + 1;
const HANN = Float64Array.from({ length: NFFT }, (_, i) => 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (NFFT - 1)));
const BANDS = { mf: [300, 1100], hf1: [1100, 3000], hf2: [3000, 8000] };
// third-octave bands 315 Hz-8 kHz, for the aliasing test: which frequencies carry the voice (over the pause)
const THIRDS = [315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000];
const i16 = (b64) => { const b = Buffer.from(b64, 'base64'); return new Int16Array(b.buffer, b.byteOffset, b.length / 2); };
const r2 = (v) => (v === null || v === undefined ? null : Math.round(v * 100) / 100);

// GccPhat's steering, built as steerOf builds it
const STEERS = new Map();
function steerOf(d) {
  let s = STEERS.get(d);
  if (s) return s;
  const tmax = d / C, J = TAUS - 1, cos = new Float64Array(TAUS * NB), sin = new Float64Array(TAUS * NB), tau = new Float64Array(TAUS), deg = new Float64Array(TAUS);
  for (let j = 0; j <= J; j++) {
    tau[j] = -tmax + 2 * tmax * j / J;
    deg[j] = Math.asin(Math.max(-1, Math.min(1, -tau[j] * C / d))) * 180 / Math.PI;
    for (let b = 0; b < NB; b++) { const a = 2 * Math.PI * tau[j] * (K0 + b) * SR / NFFT; cos[j * NB + b] = Math.cos(a); sin[j * NB + b] = Math.sin(a); }
  }
  STEERS.set(d, (s = { cos, sin, tau, deg }));
  return s;
}
let T = null;
function fft(re, im) {
  const N = re.length;
  if (!T) {
    const bits = Math.round(Math.log2(N)), rev = new Uint32Array(N), cos = new Float64Array(N / 2), sin = new Float64Array(N / 2);
    for (let i = 0; i < N; i++) { let r = 0; for (let b = 0; b < bits; b++) r |= ((i >> b) & 1) << (bits - 1 - b); rev[i] = r; }
    for (let k = 0; k < N / 2; k++) { cos[k] = Math.cos(2 * Math.PI * k / N); sin[k] = -Math.sin(2 * Math.PI * k / N); }
    T = { rev, cos, sin };
  }
  for (let i = 0; i < N; i++) { const j = T.rev[i]; if (j > i) { let t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; } }
  for (let size = 2; size <= N; size <<= 1) {
    const half = size >> 1, step = N / size;
    for (let s = 0; s < N; s += size) for (let k = 0; k < half; k++) {
      const wr = T.cos[k * step], wi = T.sin[k * step], a = s + k, b = a + half;
      const xr = re[b] * wr - im[b] * wi, xi = re[b] * wi + im[b] * wr;
      re[b] = re[a] - xr; im[b] = im[a] - xi; re[a] += xr; im[a] += xi;
    }
  }
}
// frames [s, s + NFFT) for s = a, a + HOP, ... while s + NFFT <= b: summed cross-spectrum in GccPhat's band, mean power
// per frame (GccPhat's band), and the full-spectrum power per bin (for the band levels)
function sumFrames(L, R, a, b) {
  const re = new Float64Array(NB), im = new Float64Array(NB), pw = new Float64Array(NB), full = new Float64Array(NFFT / 2 + 1);
  const lr = new Float64Array(NFFT), li = new Float64Array(NFFT), rr = new Float64Array(NFFT), ri = new Float64Array(NFFT), sc = 1 / 32768;
  let k = 0;
  for (let s = a; s + NFFT <= b; s += HOP, k++) {
    for (let i = 0; i < NFFT; i++) { lr[i] = L[s + i] * sc * HANN[i]; li[i] = 0; rr[i] = R[s + i] * sc * HANN[i]; ri[i] = 0; }
    fft(lr, li); fft(rr, ri);
    for (let q = 0; q <= NFFT / 2; q++) full[q] += (lr[q] * lr[q] + li[q] * li[q] + rr[q] * rr[q] + ri[q] * ri[q]) / 2;
    for (let q = 0; q < NB; q++) {
      const j = K0 + q;
      re[q] += lr[j] * rr[j] + li[j] * ri[j]; im[q] += li[j] * rr[j] - lr[j] * ri[j];
      pw[q] += (lr[j] * lr[j] + li[j] * li[j] + rr[j] * rr[j] + ri[j] * ri[j]) / 2;
    }
  }
  return { re, im, pw, full, frames: k };
}
const bandDb = (v, p) => {
  const out = {};
  for (const [name, [lo, hi]] of Object.entries(BANDS)) {
    let a = 0, b = 0;
    for (let q = Math.ceil(lo * NFFT / SR); q < Math.min(Math.floor(hi * NFFT / SR) + (hi === 8000 ? 1 : 0), NFFT / 2 + 1); q++) { a += v[q]; b += p[q]; }
    out[name] = b > 0 && a > 0 ? r2(10 * Math.log10(a / b)) : null;
  }
  return out;
};

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  const c = JSON.parse(line), L = i16(c.L), R = i16(c.R), on = c.onset_sample, d = c.baseline_m, st = steerOf(d);
  const rec = { dataset: c.dataset || 'starss23', scenario: c.scenario || `${c.room} pair ${c.pair.join('')}`, id: c.id || `${c.pair.join('')}/${c.file}/${c.onset_s}/${c.cls}/${c.src}`,
                pair_mm: r2(d * 1000), gcc: null, a2: null, pause_deg: null, snr_db: null };
  // GccPhat, the stream as the Conductor drives it, with the read snapshotted as the audio grows
  try {
    const from = on - PREROLL, s = Gcc.createStream(d, { readFrom: from });
    const track = { 43: null, 100: null, 250: null, lock: null };
    let o = null, firstDraw = false;
    for (let i = 0; i < L.length; i += CHUNK) {
      o = s.push(L.subarray(i, i + CHUNK), R.subarray(i, i + CHUNK), i === 0 ? 0 : null);
      const have = (Math.min(i + CHUNK, L.length) - from) / 48, p = o.positions[0];
      if (p && !firstDraw) { firstDraw = true; track[43] = p.deg; }
      if (p && have >= 100 && track[100] === null) track[100] = p.deg;
      if (p && have >= 250 && track[250] === null) track[250] = p.deg;
      if (p && p.locked && track.lock === null) track.lock = p.deg;
    }
    const pos = o && o.positions.length && o.positions[0].locked ? o.positions : null;
    // the copy: pause (PAUSE_MS before the onset, as the stream's pause()), the lock's frames, the weights, the votes
    const pa = from + HOP - Math.round(PAUSE_MS * SR / 1000) - NFFT / 2, pb = from + HOP + NFFT / 2;
    const P = pa >= 0 ? sumFrames(L, R, pa, pb) : null;
    const V = sumFrames(L, R, from, Math.min(from + (Math.ceil(LOCK_S * SR / HOP) - 1) * HOP + NFFT, L.length));   // every frame starting in the half second
    let wt = null;
    if (P) wt = Float64Array.from(P.pw, (n, b) => Math.max(0, Math.min(1, 1 - (n / P.frames) / Math.max(V.pw[b] / V.frames, 1e-30))));
    const mine = Gcc.readSum(V.re, V.im, st, wt);
    const votes = wt ? wt.reduce((a, v) => a + v, 0) : NB;
    rec.gcc = pos ? { angles: pos.map((p) => p.deg), shares: pos.map((p) => r2(p.hits / 500 * 1000) / 1000), widths: pos.map((p) => p.width),
                      tie: !!(pos[1] && pos[1].tie), votes: r2(votes), votes_of: NB, frames: V.frames, track,
                      replica_ok: !!mine && mine.deg === pos[0].deg }
                    : { angles: [], shares: [], widths: [], tie: false, votes: r2(votes), votes_of: NB, frames: V.frames, track, replica_ok: !mine };
    // the pause's own direction: the 0.5 s before the onset, every whole frame in it, unweighted
    const Q = sumFrames(L, R, Math.max(0, on - SR / 2), on);
    const pr = Q.frames ? Gcc.readSum(Q.re, Q.im, st, null) : null;
    rec.pause_deg = pr ? pr.deg : null;
    rec.pause_share = pr ? pr.share : null;
    const vf = V.full.map((v) => v / V.frames), qf = Q.full.map((v) => v / Math.max(Q.frames, 1));
    rec.snr_db = bandDb(vf, qf);
    // each third-octave band's share of the voice's excess power over the pause, 300 Hz-8 kHz
    const ex = THIRDS.map((fc) => {
      let e = 0;
      for (let q = Math.ceil(fc * 2 ** (-1 / 6) * NFFT / SR); q <= Math.min(Math.floor(fc * 2 ** (1 / 6) * NFFT / SR), Math.floor(8000 * NFFT / SR)); q++) e += Math.max(0, vf[q] - qf[q]);
      return e;
    });
    const tot = ex.reduce((a, v) => a + v, 0);
    rec.voice_bands = THIRDS.map((fc, i) => [fc, tot > 0 ? Math.round(ex[i] / tot * 1000) / 1000 : null]);
  } catch (e) { rec.gcc_err = String(e); }
  // Angle2's onset and its second family
  try {
    const r = A2.readUtterance(L, R, on, d);
    rec.a2 = r ? { deg: r2(r.onset.deg), edge: r.onset.edge ?? null, first_ms: r2((r.onset.first - on) / 48), at3_ms: r2((r.onset.at3 - on) / 48),
                   second_deg: r.refl ? r2(r.refl.deg) : null } : null;
  } catch (e) { rec.a2_err = String(e); }
  process.stdout.write(JSON.stringify(rec) + '\n');
}
process.stderr.write(`GccPhat: ${noPeak} flat scans (no read); Angle2: ${a2Zero} logged 0 deg window reads\n`);
