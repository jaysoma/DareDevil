/*
 * RotationTracker -- Stage-1 position, and the chevron driven by Jay's acoustic rotation tracker.
 *
 * THE SCHEME IS THE ADAPTER; THE ALGORITHM IS HIS, BELOW, VERBATIM. The only edits to it are the
 * dropped `export` keyword (the RangeMath loader wraps each file in a closure and returns its FIRST
 * class, so RangeScheme has to be declared first and nothing may be a module) and nothing else:
 * the bands, cueScale, the smoothing constants and the branch resolver are exactly as he froze them.
 * His note stands -- for a holdout run, DO NOT retune cueScale or the bands.
 *
 * WHAT IT NEEDS. `static needsMel` makes the page fetch /voicemel for the tape and attach the 80-bin
 * log-mel to every frame inside an utterance, which is the same filterbank CAM++ consumes
 * (geonar/voicemel.py, 10 ms hop). A tape without one says so in the header rather than drawing a
 * silent zero.
 *
 * HOW IT IS SEEDED. The tape's enrolment utterances -- the opening few seconds voiceopen froze its
 * voiceprint on -- are taken as FACING THE PHONE, and their mel frames become calibrateFacing()'s
 * reference. The angle is seeded to 0 at the same moment. That is the one assumption, it is the same
 * one the opening-distance rule makes, and it is stated in the readout. Everything after is the
 * tracker's own: |sin(theta)| from the lateral cue, four branches, continuity and angular velocity
 * choosing between them.
 *
 * POSITION IS STAGE 1, UNTOUCHED. The radius is the steered 5 ms onset amplitude over open_m, exactly
 * as Wavefront draws it -- rotation must not move the dot, which is the whole reason Stage 1 greys
 * out and hands over. The voice cosine still tints the disc. Three channels, one each.
 */
class RangeScheme {
  static label = "RotationTracker: Stage-1 position, chevron from the acoustic rotation tracker";
  static current = true;
  static needsMel = true;
  static anchorsNeeded = 0;
  static anchors = null;
  static solved = null;
  static fault = null;
  static captured = [null];

  static BOOT_S = 0.5;               // the bearing decision window
  static R_NEAR = 1.0;
  static R_FAR = 8.0;
  static AMP_MAX = 2.5;
  static RAY_NEAR = 1.0;
  static RAY_FAR = 8.0;

  constructor(id) { this.id = id; this.reset(); }
  reset() {
    this.last = null;
    this.curIdx = null;
    this.pos = null;
    this.cur = null;
    this.cos = null;
    this.rot = new RotationTracker({ initialAngleDeg: null });
    this.calFrames = [];             // mel of the enrolment utterances: the facing reference
    this.calibrated = false;
    this.faceDeg = null;
    this.offAxis = null;
    this.conf = 0;
  }
  static _median(v) {
    const s = v.slice().sort(function (a, b) { return a - b; });
    const m = s.length >> 1;
    return s.length % 2 ? s[m] : 0.5 * (s[m - 1] + s[m]);
  }
  static _wrap(d) { return ((d + 180) % 360 + 360) % 360 - 180; }

  /* units to metres by the law and the assumed opening -- see Wavefront._metres */
  static _metres(amp, f) {
    const R = RangeScheme;
    const om = (f && typeof f.open_m === "number" && f.open_m > 0) ? f.open_m : null;
    if (om !== null && amp > 0) return Math.max(R.RAY_NEAR, Math.min(R.RAY_FAR, om / amp));
    return R.RAY_FAR - (R.RAY_FAR - R.RAY_NEAR) * (amp / R.AMP_MAX);
  }

