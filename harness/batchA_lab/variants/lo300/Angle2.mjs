// BAND COPY for harness/batchA_lab (cause 4): the analysis band starts at 300 Hz. Not the shipped scheme.
// Angle2.mjs -- A BEARING SCHEME: every sound's ONSET and its FIRST REFLECTION, told apart by when they arrive.
//
// Jay, 2026-10-20: "I'm trying to create a listening app robust enough to determine the difference between the actual
// onset vs a reflection ... if the first onset and reflection are indistinguishable, I'm ok with rendering both as dimmed
// speech bubbles" -- "Build it and let's see what happens. I just want accurate onset and 1st reflection" -- "Conductor
// has its own scheme to recognize speech, which might differ from your implementation, so if yours is working, we just
// try yours." Ported from the scratch Python that was checked on synthetic copies (onset 27/27, the gap to within two
// samples, the reflection within 4 deg on 16 of 22 decided) and on walk-012435 (12 of 200 sounds told apart, the onset on
// the side Jay named 10 of 12).
//
//   ITS OWN SOUNDS: every 21 ms frame (STEP apart) whose whole 1.1-8 kHz level clears SOUND_DB over that band's own floor
//   (Jay's down-fast/up-barely; seeded from the Conductor's per-frequency floor when it hands one over) -- the same test
//   as geonar/angle_rays.py, on the tape's own frame grid. A sound starts at the first frame that clears after one that did not. The Conductor's
//   utterance only decides which audio arrives here; the sounds inside it are found here.
//   THE ONSET: Angle's read of the sound's first frame (peaksOf, below, copied from Angle.mjs, keeping its per-frequency
//   evidence as AngleNew does) gives its strongest directions; AngleNew's ghost test drops any that is another's aliasing
//   ghost. Two mics can cancel exactly one direction. Only the direct sound has arrived in the first millisecond after
//   the sound starts, so the direction whose cancellation leaves the least there is the onset -- when it leaves at most
//   MARGIN of what the runner-up leaves. Otherwise the strongest real direction stands, undecided.
//   THE FIRST REFLECTION: until it arrives, the left mic holds the direct sound alone -- a clean copy of the voice. The
//   reflection is that waveform again, later, from its own direction: after the direct is cancelled, what remains is
//   g * [s(t - G - tau_b) - s(t - G - tau_onset)]. The earliest G (1-12 ms) where a POSITIVE copy (g > 0: a wall does not
//   flip the wave; g < 0 is the fit's mirror twin) at one of Angle's 181 delays explains FIT_MIN of the remainder is the
//   first reflection, G its lag.
//   UNDECIDED (no start out of a quieter moment, or no clean copy found): the onset and Angle's next direction at least
//   SEP_DEG away are both published, the second as a tie -- Jay: "render both as dimmed speech bubbles".
//   PER UTTERANCE: the first sound whose onset and reflection were told apart; until one is, the first sound's pair.
//   Nothing is averaged: one frame's peaks, sample-level timing, one fit per delay.
//   Delay convention is Angle's: R(t) = L(t - tau), deg = asin(-tau c / d), +deg reaches R first.
//   THE UTTERANCE'S ONSET (readUtterance, below): the first direction to recur three times from 100 ms before the
//   Conductor's onset, counting rising windows first -- what Render's puck uses for an utterance when the tape has it
//   (geonar/angle_rays.py).
//   NOT ACTIVE until RangeMath/active.json names it: {"bearing": "Angle2"}.
export const FRAME = 1024, STEP = 512, NFFT = 2048, LO_HZ = 300, HI_HZ = 8000, PRE = 0.97, SCAN_TAUS = 181;
export const BLOCK = FRAME;                    // the read's length under its old name
export const SEP_DEG = 10, TIE_SHARE = 0.8, REFL_MS = 30;
const SR = 48000, C = 343;
const round = (v, d) => Number(v.toFixed(d));
// THE START-WEIGHTED WINDOW (Jay, 2026-10-12: "We favor the full weight at first sample"): a falling half-cosine, full
// weight at the frame's first sample and none at its last, its power centred 4.9 ms in (a Hann's is 10.7 ms). At an onset
// the direct sound is alone in the first few ms and the floor bounce and near walls arrive by the middle, so the read
// leans on the direct -- precedence, with 21 ms of evidence behind it. Its power matches the Hann's (1.001), so the
// Conductor's floor (bandfloor.py, Hann) still lines up bin for bin. On walk-203939, with the read starting one frame
// before the MF onset (the Conductor hands it over from there): -8, -8, +37, +50 against marks -7, -7, +38, +46.
const HANN = Float64Array.from({ length: FRAME }, (_, i) => 0.5 + 0.5 * Math.cos(Math.PI * i / (FRAME - 1)));

