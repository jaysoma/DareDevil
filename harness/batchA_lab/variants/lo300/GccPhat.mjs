// BAND COPY for harness/batchA_lab (cause 4): the analysis band starts at 300 Hz. Not the shipped scheme.
// GccPhat.mjs -- A BEARING SCHEME FOR THE MATH HOST: textbook GCC-PHAT (Knapp & Carter, 1976) over the utterance's first
// half second, shown while it grows.
//
// Jay, 2026-10-20: "Ok we can try this as the bearing ... disregard that rule for now [the Oct 10 tie-breaker]. We can
// try without beamforming first ... I don't want there to be a half-second lag so maybe after x-ms, we render a dot, and
// it wobbles around until it stabilizes, as we define it like 0.5secs."
//
// THE READ, AS KNAPP AND CARTER DEFINED IT: from the Conductor's read start (read_from_sample, one frame step before its
// onset), 2048-sample Hann frames every 512 samples; each frame's cross-spectrum L conj(R) is ADDED to a running sum, one
// frequency slice at a time (23 Hz each), 300 Hz-8 kHz. The bearing is the PHAT of that sum -- every slice divided by its
// own size, so each frequency casts one vote -- scored over 241 delays across the pair; the tallest score is the delay.
// Nothing else: no second arrival, no tie-breaker, no precedence, no beam. It is SummedHalfSecond's summed read (6daac51)
// with the Oct 10 tie-breaker taken out, reading from where the Conductor says the read starts (SummedHalfSecond read
// from the stream's first sample, which since Conductor v10 is 43 ms of history before that).
// Convention as everywhere: score(tau) = Re sum X^ e^(-j 2 pi f tau), deg = asin(-tau c / d); + reaches R first.
// 300 Hz, NOT 1.1 kHz -- TRIED AND PUT BACK (Jay, 2026-10-21: "Let's try a, b, c" -- then, "If 300Hz works better, than
// sure"). Below about 1.1 kHz this pair hears the room's reverberation in phase, so those slices vote straight ahead; at
// walk-194940 18.42 s the bands read 300-1100 Hz +1, 1.1-3 kHz -42, 3-8 kHz -62, and from 1.1 kHz the sum read -62 for
// +12 (with 40.4, 41.4 and 43.5 s +27, +17, +40 -> -52, -44, -55; the rest within 3 deg). Judged by repetition -- one
// spot, the same angles every utterance, which needs no phone pose -- +12..+17 is in all eight of position one's
// utterances (angles 1-3, below), but so is -7 (angle 2 or 3 at 8.58, 10.63, 14.58 and 18.42 s), and that stop's onsets
// (Angle2's first frames, Render's Onsets layer) read -3..-10: repetition cannot say either band is right there. 300 Hz
// is back as the checked-in state, not as the better band. Angle.mjs keeps 1.1 kHz: in one 21 ms frame the low end
// leaks to 0 deg.
//
// THE SPIN: the dot appears once the sum holds FIRST_MS of audio from the read start, and moves with every frame after
// that (every 10.7 ms) as the sum grows -- the wobble -- until the half second (LOCK_S) is in. Then the read locks and
// holds for the rest of the utterance. While it moves the stream says `settling`, which Render reads as "draw each read
// at once": the walking limit judges one lock against the last, not a read settling. The range waits for the lock:
// `first` (the onset bearing CdrRange is handed, and what the pass waits on before it reads range frames) is set only
// then, so the range sees what it saw under SummedHalfSecond.
// VOTES, for a range that takes them (2026-10-21, FiveMsAmplitude): when the read locks, the first vote is the first 5 ms
// of the voice -- from the Conductor's onset, one step after the read start -- at the locked delay, then one every 5 ms,
// as SummedHalfSecond did. Until Jay's walk-194940 screenshot at 19.2 s it was the 5 ms AT the read start: that window
// ends 5.7 ms before the onset, so the range read the room, not the voice (280 there; the opening 2162, same spot).
// EACH FREQUENCY'S VOTE, WEIGHTED BY THE VOICE OVER THE PAUSE (2026-10-21, walk-194940 position 2; Jay: "if you found a
// solution that works, better still"). A steady source at about -60 deg sounded through that walk's pauses from ~24 s on,
// and PHAT gives every frequency one vote however little voice it holds, so at 3.85 m it outvoted Jay (-58 for +15).
// After the PHAT each slice's vote is scaled by max(0, 1 - N/P): N its mean power over the PAUSE_MS before the onset
// (frames centred in the pause the ears just measured), P its mean power over the read so far. Measured before it
// shipped: 194940 position 1 identical on all 8 onsets; position 2 29.2 s -58 -> +16, 32.4 s +9 -> +12 (28.5 s stays
// -32); 203939's six marked utterances identical or 1 deg closer to the marks. With under PAUSE_MS + a frame of audio
// before the read (a Conductor that hands less history), every vote counts fully: the textbook read.
// TRIED IN ITS PLACE AND BACKED OUT (2026-10-21, Jay's "a, b, c"): the Conductor's floor (geonar/bandfloor.py) for N.
// That floor rises with a ~10 s time constant, so the steady source that starts sounding about 24 s into walk-194940
// was not in it 5 s later: position two read -58 at 29.2 s and -59 at 32.4 s (+17/+13 with the pause). The pause, for
// its part, still weighs Jay away where it holds his own previous phrase (21.62 s).
// A TIE, NOT A DECISION (Jay, 2026-10-21: "if we can render first onset, we would be a step forward" -- "render them as a
// tie rather than introduce more bulky math logic"). At its lock the read also names the tallest other peak of its scan,
// TIE_SEP_DEG or more away, when it scores TIE_SHARE of the lock or more; both go out, the second flagged `tie`, and
// Render draws both. On walk-194940 position 1 that puts Jay's -7 deg (89-97%) beside the +12..+13 lock at 8.6, 10.6
// and 14.6 s; at 18.4 s the runner-up is the room's steady -62 deg source (95%). The Oct 10 tie-breaker is not here.
// ANGLES 1, 2, 3 (Jay, 2026-10-21: "Go ahead on those, and the limits are features to be rendered, not math problems to be
// solved"). At its lock the read names the scan's three tallest peaks, each TIE_SEP_DEG or more from the taller ones, with
// no share cut: angle 1 is the lock, angles 2 and 3 go out as positions #2 and #3 (#2 still flagged the tie when it scores
// TIE_SHARE of the lock). Each carries its width: the angles where the scan stays at half its height or more, so two
// arrivals too close to part read as one wide peak. What two mics cannot tell apart is drawn, not solved: Render shades
// each width and mirrors it behind the phone (front and back give one delay). Judge them by whether a stop's angles
// repeat from utterance to utterance, which needs no phone pose.
export const NFFT = 2048, HOP = 512, LO_HZ = 300, HI_HZ = 8000, TAUS = 241;
export const FIRST_MS = 43;     // the first read: one frame (42.7 ms) from the read start, ~32 ms after the onset
export const TIE_SHARE = 0.8, TIE_SEP_DEG = 10;   // a second direction drawn beside the lock
export const ANGLES = 3;        // angles 1, 2, 3: the scan's tallest peaks, TIE_SEP_DEG apart, each with its width
export const PAUSE_MS = 200;    // the pause before the onset that the votes are weighed against
export const LOCK_S = 0.5;      // the half second: every frame that STARTS inside it, 47 of them (533 ms of audio)
// WHY 47 AND NOT THE 43 THAT END INSIDE 0.5 s (2026-10-20, walk-203939): the dry run Jay approved summed every frame
// starting in the half second; the 43 that end inside it read -12 for -13 at 7.9 s (mark -15) and +83 for +80 at 56.4 s
// (mark about +70). Jay, the same night: anything new that costs accuracy is not implemented.
const SR = 48000, C = 343;
const WIN = 240;                // votes (for a range that takes them) every 5 ms at the locked delay, as SummedHalfSecond
const HANN = Float64Array.from({ length: NFFT }, (_, i) => 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (NFFT - 1)));
function fftTables(N) {
  const bits = Math.round(Math.log2(N)), rev = new Uint32Array(N), cos = new Float64Array(N / 2), sin = new Float64Array(N / 2);
  for (let i = 0; i < N; i++) { let r = 0; for (let b = 0; b < bits; b++) r |= ((i >> b) & 1) << (bits - 1 - b); rev[i] = r; }
  for (let k = 0; k < N / 2; k++) { cos[k] = Math.cos(2 * Math.PI * k / N); sin[k] = -Math.sin(2 * Math.PI * k / N); }
  return { N, rev, cos, sin };
}
function fft(re, im, T) {
  const N = T.N;
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
const K0 = Math.ceil(LO_HZ * NFFT / SR), K1 = Math.floor(HI_HZ * NFFT / SR), NB = K1 - K0 + 1;
const round = (v, d) => Number(v.toFixed(d));
let FFT_T = null;
// THE DELAYS, once per pair spacing: each delay's phase at each frequency slice, and the angle it means
const STEERS = new Map();
function steerOf(baselineM) {
  let s = STEERS.get(baselineM);
  if (s) return s;
  const tmax = baselineM / C, J = TAUS - 1, cos = new Float64Array(TAUS * NB), sin = new Float64Array(TAUS * NB);
  const tau = new Float64Array(TAUS), deg = new Float64Array(TAUS);
  for (let j = 0; j <= J; j++) {
    tau[j] = -tmax + 2 * tmax * j / J;
    deg[j] = Math.asin(Math.max(-1, Math.min(1, -tau[j] * C / baselineM))) * 180 / Math.PI;
    for (let b = 0; b < NB; b++) { const f = (K0 + b) * SR / NFFT, a = 2 * Math.PI * tau[j] * f; cos[j * NB + b] = Math.cos(a); sin[j * NB + b] = Math.sin(a); }
  }
  s = { cos, sin, tau, deg };
  STEERS.set(baselineM, s);
  return s;
}
// one frame's cross-spectrum L conj(R), added to the sum
function addFrame(L, R, s, re, im, w, pw = null) {
  const scale = 1 / 32768;
  for (let i = 0; i < NFFT; i++) { w.lr[i] = L[s + i] * scale * HANN[i]; w.li[i] = 0; w.rr[i] = R[s + i] * scale * HANN[i]; w.ri[i] = 0; }
  fft(w.lr, w.li, FFT_T); fft(w.rr, w.ri, FFT_T);
  for (let b = 0; b < NB; b++) {
    const k = K0 + b;
    re[b] += w.lr[k] * w.rr[k] + w.li[k] * w.ri[k]; im[b] += w.li[k] * w.rr[k] - w.lr[k] * w.ri[k];
    if (pw) pw[b] += (w.lr[k] * w.lr[k] + w.li[k] * w.li[k] + w.rr[k] * w.rr[k] + w.ri[k] * w.ri[k]) / 2;   // the frame's power
  }
}
// LOGGED READS (Jay, 2026-10-22: "anytime [the angle] evaluates to 0, log the values"). Tagged for the console's filter;
// console.warn, so a headless run's stdout (one JSON line per read) stays clean. setLog() swaps the sink.
export let LOG = (tag, values) => console.warn(tag, JSON.stringify(values));
export function setLog(fn) { LOG = fn; }
const FLAT = 1e-9;              // a scan whose tallest delay beats its lowest by less than this (per vote) has no peak
// the PHAT of the sum, scored over the delays: the tallest is the read. share = that score over the slice count (1 when
// every frequency agrees on the one delay).
export function readSum(re, im, st, wt = null) {
  const wr = new Float64Array(NB), wi = new Float64Array(NB);
  for (let b = 0; b < NB; b++) { const m = Math.hypot(re[b], im[b]) || 1; wr[b] = re[b] / m; wi[b] = im[b] / m; }
  if (wt) for (let b = 0; b < NB; b++) { wr[b] *= wt[b]; wi[b] *= wt[b]; }      // a slice the pause already filled votes ~0
  // EVERY DELAY'S SCORE FIRST, THEN THE TALLEST (Jay, 2026-10-22: "setting an initial value to -Infinity is ... never a
  // good idea ... calculate all scores, store them in an array and take the max value at the end"). With a -Infinity
  // seed, a scan of NaNs or a flat one (every vote weighed to 0 by the pause) silently kept index 0, which is the most
  // negative delay: +90 deg. Now such a scan is no read at all, and says so.
  const sc = new Float64Array(TAUS);
  for (let j = 0; j < TAUS; j++) {
    const o = j * NB;
    let score = 0;
    for (let b = 0; b < NB; b++) score += wr[b] * st.cos[o + b] + wi[b] * st.sin[o + b];
    sc[j] = score;
  }
  const votes = wt ? Math.max(wt.reduce((a, v) => a + v, 0), 1e-9) : NB;
  let jb = 0, lo = sc[0];
  for (let j = 1; j < TAUS; j++) { if (sc[j] > sc[jb]) jb = j; if (sc[j] < lo) lo = sc[j]; }
  const best = sc[jb];
  if (!sc.every(Number.isFinite) || best - lo <= FLAT * Math.max(votes, 1)) {
    LOG('[GccPhat] no peak', { finite: sc.every(Number.isFinite), max: best, min: lo, votes: round(votes, 3) });
    return null;
  }
  // ANGLES 1, 2, 3: the peaks of the scan (a delay scoring at least both neighbours), tallest first, each TIE_SEP_DEG or
  // more from the taller ones kept; a peak's width runs out to where the scan falls below half its height
  const cand = [];
  for (let j = 0; j < TAUS; j++) if (!((j > 0 && sc[j] < sc[j - 1]) || (j < TAUS - 1 && sc[j] < sc[j + 1]))) cand.push(j);
  cand.sort((a, b) => sc[b] - sc[a]);
  const pk = [jb];
  for (const j of cand) {
    if (pk.length >= ANGLES) break;
    if (sc[j] > 0 && pk.every((k) => Math.abs(st.deg[j] - st.deg[k]) >= TIE_SEP_DEG)) pk.push(j);
  }
  const angles = pk.map((j) => {
    let a = j, b = j;
    while (a > 0 && sc[a - 1] >= sc[j] / 2) a--;
    while (b < TAUS - 1 && sc[b + 1] >= sc[j] / 2) b++;
    return { deg: round(st.deg[j], 2), tau_ms: round(st.tau[j] * 1000, 4), share: round(sc[j] / votes, 3),
             width: [round(Math.min(st.deg[a], st.deg[b]), 1), round(Math.max(st.deg[a], st.deg[b]), 1)] };
  });
  // the tie: angle 2, when it scores TIE_SHARE of the lock or more (the same peak the tie search found before)
  const second = (pk.length > 1 && best > 0 && sc[pk[1]] >= TIE_SHARE * best) ? angles[1] : null;
  const read = { deg: round(st.deg[jb], 2), tau_ms: round(st.tau[jb] * 1000, 4), share: round(best / votes, 3), second, angles };
  if (read.deg === 0) LOG('[GccPhat] zero', { j: jb, tau_ms: read.tau_ms, score: round(best, 4), share: read.share,
    min: round(lo, 4), mean: round(sc.reduce((a, v) => a + v, 0) / TAUS, 4), votes: round(votes, 3), width: angles[0].width,
    next: angles[1] ? { deg: angles[1].deg, share: angles[1].share } : null });
  return read;
}
export function createStream(baselineM, { readFrom = null } = {}) {
  if (!FFT_T) FFT_T = fftTables(NFFT);
  const st = steerOf(baselineM), need = Math.round(LOCK_S * SR), firstN = Math.round(FIRST_MS * SR / 1000);
  const w = { lr: new Float64Array(NFFT), li: new Float64Array(NFFT), rr: new Float64Array(NFFT), ri: new Float64Array(NFFT) };
  const re = new Float64Array(NB), im = new Float64Array(NB), pw = new Float64Array(NB);
  let L = new Int16Array(24000), R = new Int16Array(24000), len = 0, firstSample = null, from = null;
  let next = 0, frames = 0, read = null, locked = false, lastVote = 0, onsetVoted = false;
  let nz;                         // the pause's power per slice: undefined until measured, null when there is no pause
  const pauseN = Math.round(PAUSE_MS * SR / 1000);
  const out = { positions: [], first: null, votes: [], ms: 0, settling: false };
  const begin = (s) => { from = s; next = s; frames = 0; read = null; locked = false; onsetVoted = false; re.fill(0); im.fill(0); pw.fill(0); nz = undefined; out.first = null; out.positions = []; out.settling = false; };
  // every frame that has arrived and fits inside the half second goes into the sum; the read is renewed once per push
  // the pause: frames centred in the PAUSE_MS before the onset (the read start + one step), averaged per slice
  const pause = () => {
    const a = from + HOP - pauseN - NFFT / 2, b = from + HOP + NFFT / 2;
    if (a < 0) return null;
    if (b > len) return undefined;
    const nre = new Float64Array(NB), nim = new Float64Array(NB), npw = new Float64Array(NB);
    let k = 0;
    for (let s0 = a; s0 + NFFT <= b; s0 += HOP) { addFrame(L, R, s0, nre, nim, w, npw); k++; }
    for (let i = 0; i < NB; i++) npw[i] /= Math.max(k, 1);
    return npw;
  };
  const weights = () => nz ? Float64Array.from(nz, (n, b) => Math.max(0, Math.min(1, 1 - n / Math.max(pw[b] / frames, 1e-30)))) : null;
  const advance = () => {
    let added = false;
    if (nz === undefined) nz = pause();
    while (!locked && next + NFFT <= len && next - from < need) { addFrame(L, R, next, re, im, w, pw); next += HOP; frames++; added = true; }
    if (next - from >= need) locked = true;                     // the next frame would start past the half second
    if (added && (locked || next - HOP + NFFT - from >= firstN)) read = readSum(re, im, st, weights());
    out.settling = !!read && !locked;
    if (locked && read && !out.first) out.first = { deg: read.deg, tau_ms: read.tau_ms };
  };
  const positions = () => {
    if (!read) return [];
    const ms = Math.floor(len / 48), a = read.angles;
    const p = [{ id: 1, deg: read.deg, tau_ms: read.tau_ms, hits: read.share * 500, first_ms: 0, last_ms: ms, standing_ms: ms, reflection_standing_ms: null, frames, locked, width: a[0].width }];
    // angles 2 and 3 at the lock, as positions of their own; angle 2 is also the tie when it scores TIE_SHARE of the lock
    if (locked) for (let i = 1; i < a.length; i++)
      p.push({ id: i + 1, deg: a[i].deg, tau_ms: a[i].tau_ms, hits: a[i].share * 500, first_ms: 0, last_ms: ms, standing_ms: ms,
               reflection_standing_ms: null, lag_ms: null, width: a[i].width, ...(i === 1 && read.second ? { tie: true } : {}) });
    return p;
  };
  return {
    push(l, r, startSample = null) {
      if (startSample !== null && firstSample === null) firstSample = startSample;
      if (from === null) begin(readFrom !== null && firstSample !== null ? Math.max(0, readFrom - firstSample) : 0);
      if (len + l.length > L.length) {
        const cap = Math.max(len + l.length, L.length * 2), nl = new Int16Array(cap), nr = new Int16Array(cap);
        nl.set(L.subarray(0, len)); nr.set(R.subarray(0, len)); L = nl; R = nr;
      }
      L.set(l, len); R.set(r, len); len += l.length;
      out.votes = []; out.ms = Math.floor(len / 48);
      advance();
      out.positions = positions();
      // FIRST VOTE = THE ONSET (2026-10-21, FiveMsAmplitude as the range; Jay: "Make the change for Range"): a range that
      // keeps only the first vote of a position reads the 5 ms from the onset (the read start + one step), at the locked delay.
      if (locked && read && !onsetVoted) { onsetVoted = true; out.votes.push({ id: 1, start: from + HOP, tau_ms: read.tau_ms }); }
      if (locked && read && len - lastVote >= WIN) { lastVote = len; out.votes.push({ id: 1, start: len - WIN, tau_ms: read.tau_ms }); }
      return out;
    },
    window(start) { return start >= 0 && start + WIN <= len ? { L: L.subarray(start, start + WIN), R: R.subarray(start, start + WIN) } : null; },
    at(n) { return n <= len ? { L: L.subarray(0, n), R: R.subarray(0, n) } : null; },
    // THE GATE NAMES THE ONSET LATER (the session's first utterance opens provisionally at sample 0): the sum starts again
    // from the read start it names, and takes in at once whatever of the half second is already here.
    restart(atSample) {
      const s = atSample - (firstSample ?? 0);
      if (s < 0 || s > len) return false;
      begin(s); lastVote = len;
      advance();
      out.positions = positions();
      return true;
    },
  };
}