  estimate(f) {
    const R = RangeScheme, t = f.track;
    if (!t) return this.last;
    const oi = t.onset_idx;
    if (oi === null || oi === undefined) return this.last;
    if (oi !== this.curIdx) {
      this.curIdx = oi;
      this.cur = { t0: f.t, degs: [], lvl: [], locked: false, ranged: false };
      this.pos = null;
    }
    const c = this.cur, d = t.deg;
    if (!c.locked && typeof d === "number" && isFinite(d)) c.degs.push(d);
    if (typeof t.voice_open === "number" && isFinite(t.voice_open)) this.cos = t.voice_open;

    if (!c.locked) {
      const amps = f.ray_amp, pots = f.pots;
      if (amps && amps.length && pots && pots.length) {
        let bestAmp = null;
        for (let pi = 0; pi < pots.length; pi++) {
          let a2 = null, bd2 = 1e9;
          for (let i = 0; i < amps.length; i++) {
            const dd2 = Math.abs(R._wrap(amps[i][0] - pots[pi].deg));
            if (dd2 < bd2) { bd2 = dd2; a2 = amps[i][1]; }
          }
          if (bd2 <= 8 && a2 !== null && (bestAmp === null || a2 > bestAmp)) bestAmp = a2;
        }
        if (bestAmp !== null) c.lvl.push(bestAmp);
      }
      if ((f.t - c.t0) >= R.BOOT_S && c.degs.length) { c.locked = true; this.pos = { deg: R._median(c.degs) }; }
    }
    if (this.last === null) this.last = 0.5 * (R.R_NEAR + R.R_FAR);
    if (!c.ranged && c.lvl.length) {
      const settled = c.locked;
      const amp = settled ? R._median(c.lvl) : c.lvl[c.lvl.length - 1];
      const r = R._metres(amp, f);
      if (isFinite(r) && r > 0) { this.last = r; if (settled) c.ranged = true; }
    }
    return this.last;
  }

  bearing(f) { return this.pos ? this.pos.deg : null; }
  facing(f) { return null; }

  /* THE CHEVRON. The enrolment utterances build the facing reference and seed 0; everything after
   * is fed to the tracker frame by frame. 0 = facing the phone, and because the tracker resolves
   * the branch by continuity this is a FULL 0-360 bearing, not the magnitude the band-ratio cue
   * could give on its own. */
  facingDeg(f) {
    const t = f.track;
    if (!t) return this.faceDeg;
    const speech = t.onset_idx !== null && t.onset_idx !== undefined;
    const mel = f.mel;

    if (!this.calibrated) {
      if (speech && mel && t.voice_open_enrolled) { this.calFrames.push(mel); return this.faceDeg; }
      // the first non-enrolled speech closes the calibration: reference from the opening, angle 0
      if (speech && this.calFrames.length >= 8) {
        try {
          this.rot.calibrateFacing(this.calFrames);
          this.rot.seedAngle(0);
          this.calibrated = true;
          this.calFrames = [];
        } catch (e) { this.calFrames = []; return this.faceDeg; }
      } else if (speech && mel && !t.voice_open_enrolled) {
        this.calFrames.push(mel);     // no enrolment on this tape: the opening stands in
        return this.faceDeg;
      } else {
        return this.faceDeg;
      }
    }
    const r = this.rot.update(mel || null, f.t, !!(speech && mel));
    if (r && typeof r.orientationDeg === "number") this.faceDeg = r.orientationDeg;
    this.offAxis = r ? r.offAxisDeg : null;
    this.conf = r ? r.confidence : 0;
    return this.faceDeg;
  }

  rays(f) {
    const R = RangeScheme, p = f.pots, amps = f.ray_amp;
    if (!p || !p.length) return null;
    return p.map(function (q) {
      let a = null;
      if (amps && amps.length) {
        let bd = 1e9;
        for (let i = 0; i < amps.length; i++) {
          const dd = Math.abs(R._wrap(amps[i][0] - q.deg));
          if (dd < bd) { bd = dd; a = amps[i][1]; }
        }
        if (bd > 8) a = null;
      }
      const u = (a === null) ? 0 : Math.max(0, Math.min(1, a / R.AMP_MAX));
      return {
        deg: q.deg,
        r: (a === null) ? R.RAY_FAR : (R.RAY_FAR - (R.RAY_FAR - R.RAY_NEAR) * (a / R.AMP_MAX)),
        e: a, w: 0.25 + 0.75 * u,
        tag: q.deg.toFixed(0) + "°"
      };
    });
  }
  acousticMode(f) {
    const t = f && f.track;
    if (!t || t.onset_idx === null || t.onset_idx === undefined) return this.last === null ? "silent" : "held";
    if (!this.cur) return "silent";
    return this.cur.locked ? "held" : "acquiring";
  }
}


// ============================================================================================
// Jay's RotationTracker, verbatim apart from the dropped `export`.
//
// Dependency-free, experimental Stage-2 acoustic rotation tracker.
//
// Input: 80-bin CAM++ log-mel frame (~10 ms/frame).
// Output: orientationDeg (0..360), plus debug values.
//
// IMPORTANT:
// - The spectral observable is bilateral: by itself it estimates |sin(theta)|.
// - Identity continuity supplies the branch over time.
// - For the first test, seed the tracker with a known orientation and a
//   "facing phone" log-mel reference.
// - This is intentionally simple math, not a trained model.
// ============================================================================================