// radix-2 FFT in place (forward, e^-j), tables cached per size
const TABLES = new Map();
function fft(re, im) {
  const N = re.length;
  let T = TABLES.get(N);
  if (!T) {
    const bits = Math.round(Math.log2(N)), rev = new Uint32Array(N), cos = new Float64Array(N / 2), sin = new Float64Array(N / 2);
    for (let i = 0; i < N; i++) { let r = 0; for (let b = 0; b < bits; b++) r |= ((i >> b) & 1) << (bits - 1 - b); rev[i] = r; }
    for (let k = 0; k < N / 2; k++) { cos[k] = Math.cos(2 * Math.PI * k / N); sin[k] = -Math.sin(2 * Math.PI * k / N); }
    TABLES.set(N, (T = { rev, cos, sin }));
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

/* The steering table for one pair: each band bin's phase at each delay, built once per spacing. */
let STEER = null;
function steer(baselineM) {
  if (STEER && STEER.baselineM === baselineM) return STEER;
  const k0 = Math.ceil(LO_HZ * NFFT / SR), k1 = Math.floor(HI_HZ * NFFT / SR), nb = k1 - k0 + 1, tmax = baselineM / C, J = SCAN_TAUS - 1;
  const tauOf = (j) => -tmax + 2 * tmax * j / J;
  const cos = new Float64Array(nb * SCAN_TAUS), sin = new Float64Array(nb * SCAN_TAUS);
  for (let b = 0; b < nb; b++) for (let j = 0; j < SCAN_TAUS; j++) {
    const a = 2 * Math.PI * tauOf(j) * (k0 + b) * SR / NFFT;
    cos[b * SCAN_TAUS + j] = Math.cos(a); sin[b * SCAN_TAUS + j] = Math.sin(a);
  }
  const deg = Float64Array.from({ length: SCAN_TAUS }, (_, j) => Math.asin(Math.max(-1, Math.min(1, -tauOf(j) * C / baselineM))) * 180 / Math.PI);
  return (STEER = { baselineM, k0, nb, cos, sin, tauOf, deg });
}

/* One frame from `start`: its peaks, strongest first, each {deg, tau_ms, share}. `floor` is the Conductor's dB floor, one
   value per band bin (geonar/bandfloor.py), or null. The first difference reaches one sample back when the stream has it;
   at the very start of a stream the first sample stands for its own past. */
export function peaksOf(L, R, start, baselineM, floor = null) {
  const S = steer(baselineM), weighted = !!(floor && floor.length === S.nb);
  const lr = new Float64Array(NFFT), li = new Float64Array(NFFT), rr = new Float64Array(NFFT), ri = new Float64Array(NFFT);
  for (let i = 0; i < FRAME; i++) {
    const p = start + i - 1 >= 0 ? start + i - 1 : start + i;
    lr[i] = (L[start + i] - PRE * L[p]) * HANN[i];
    rr[i] = (R[start + i] - PRE * R[p]) * HANN[i];
  }
  fft(lr, li); fft(rr, ri);
  const score = new Float64Array(SCAN_TAUS), bins = { f: [], cr: [], ci: [] };
  let wsum = 0;
  for (let b = 0; b < S.nb; b++) {
    const k = S.k0 + b, re = lr[k] * rr[k] + li[k] * ri[k], im = li[k] * rr[k] - lr[k] * ri[k], m = Math.hypot(re, im);
    if (m === 0) continue;
    let w = 1;
    if (weighted) {
      const lev = 10 * Math.log10(0.5 * (lr[k] * lr[k] + li[k] * li[k] + rr[k] * rr[k] + ri[k] * ri[k]) + 1e-12);
      w = 1 - Math.pow(10, (floor[b] - lev) / 10);
      if (!(w > 0)) continue;                                   // at or below its floor: no vote
    }
    wsum += w;
    const cr = w * re / m, ci = w * im / m, o = b * SCAN_TAUS;
    bins.f.push(k * SR / NFFT); bins.cr.push(cr); bins.ci.push(ci);
    for (let j = 0; j < SCAN_TAUS; j++) score[j] += cr * S.cos[o + j] + ci * S.sin[o + j];
  }
  if (!wsum) return [];
  const peaks = [];
  for (let j = 1; j < SCAN_TAUS - 1; j++)
    if (score[j] > score[j - 1] && score[j] >= score[j + 1]) peaks.push({ deg: S.deg[j], tau_ms: S.tauOf(j) * 1000, share: score[j] / wsum });
  peaks.sort((a, b) => b.share - a.share);
  peaks.bins = bins;                                   // Angle2: every voting bin's evidence, for the ghost test (as AngleNew)
  return peaks;
}

/* The math host's stream: audio pushed as it arrives; frames read from the onset, STEP apart. opts.floor: the Conductor's
   floor at the onset. */

// ======================================================================================================================
// Angle2: sounds, onset by cancellation, first reflection by the clean copy
// ======================================================================================================================
export const SOUND_DB = 10, RISE_DB = 6, HOLD = 12, CANDIDATES = 6;
export const MIN_GAP_MS = 1, MAX_GAP_MS = 12, MAX_WIN_MS = 2, FIT_MIN = 0.7, REL_MIN = 0.1, MARGIN = 0.5;
/* AngleNew's ghost test, unchanged: only the frequencies where a's and b's phases differ by more than a quarter turn can
   tell them apart; in those, b's net vote. A spatial-aliasing ghost (at 157 mm a direction folds onto another above
   ~1.1 kHz: +47 deg reads about -39 deg at 1.6 kHz, walk-203939 at 38 s) wins none there, so its net is at or below 0. */
export function isGhost(peaks, a, b) {
  const bins = peaks.bins;
  if (!bins) return false;
  let net = 0;
  const ta = a.tau_ms / 1000, tb = b.tau_ms / 1000;
  for (let i = 0; i < bins.f.length; i++) {
    const f = bins.f[i];
    if (Math.cos(2 * Math.PI * f * (ta - tb)) >= 0) continue;          // not a deciding frequency
    const ph = 2 * Math.PI * tb * f;
    net += bins.cr[i] * Math.cos(ph) + bins.ci[i] * Math.sin(ph);
  }
  return net <= 0;
}
const SEG = 2880, NSEG = 8192, REG = 1024, NREG = 2048, LEAD = 64;   // +-60 ms around a sound; the reflection's region
const REF_LO = 1440, REF_HI = 480, LOOK = 1024;                    // quiet reference -30..-10 ms; start searched to +21 ms
// The 1.1-8 kHz band of the scratch Python: scipy butter(6, [1100, 8000], 'bandpass', fs=48000), run forward and back
// (zero phase), i.e. |H|^2 at every frequency.
const SOS = [[0.003583147879167081, 0.007166295758334162, 0.003583147879167081, 1.0, -0.6085974689515035, 0.10923883981133077],
  [1.0, 2.0, 1.0, 1.0, -0.6633877973629971, 0.265839854765454],
  [1.0, 2.0, 1.0, 1.0, -0.8315925163053838, 0.6532166078232604],
  [1.0, -2.0, 1.0, 1.0, -1.9207769455111297, 0.9224720783083171],
  [1.0, -2.0, 1.0, 1.0, -1.9446405744737894, 0.9462421937616051],
  [1.0, -2.0, 1.0, 1.0, -1.9795078447473478, 0.9810475093088119]];
const GAINS = new Map();
function bandGain(N) {
  let g = GAINS.get(N);
  if (g) return g;
  g = new Float64Array(N);
  for (let k = 0; k <= N / 2; k++) {
    const w = 2 * Math.PI * k / N, c1 = Math.cos(w), s1 = Math.sin(w), c2 = Math.cos(2 * w), s2 = Math.sin(2 * w);
    let p = 1;
    for (const [b0, b1, b2, , a1, a2] of SOS) {
      const nr = b0 + b1 * c1 + b2 * c2, ni = -(b1 * s1 + b2 * s2), dr = 1 + a1 * c1 + a2 * c2, di = -(a1 * s1 + a2 * s2);
      p *= (nr * nr + ni * ni) / (dr * dr + di * di);
    }
    g[k] = p; if (k > 0 && k < N / 2) g[N - k] = p;
  }
  GAINS.set(N, g);
  return g;
}
const ifft = (re, im) => {                                          // in place, via the forward transform
  const N = re.length;
  for (let i = 0; i < N; i++) im[i] = -im[i];
  fft(re, im);
  for (let i = 0; i < N; i++) { re[i] /= N; im[i] = -im[i] / N; }
};
function spectrum(x, from, n, N) {                                   // x[from .. from+n) zero-padded to N
  const re = new Float64Array(N), im = new Float64Array(N);
  for (let i = 0; i < n; i++) re[i] = x[from + i];
  fft(re, im);
  return { re, im };
}
const sfreq = (k, N) => (k <= N / 2 ? k : k - N) * SR / N;           // signed frequency of bin k
function shifted(S, tau, N, aRe, aIm) {                              // S delayed by tau s, written into (aRe, aIm)
  for (let k = 0; k < N; k++) {
    const ph = -2 * Math.PI * sfreq(k, N) * tau, c = Math.cos(ph), s = Math.sin(ph);
    aRe[k] = S.re[k] * c - S.im[k] * s; aIm[k] = S.re[k] * s + S.im[k] * c;
  }
}
function analytic(re, im, n) {                                       // a spectrum -> [signal, its envelope], n samples
  const N = re.length, zr = new Float64Array(N), zi = new Float64Array(N);
  zr[0] = re[0]; zi[0] = im[0]; zr[N / 2] = re[N / 2]; zi[N / 2] = im[N / 2];
  for (let k = 1; k < N / 2; k++) { zr[k] = 2 * re[k]; zi[k] = 2 * im[k]; }
  ifft(zr, zi);
  const x = new Float64Array(n), e = new Float64Array(n);
  for (let i = 0; i < n; i++) { x[i] = zr[i]; e[i] = Math.hypot(zr[i], zi[i]); }
  return [x, e];
}
function causalEnv(x, from, n) {                                     // |first difference|, a look-back running max
  const d = new Float64Array(n), e = new Float64Array(n);
  for (let i = 0; i < n; i++) { const j = from + i; d[i] = i === 0 ? 0 : Math.abs(x[j] - PRE * x[j - 1]); }
  for (let i = HOLD - 1; i < n; i++) { let m = 0; for (let h = 0; h < HOLD; h++) m = Math.max(m, d[i - h]); e[i] = m; }
  return e;
}
function firstRise(env, refLo, refHi, lo, hi) {
  let ref = 0; for (let i = refLo; i < refHi; i++) ref = Math.max(ref, env[i]);
  const thr = ref * Math.pow(10, RISE_DB / 20);
  for (let i = lo; i < hi - HOLD; i++) {
    let all = true; for (let h = 0; h < HOLD; h++) if (!(env[i + h] > thr)) { all = false; break; }
    if (all) return i;
  }
  return null;
}
const degOf = (tau, baselineM) => Math.asin(Math.max(-1, Math.min(1, -tau * C / baselineM))) * 180 / Math.PI;

/* One sound whose first frame starts at `s`: its onset and first reflection, or the undecided pair. Needs SEG samples on
   both sides of s; returns null until they are there. Exported for checking against the scratch Python. */
export function readSound(L, R, s, baselineM, floor = null) {
  if (s + SEG > L.length) return null;
  const all = peaksOf(L, R, s, baselineM, floor), top = all.slice(0, CANDIDATES);
  if (!top.length) return null;
  // GHOSTS OUT FIRST (Jay, 2026-10-20, walk-203939 at 37.7 s: -38 deg, the alias of his +46): a candidate that another
  // candidate shows to be its aliasing ghost -- and not the other way round -- cannot be an arrival at all
  const real = top.filter((b) => !top.some((a) => a !== b && isGhost(all, a, b) && !isGhost(all, b, a)));
  const peaks = real.length ? real : top;
  const pair = (on) => peaks.find((q) => Math.abs(q.deg - on.deg) >= SEP_DEG) || null;
  const undecided = (on, why) => ({ start: s, onset: on, other: pair(on), refl: null, gap_ms: null, decided: false, why });
  const lo = s - SEG;
  if (lo < 0) return undecided(peaks[0], 'not enough before it');
  const n = 2 * SEG, s0 = SEG, gain = bandGain(NSEG);
  const Ls = spectrum(L, lo, n, NSEG), Rs = spectrum(R, lo, n, NSEG);
  for (let k = 0; k < NSEG; k++) { Ls.re[k] *= gain[k]; Ls.im[k] *= gain[k]; Rs.re[k] *= gain[k]; Rs.im[k] *= gain[k]; }
  const [lf, el] = analytic(Ls.re, Ls.im, n), [, er] = analytic(Rs.re, Rs.im, n);
  const envx = new Float64Array(n); for (let i = 0; i < n; i++) envx[i] = el[i] + er[i];
  const ecl = causalEnv(L, lo, n), ecr = causalEnv(R, lo, n), envc = new Float64Array(n);
  for (let i = 0; i < n; i++) envc[i] = ecl[i] + ecr[i];
  const t0 = firstRise(envc, s0 - REF_LO, s0 - REF_HI, s0 - REF_HI, s0 + LOOK);
  if (t0 === null) return undecided(peaks[0], 'no start out of a quieter moment');
  const end = Math.min(n, t0 + 720), e1 = t0 + 48;
  let peak = 1e-12; for (let i = t0; i < end; i++) peak = Math.max(peak, envx[i]);
  // THE ONSET: the direction whose cancellation leaves the least in the first millisecond -- ONLY WHEN IT IS CLEARLY
  // LEAST (Jay, 2026-10-20, walk-203939 at 19 s: in a soft ramp every candidate left 0.15-0.27 and -71 deg won a coin
  // flip over his +38). It must leave at most MARGIN of what the runner-up leaves; otherwise the onset is the strongest
  // real direction and the sound is undecided.
  const aRe = new Float64Array(NSEG), aIm = new Float64Array(NSEG), tried = [];
  for (const c of peaks) {
    shifted(Ls, c.tau_ms / 1000, NSEG, aRe, aIm);
    for (let k = 0; k < NSEG; k++) { aRe[k] = Rs.re[k] - aRe[k]; aIm[k] = Rs.im[k] - aIm[k]; }
    const [y, ey] = analytic(aRe, aIm, n);
    let leak = 0; for (let i = t0; i < e1; i++) leak = Math.max(leak, ey[i]);
    tried.push({ leak: leak / peak, c, y });
  }
  tried.sort((a, b) => a.leak - b.leak);
  if (tried.length > 1 && tried[0].leak > MARGIN * tried[1].leak)
    return undecided(peaks[0], 'no clear first arrival: cancelling any direction leaves about the same');
  const on = tried[0].c, y = tried[0].y;
  // THE FIRST REFLECTION: the earliest positive copy of the direct-only voice that explains what remains
  const S = steer(baselineM), a0 = t0 - LEAD, reg = spectrum(lf, a0, Math.min(REG, n - a0), NREG);
  const W = Math.round(MAX_WIN_MS * SR / 1000), rRe = new Float64Array(NREG), rIm = new Float64Array(NREG);
  const take = (tau) => {                                            // the band-limited left mic delayed by tau, from t0
    shifted(reg, tau, NREG, rRe, rIm); ifft(rRe, rIm);
    return Float64Array.from({ length: W }, (_, u) => rRe[LEAD + u]);
  };
  const ref = take(on.tau_ms / 1000), X = [], XX = [];
  for (let j = 0; j < SCAN_TAUS; j++) {
    const sh = take(S.tauOf(j)), x = new Float64Array(W), cum = new Float64Array(W + 1);
    for (let u = 0; u < W; u++) { x[u] = sh[u] - ref[u]; cum[u + 1] = cum[u] + x[u] * x[u]; }
    X.push(x); XX.push(cum);
  }
  let found = null;
  for (let G = Math.round(MIN_GAP_MS * SR / 1000); G < Math.round(MAX_GAP_MS * SR / 1000); G++) {
    const win = Math.min(G, W), w0 = t0 + G;
    if (w0 + win > n) break;
    let ey2 = 1e-12, ex2 = 0;
    for (let u = 0; u < win; u++) { ey2 += y[w0 + u] * y[w0 + u]; ex2 += envx[w0 + u] * envx[w0 + u]; }
    const rel = Math.sqrt(ey2 / ex2);
    let top = null;
    for (let j = 0; j < SCAN_TAUS; j++) {
      const x = X[j], xx = XX[j][win];
      if (!(xx > 0)) continue;
      let xy = 0; for (let u = 0; u < win; u++) xy += x[u] * y[w0 + u];
      const g = xy / xx;
      if (!(g > 0)) continue;
      const fit = g * xy / ey2;
      if (!top || fit > top.fit) top = { fit, j, g };
    }
    if (top && top.fit >= FIT_MIN && rel >= REL_MIN) { found = { ...top, G }; break; }
  }
  if (!found) return undecided(on, 'no clean copy of the voice found after it');
  const tau = S.tauOf(found.j);
  return { start: s, onset: on, other: null, decided: true, gap_ms: found.G * 1000 / SR,
           refl: { deg: degOf(tau, baselineM), tau_ms: tau * 1000, fit: found.fit, gain: found.g, at: lo + t0 + found.G } };
}

// ======================================================================================================================
// THE UTTERANCE'S ONSET, DIRECTION FIRST (Jay, 2026-10-20, walk-203939 at 37.6 s: "+54-degree angle MUST shine through as the
// correct/salient one" -- "this still tracks with human hearing" -- "It doesn't have to resolve EVERY angle that's off. Just a
// handful. So go ahead and apply that change"). From U_BEFORE_MS before the Conductor's onset, every U_WIN (3 ms) window,
// one millisecond apart, is read for its strongest delay in Angle's band -- counted only once the voice is U_GATE_DB over the
// quietest millisecond of the 100 ms before the scan. Reads within U_AGREE samples of delay are one direction (samples, not
// degrees: one sample is ~3 deg straight ahead but ~13 deg near the ends of the mic axis, where a degree test was five
// times stricter). The first direction to recur U_HITS times -- not necessarily in a row -- is the onset; the next one to do
// so, the first reflection. Precedence still: the earliest direction that keeps coming back, not the loudest. Nothing is
// averaged: each window's own peak, counted. The scan runs at most U_LONG_MS.
// On walk-203939 (hand count before this was built): 19.1 s +30s, 37.7 s +54/+59/+51 29 ms before the Conductor's onset,
// 56.4 s +90/+61/+73 ahead of the kitchen reflection's -38 family.
// THE ONSET FROM CLEAN, RISING WINDOWS (2026-10-22, results/angle2_pull.md). On STARSS23 the onset read 2-19 deg nearer
// 0 than GccPhat, growing with angle. In image-source rooms it is neither U_AGREE nor U_HITS: it is WHEN the count starts.
// In a room with noise (or the last phrase's tail) the voice clears the gate tens of ms after it starts; by then the
// floor, ceiling and front/back walls -- all images nearer 0 than the talker -- are in every 3 ms window, and the first
// family to recur is theirs or a blend. Two tests pick the windows the direct sound still holds alone: the level is
// U_RISE_DB over the window U_RISE_MS before (new sound, and new sound reaches the mics direct first), and the read's peak
// holds U_CLEAN of the band's votes (one wave, not a blend). The onset is the first direction to recur U_EDGE_HITS times
// among those windows; when none does within U_LONG_MS, the first to recur U_HITS times among all counted windows, as
// before, flagged edge: false. The first reflection is unchanged: the next direction to recur among all counted
// windows, other than the onset's. On the room sweep (94 sets): 2576 onsets moved to within 10 deg, 557 out of it.
// ======================================================================================================================
export const U_WIN = 144, U_GATE_DB = 10, U_HITS = 3, U_AGREE = 3, U_BEFORE_MS = 100, U_LONG_MS = 600;
export const U_RISE_DB = 3, U_RISE_MS = 3, U_CLEAN = 0.6, U_EDGE_HITS = 2;
const U_N = 1024, U_K0 = Math.ceil(LO_HZ * U_N / SR), U_K1 = Math.floor(HI_HZ * U_N / SR);
const U_HANN = Float64Array.from({ length: U_WIN }, (_, i) => 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (U_WIN - 1)));
let U_STEER = null;
function uSteer(baselineM) {
  if (U_STEER && U_STEER.baselineM === baselineM) return U_STEER;
  const tmax = baselineM / C, J = SCAN_TAUS - 1, nb = U_K1 - U_K0 + 1;
  const tauOf = (j) => -tmax + 2 * tmax * j / J;
  const cos = new Float64Array(nb * SCAN_TAUS), sin = new Float64Array(nb * SCAN_TAUS);
  for (let b = 0; b < nb; b++) for (let j = 0; j < SCAN_TAUS; j++) {
    const a = 2 * Math.PI * tauOf(j) * (U_K0 + b) * SR / U_N;
    cos[b * SCAN_TAUS + j] = Math.cos(a); sin[b * SCAN_TAUS + j] = Math.sin(a);
  }
  return (U_STEER = { baselineM, nb, cos, sin, tauOf });
}
// LOGGED READS (Jay, 2026-10-22: "anytime [the angle] evaluates to 0, log the values"), as GccPhat.mjs: console.warn,
// tagged; setLog() swaps the sink.
export let LOG = (tag, values) => console.warn(tag, JSON.stringify(values));
export function setLog(fn) { LOG = fn; }
function uRead(lf, rf, a, S, t) {                    // one 3 ms window's strongest delay (s) and its peak's share of the votes
  const lr = new Float64Array(U_N), li = new Float64Array(U_N), rr = new Float64Array(U_N), ri = new Float64Array(U_N);
  for (let i = 0; i < U_WIN; i++) { lr[i] = lf[a + i] * U_HANN[i]; rr[i] = rf[a + i] * U_HANN[i]; }
  fft(lr, li); fft(rr, ri);
  const score = new Float64Array(SCAN_TAUS);
  for (let b = 0; b < S.nb; b++) {
    const k = U_K0 + b, re = lr[k] * rr[k] + li[k] * ri[k], im = li[k] * rr[k] - lr[k] * ri[k], m = Math.hypot(re, im);
    if (m === 0) continue;
    const cr = re / m, ci = im / m, o = b * SCAN_TAUS;
    for (let j = 0; j < SCAN_TAUS; j++) score[j] += cr * S.cos[o + j] + ci * S.sin[o + j];
  }
  // every delay scored first, then the tallest; a flat or broken scan (no bin voted, or NaNs) is no read rather than
  // index 0, the most negative delay, +90 deg (Jay, 2026-10-22)
  let j = 0, lo = score[0];
  for (let q = 1; q < SCAN_TAUS; q++) { if (score[q] > score[j]) j = q; if (score[q] < lo) lo = score[q]; }
  if (!score.every(Number.isFinite) || score[j] - lo <= 1e-9 * S.nb) {
    LOG('[Angle2] no peak', { at: t, finite: score.every(Number.isFinite), max: score[j], min: lo });
    return null;
  }
  const tau = S.tauOf(j), share = score[j] / S.nb;
  if (round(degOf(tau, S.baselineM), 2) === 0)
    LOG('[Angle2] zero', { at: t, j, tau_ms: round(tau * 1000, 4), score: round(score[j], 4), share: round(share, 3),
      min: round(lo, 4), mean: round(score.reduce((x, v) => x + v, 0) / SCAN_TAUS, 4) });
  return { tau, share };
}
/* The utterance whose Conductor onset is at sample `at`: { onset: {deg, first, at3, edge}, refl: {deg, first, at3} | null }
   in tape samples (first = the direction's first read, at3 = the read that made it recur U_HITS times; edge = the onset
   came from the clean, rising windows), or null when no direction recurred within U_LONG_MS or the tape has too little
   around it. `trace`, when an array, gets every counted window's read {at, db (over the floor), rise (dB over the window
   U_RISE_MS before), share, deg, fam (its family's index)}, for checking. */
export function readUtterance(L, R, at, baselineM, trace = null) {
  const a0 = at - U_BEFORE_MS * 48, f0 = a0 - 100 * 48, pad = 2048;
  const lo = f0 - pad, hi = at + U_LONG_MS * 48 + U_WIN + pad;      // the scan starts 100 ms + pad in: room to look U_RISE_MS back
  if (lo < 0 || hi > L.length) return null;
  const n = hi - lo; let N = 1; while (N < n) N <<= 1;
  const g = bandGain(N), Ls = spectrum(L, lo, n, N), Rs = spectrum(R, lo, n, N);
  for (let k = 0; k < N; k++) { Ls.re[k] *= g[k]; Ls.im[k] *= g[k]; Rs.re[k] *= g[k]; Rs.im[k] *= g[k]; }
  ifft(Ls.re, Ls.im); ifft(Rs.re, Rs.im);
  const lf = Ls.re, rf = Rs.re, S = uSteer(baselineM);
  let floorDb = Infinity;
  for (let b = f0 - lo; b + 48 <= a0 - lo; b += 48) {
    let e = 0; for (let i = 0; i < 48; i++) e += lf[b + i] * lf[b + i] + rf[b + i] * rf[b + i];
    floorDb = Math.min(floorDb, 10 * Math.log10(e / 48 + 1e-12));
  }
  const tally = (fs, ds, tau, t) => {                              // count a read into its family (new if none within U_AGREE)
    let f = fs.find((q) => Math.abs(q.ds - ds) <= U_AGREE);
    if (!f) { f = { ds, tau, first: t, hits: 0 }; fs.push(f); }
    f.hits++; return f;
  };
  const fams = [], edges = [], recurred = [];   // families of every counted window, of the clean rising ones; fams in the order they recurred
  let edge = null;
  const other = (r) => Math.abs(r.f.ds - edge.f.ds) > U_AGREE;
  for (let ms = 0; ms < U_LONG_MS + U_BEFORE_MS && !(edge && recurred.some(other)); ms++) {
    const a = a0 - lo + ms * 48, b = a - U_RISE_MS * 48;
    let e = 0, e0 = 0;
    for (let i = 0; i < U_WIN; i++) { e += lf[a + i] * lf[a + i] + rf[a + i] * rf[a + i]; e0 += lf[b + i] * lf[b + i] + rf[b + i] * rf[b + i]; }
    const db = 10 * Math.log10(e / U_WIN + 1e-12) - floorDb, rise = 10 * Math.log10((e + 1e-12) / (e0 + 1e-12));
    if (db < U_GATE_DB) continue;
    const t = a0 + ms * 48, u = uRead(lf, rf, a, S, t);
    if (!u) continue;                                             // a scan with no peak has no direction: no vote
    const { tau, share } = u, ds = tau * SR;
    const f = tally(fams, ds, tau, t);
    if (trace) trace.push({ at: t, db, rise, share, deg: degOf(tau, baselineM), fam: fams.indexOf(f) });
    if (f.hits === U_HITS) recurred.push({ f, at3: t });
    if (!edge && rise >= U_RISE_DB && share >= U_CLEAN) { const h = tally(edges, ds, tau, t); if (h.hits === U_EDGE_HITS) edge = { f: h, at3: t }; }
  }
  const pos = (r, isEdge) => ({ deg: degOf(r.f.tau, baselineM), first: r.f.first, at3: r.at3, ...(isEdge === undefined ? {} : { edge: isEdge }) });
  if (edge) { const r = recurred.find(other); return { onset: pos(edge, true), refl: r ? pos(r) : null }; }
  return recurred.length ? { onset: pos(recurred[0], false), refl: recurred[1] ? pos(recurred[1]) : null } : null;
}

// the whole band's level of one frame, as geonar/detect_movie.band_level: first difference, a symmetric Hann, the two
// capsules' power averaged, summed over Angle's band
const BAND_K0 = Math.ceil(LO_HZ * NFFT / SR), BAND_K1 = Math.floor(HI_HZ * NFFT / SR);
const SYM_HANN = Float64Array.from({ length: FRAME }, (_, i) => 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (FRAME - 1)));
function bandLevel(L, R, s) {
  const lr = new Float64Array(NFFT), li = new Float64Array(NFFT), rr = new Float64Array(NFFT), ri = new Float64Array(NFFT);
  for (let i = 0; i < FRAME; i++) {
    const p = s + i - 1 >= 0 ? s + i - 1 : s + i;
    lr[i] = (L[s + i] - PRE * L[p]) * SYM_HANN[i]; rr[i] = (R[s + i] - PRE * R[p]) * SYM_HANN[i];
  }
  fft(lr, li); fft(rr, ri);
  let sum = 0;
  for (let k = BAND_K0; k <= BAND_K1; k++) { sum += 0.5 * (lr[k] * lr[k] + li[k] * li[k] + rr[k] * rr[k] + ri[k] * ri[k]); }
  return 10 * Math.log10(sum + 1e-12);
}

