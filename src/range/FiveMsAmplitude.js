/*
 * FiveMsAmplitude -- RANGE AS 1 / THE AMPLITUDE OF EACH POSITION'S OWN FIRST 5 ms. NO ANCHOR.
 *
 * Jay, 2026-10-12: "Take off the anchor ... Remove anchor from calculation. Just use Amplitude as a ratio of screen
 * size" -- and, asked which amplitude: "Position's own 5 ms": the loudness of the 5 ms window that found each position,
 * the same block Angle reads its angle from. One window, no averaging, no anchor; each reflection its own length.
 *
 * WHY. CdrRange made the tape's opening utterance 1.000 u and set its distance law from it. On walk-205606 the opening
 * was the Siri ding at 0.2 s -- the phone's own speaker -- so every word after it read 7.5-10 u and drew off the screen,
 * past where shift+wheel could reach. Nothing here compares one reading with another.
 *
 * THE READ is ArrivalRange's, unchanged: the power of L + R with R turned by the position's own delay (exact, per bin),
 * 300 Hz-8 kHz, over the 5 ms window of the position's FIRST vote -- the window that found it. Later votes are not
 * read. amplitude = sqrt(2 P) (P is one-sided), and the answer is 1 / amplitude: louder is nearer, the free-field 1/r
 * law, no slope, no clamp. It is neither metres nor opening units: Render draws it as a share of the screen
 * (SCREEN_RANGES there), and shift+wheel is its only calibration.
 *
 * A range scheme is loaded as plain source and may import nothing, so power() is ArrivalRange's, copied.
 */
class RangeScheme {
  static label = "FiveMsAmplitude: 1 / amplitude of each position's own first 5 ms, no anchor";
  static outputUnit = "screen";
  static BAND_LO_HZ = 300;
  static BAND_HI_HZ = 8000;

  constructor() { this.reset(); }

  reset() {
    this.onset = new Map();          // utt -> Map(id -> amplitude over that position's first 5 ms)
  }

  /* Power of L + R shifted by tauMs (exact, per bin) over the band, from one raw window. ArrivalRange.power. */
  static power(p, tauMs) {
    if (!p || !p.L || !p.R || !p.L.length) return null;
    const sr = p.sr || 48000, n = p.L.length, tau = tauMs / 1000, scale = 1 / 32768;
    const k0 = Math.max(1, Math.ceil(RangeScheme.BAND_LO_HZ * n / sr)), k1 = Math.min((n >> 1) - 1, Math.floor(RangeScheme.BAND_HI_HZ * n / sr));
    if (k1 < k0) return null;
    let ml = 0, mr = 0;
    for (let i = 0; i < n; i++) { ml += p.L[i]; mr += p.R[i]; }
    ml /= n; mr /= n;
    let P = 0;
    for (let k = k0; k <= k1; k++) {
      let lr = 0, li = 0, rr = 0, ri = 0;
      const w = 2 * Math.PI * k / n;
      for (let i = 0; i < n; i++) {
        const c = Math.cos(w * i), s = Math.sin(w * i), l = (p.L[i] - ml) * scale, r = (p.R[i] - mr) * scale;
        lr += l * c; li -= l * s; rr += r * c; ri -= r * s;
      }
      const a = -2 * Math.PI * (k * sr / n) * tau, c = Math.cos(a), s = Math.sin(a);
      const xr = rr * c - ri * s, xi = rr * s + ri * c;                 // R(f) rotated by the position's delay
      const br = 0.5 * (lr + xr), bi = 0.5 * (li + xi);
      P += (br * br + bi * bi) / (n * n);
    }
    return P;
  }

  /* A position's first vote is the window that found it; later votes are not read. */
  vote(utt, id, p, tauMs) {
    let m = this.onset.get(utt);
    if (!m) { m = new Map(); this.onset.set(utt, m); }
    if (m.has(id)) return;
    const P = RangeScheme.power(p, tauMs);
    if (P === null) return;
    m.set(id, Math.sqrt(2 * P));
  }

  direct(_utt, _id) {}               // every position has its own length; nothing to note

  forget(utt) { this.onset.delete(utt); }

  estimate(_f) { return null; }      // not frame-driven: the pass hands CDR frames to every range; this reads none

  unitsOf(utt, id) {
    const m = this.onset.get(utt), a = m ? m.get(id) : undefined;
    return a > 0 ? 1 / a : null;
  }
}