class RotationTracker {
  constructor({
    initialAngleDeg = null,
    windowFrames = 80,          // ~0.8 s at 10 ms hop
    minFrames = 24,
    fricativeFraction = 0.25,   // select brightest quarter of active frames
    energyKeepFraction = 0.70,  // discard quietest 30%
    cueScale = 0.714,           // current 3-run fit: |sin(theta)| ~= 0.714 * deltaCue
    angleSmoothing = 0.28,
    omegaSmoothing = 0.18,
    maxOmegaDegPerSec = 220
  } = {}) {
    this.windowFrames = windowFrames;
    this.minFrames = minFrames;
    this.fricativeFraction = fricativeFraction;
    this.energyKeepFraction = energyKeepFraction;
    this.cueScale = cueScale;
    this.angleSmoothing = angleSmoothing;
    this.omegaSmoothing = omegaSmoothing;
    this.maxOmega = maxOmegaDegPerSec;

    this.frames = [];
    this.reference = null;      // normalized 80-bin facing profile
    this.referenceCue = null;

    this.angle = initialAngleDeg == null ? null : wrap360(initialAngleDeg);
    this.omega = 0;
    this.lastT = null;
  }

  // Seed/reseed the continuity branch. 0 = facing phone, 90 = right/left side,
  // 180 = facing away, etc.
  seedAngle(angleDeg) {
    this.angle = wrap360(angleDeg);
    this.omega = 0;
  }

  // Supply a known-facing reference.
  // Accepts either one 80-bin vector or an array of 80-bin frames.
  calibrateFacing(melOrFrames) {
    const frames = Array.isArray(melOrFrames[0]) || melOrFrames[0] instanceof Float32Array
      ? melOrFrames
      : [melOrFrames];

    const p = robustProfile(frames, this.energyKeepFraction, this.fricativeFraction);
    if (!p) throw new Error("Not enough valid frames for facing calibration.");

    this.reference = normalizeShape(p);
    this.referenceCue = lateralCue(this.reference);
    return {
      referenceCue: this.referenceCue
    };
  }

  resetWindow() {
    this.frames.length = 0;
  }

  // mel80: CAM++ 80-bin log-mel frame
  // tSec: timestamp in seconds
  // speechActive: false means hold/propagate state without ingesting spectrum
  update(mel80, tSec, speechActive = true) {
    if (speechActive && mel80) {
      if (mel80.length !== 80) throw new Error(`Expected 80 mel bins, got ${mel80.length}`);
      this.frames.push(Array.from(mel80));
      if (this.frames.length > this.windowFrames) this.frames.shift();
    }

    const dt = this.lastT == null ? 0 : Math.max(0, Math.min(0.25, tSec - this.lastT));
    this.lastT = tSec;

    // No acoustic update: coast briefly on continuity.
    if (!speechActive || this.frames.length < this.minFrames || !this.reference) {
      if (this.angle != null && dt > 0) {
        this.angle = wrap360(this.angle + this.omega * dt);
        this.omega *= 0.96;
      }
      return this._result(null, null, 0);
    }

    const p = robustProfile(this.frames, this.energyKeepFraction, this.fricativeFraction);
    if (!p) return this._result(null, null, 0);

    const shape = normalizeShape(p);

    // The 3 controlled runs gave the most repeatable lateral cue around:
    //   mel 25..34 versus mel 50..69
    //
    // We work relative to the same speaker's facing reference.
    const cue = lateralCue(shape);
    const deltaCue = cue - this.referenceCue;

    // Candidate empirical mapping frozen for holdout testing.
    // It is intentionally clipped because the acoustic cue saturates.
    const sinAbs = clamp(this.cueScale * deltaCue, 0, 1);
    const phi = Math.asin(sinAbs) * 180 / Math.PI; // 0..90

    // Spectral magnitude cannot tell these four branches apart by itself:
    // theta, 180-theta, 180+theta, 360-theta.
    const candidates = uniqueAngles([
      phi,
      180 - phi,
      180 + phi,
      360 - phi
    ]);

    let chosen = null;

    if (this.angle == null) {
      // We know off-axis magnitude, but not the signed branch.
      return this._result(phi, deltaCue, this._confidence());
    }

    const predicted = wrap360(this.angle + this.omega * dt);

    // Continuity is the branch resolver.
    // A small velocity-consistency term prevents branch-flipping near 0/90/180.
    let bestCost = Infinity;
    for (const c of candidates) {
      const posErr = circularDiffDeg(c, predicted);
      const impliedOmega = dt > 1e-4
        ? clamp(circularDiffDeg(c, this.angle) / dt, -this.maxOmega, this.maxOmega)
        : this.omega;
      const velErr = impliedOmega - this.omega;

      const cost = posErr * posErr + 0.015 * velErr * velErr;
      if (cost < bestCost) {
        bestCost = cost;
        chosen = c;
      }
    }

    // Circular smoothing.
    const step = circularDiffDeg(chosen, this.angle);
    const oldAngle = this.angle;
    this.angle = wrap360(this.angle + this.angleSmoothing * step);

    if (dt > 1e-4) {
      const measuredOmega = clamp(
        circularDiffDeg(this.angle, oldAngle) / dt,
        -this.maxOmega,
        this.maxOmega
      );
      this.omega =
        (1 - this.omegaSmoothing) * this.omega +
        this.omegaSmoothing * measuredOmega;
    }

    return this._result(phi, deltaCue, this._confidence());
  }