export function createStream(baselineM, opts = {}) {
  let L = new Int16Array(48000), R = new Int16Array(48000), len = 0, from = 0, firstSample = null, floor = opts.floor || null;
  let k = 0, level = null, prevClear = false, sounds = [], chosen = null;
  // out.sounds: every sound read so far (absolute sample, decided, onset, reflection) -- a list for whoever wants more than
  // the one position per utterance; the math host reads only positions, first and votes
  const out = { positions: [], first: null, votes: [], sounds: [] };
  const seedFloor = () => {
    if (!floor) return null;
    let p = 0; for (const v of floor) p += Math.pow(10, v / 10);
    return 10 * Math.log10(p + 1e-12);
  };
  const r3 = (v) => round(v, 3);
  const publish = () => {
    if (!chosen) { out.first = null; out.positions = []; out.votes = []; return; }
    const o = chosen.onset;
    out.first = { deg: round(o.deg, 2), tau_ms: round(o.tau_ms, 4) };
    out.positions = [{ id: 1, deg: round(o.deg, 2), tau_ms: round(o.tau_ms, 4), hits: r3(o.share), decided: chosen.decided }];
    out.votes = [{ id: 1, start: chosen.start, tau_ms: o.tau_ms }];
    if (chosen.decided) {
      const f = chosen.refl;
      out.positions.push({ id: 2, deg: round(f.deg, 2), tau_ms: round(f.tau_ms, 4), hits: r3(f.fit), lag_ms: round(chosen.gap_ms, 2), tie: false, decided: true });
      out.votes.push({ id: 2, start: f.at, tau_ms: f.tau_ms });
    } else if (chosen.other) {
      const q = chosen.other;
      out.positions.push({ id: 2, deg: round(q.deg, 2), tau_ms: round(q.tau_ms, 4), hits: r3(q.share), tie: true, decided: false });
      out.votes.push({ id: 2, start: chosen.start, tau_ms: q.tau_ms });
    }
  };
  const walk = () => {
    // its own sounds: frames STEP apart ON THE TAPE'S OWN GRID (sample 0, 512, 1024 ... of the recording -- the frames
    // geonar/angle_rays.py and Render's Angle-rays layer read), wherever the Conductor's audio happens to begin; each
    // frame judged against the floor as it stood
    const grid = firstSample === null ? 0 : (STEP - (firstSample % STEP)) % STEP;
    while (grid + k * STEP + FRAME <= len) {
      const at = grid + k * STEP, v = bandLevel(L, R, at);
      if (level === null) level = seedFloor() ?? v;
      const clear = v >= level + SOUND_DB;
      level = v < level ? 0.90 * level + 0.10 * v : 0.999 * level + 0.001 * v;
      if (clear && !prevClear && at >= from - STEP) sounds.push({ at, read: null });
      prevClear = clear; k++;
    }
    let changed = false;
    for (const sd of sounds) {
      if (sd.read) continue;
      if (sd.at + SEG > len) break;
      sd.read = readSound(L.subarray(0, len), R.subarray(0, len), sd.at, baselineM, floor) || { decided: false, none: true };
      if (sd.read.none) continue;
      out.sounds.push({ at: (firstSample ?? 0) + sd.at, decided: sd.read.decided, onset: round(sd.read.onset.deg, 1),
                        refl: sd.read.decided ? round(sd.read.refl.deg, 1) : null, gap_ms: sd.read.decided ? round(sd.read.gap_ms, 2) : null });
      if (!chosen || (!chosen.decided && sd.read.decided)) { chosen = sd.read; changed = true; }
    }
    if (changed) publish();
  };
  return {
    push(l, r, startSample = null) {
      if (startSample !== null && firstSample === null) {
        firstSample = startSample;
        if (opts.readFrom !== null && opts.readFrom !== undefined) from = Math.max(0, opts.readFrom - firstSample);
      }
      if (len + l.length > L.length) {
        const cap = Math.max(len + l.length, L.length * 2), nl = new Int16Array(cap), nr = new Int16Array(cap);
        nl.set(L.subarray(0, len)); nr.set(R.subarray(0, len)); L = nl; R = nr;
      }
      L.set(l, len); R.set(r, len); len += l.length;
      walk();
      return out;
    },
    // a position's own frame, for the range
    window(start) { return start >= 0 && start + FRAME <= len ? { L: L.subarray(start, start + FRAME), R: R.subarray(start, start + FRAME) } : null; },
    // the gate names the onset later: look for sounds again from there
    restart(atSample, newFloor = null) {
      const s = atSample - (firstSample ?? 0);
      if (s < 0 || s > len) return false;
      from = s; k = 0; level = null; prevClear = false; sounds = []; chosen = null; out.sounds = [];
      if (newFloor) floor = newFloor;
      walk(); publish();
      return true;
    },
  };
}