  _confidence() {
    const n = Math.min(1, this.frames.length / this.windowFrames);
    return clamp(n, 0, 1);
  }

  _result(offAxisDeg, deltaCue, confidence) {
    return {
      orientationDeg: this.angle,
      offAxisDeg,             // 0..90 acoustic magnitude before branch resolution
      deltaCue,
      angularVelocityDegPerSec: this.omega,
      confidence
    };
  }
}


// ---------- DSP helpers ----------

// Empirically strongest simple lateral contrast in the current three runs.
function lateralCue(mel80) {
  return meanRange(mel80, 25, 35) - meanRange(mel80, 50, 70);
}

function normalizeShape(v) {
  const m = meanRange(v, 0, v.length);
  return Array.from(v, x => x - m);   // remove broadband level / range-ish gain
}

// Mirrors the exploratory analysis:
// 1) discard quietest frames,
// 2) among active frames select the most fricative/bright subset,
// 3) average their log-mel spectra.
function robustProfile(frames, energyKeepFraction, fricativeFraction) {
  if (!frames || frames.length === 0) return null;

  const good = frames.filter(f => f && f.length === 80 && Array.prototype.every.call(f, Number.isFinite));
  if (good.length === 0) return null;

  const withStats = good.map(f => ({
    f,
    energy: meanRange(f, 0, 80),
    brightness: meanRange(f, 45, 80) - meanRange(f, 0, 30)
  }));

  // Keep upper energy fraction.
  withStats.sort((a, b) => a.energy - b.energy);
  const energyStart = Math.max(
    0,
    Math.floor(withStats.length * (1 - energyKeepFraction))
  );
  const active = withStats.slice(energyStart);
  if (active.length === 0) return null;

  // Fricative-heavy frames are especially informative for orientation.
  active.sort((a, b) => b.brightness - a.brightness);
  const k = Math.max(4, Math.round(active.length * fricativeFraction));
  const selected = active.slice(0, Math.min(k, active.length));

  const out = new Array(80).fill(0);
  for (const x of selected) {
    for (let i = 0; i < 80; i++) out[i] += x.f[i];
  }
  for (let i = 0; i < 80; i++) out[i] /= selected.length;
  return out;
}

function meanRange(a, start, end) {
  let s = 0;
  for (let i = start; i < end; i++) s += a[i];
  return s / Math.max(1, end - start);
}

function clamp(x, lo, hi) {
  return Math.max(lo, Math.min(hi, x));
}

function wrap360(x) {
  x %= 360;
  return x < 0 ? x + 360 : x;
}

// Signed shortest difference target-current in [-180, 180).
function circularDiffDeg(target, current) {
  let d = wrap360(target) - wrap360(current);
  if (d >= 180) d -= 360;
  if (d < -180) d += 360;
  return d;
}

function uniqueAngles(values) {
  const out = [];
  for (const v of values) {
    const w = wrap360(v);
    if (!out.some(x => Math.abs(circularDiffDeg(x, w)) < 1e-6)) out.push(w);
  }
  return out;
}
