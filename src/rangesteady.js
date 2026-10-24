/*
 * rangesteady.js -- RANGE MADE EVENT-DRIVEN, as a wrapper around ANY RangeMath scheme.
 *
 * Jay, 2026-09-26: "A lot of the heavy lifting is already done by teams of researchers sitting in
 * labs... I just piggy back onto the stabilized bearing. Instead of our renderer passing in the running
 * streaming audio, we only invoke range when bearing changes." And: "RangeMath is invoked FROM
 * RangeSteady. That's how we should do it."
 *
 * So this is a POLICY, not a scheme, and it lives outside RangeMath/ (that folder is the registry).
 * steady(Inner) returns a class with the scheme contract -- constructor(id), estimate(f), facing(f),
 * acousticMode(f), the statics the page sets -- whose estimate is the INNER scheme's law read at
 * events and HELD in between. The inner scheme runs on every frame exactly as before (its own
 * calibration, its own state); what changes is which level it is asked to convert, and when.
 *
 * WHY. Bearing is a time-difference measurement and loudness cancels out of it, which is why it froze
 * solid once the beam was gated and denoised. Range is built on loudness, and loudness breathes with
 * every syllable: measured standing still at one stop, the level over a 0.75 s window has a standard
 * deviation of 2-3 dB (walk-211959) to 4-7 dB (walk-165255), on the raw beam as much as the denoised
 * one, and at the fourth power 1 dB is 6% of range. A streaming estimate therefore draws the syllables
 * however it is smoothed. Distance cannot change inside an utterance while the bearing holds, so:
 *
 *   HOLD, and re-read only on an event that says he moved --
 *     a new turn      the gate reopened after a pause (the diarizer's minDurationOff, 0.5 s), or
 *                     DareDevil gave him a new id: a fresh utterance, one fresh reading
 *     a bearing move  the stabilised bearing left where it was at the last reading (> 6 deg; it is
 *                     steady to about 3)
 *   Each reading converts the WHOLE utterance so far: the MEDIAN of the inner scheme's own windowed
 *   power over it -- the statistic its calibration was taken on, so a reading and the anchor are
 *   measured the same way. (The first cut read the 75th percentile of hop levels, which sits 2-9 dB
 *   above a median-of-windows calibration on every stop: x0.6-x0.9 nearer than truth, always.) A
 *   reading waits for half a second of the utterance and holds the previous value meanwhile, then
 *   steps in at walking speed.
 *   A sustained level shift with no bearing change (the walk straight out from the phone) is the
 *   next event to add.
 *
 * THE INNER CONTRACT. During its calibration (static `offset` still null, for schemes that have one)
 * the inner's own estimate is passed straight through, so its anchoring runs untouched. After that a
 * scheme exposing power(f) and metres(P) -- "the power you calibrate on" and "metres for a power under
 * my calibration" -- gets the utterance's median power converted by its own law; a scheme without
 * them is still held and re-read at the same events, just from its own estimate at that moment.
 *
 * Page: ?scheme=presenter&steady=1 wraps Presenter; drop the flag for the raw stream, side by side.
 */
(function (root) {
  "use strict";

  function steady(Inner) {
    class Steady {
      constructor(id) {
        this.id = id;
        this.inner = new Inner(id);
        this.vmax = 1.5;             // metres per second a person walks: the step limit between readings
        this.turnGapS = 0.5;         // a pause this long ends an utterance
        this.readAfterS = 0.5;       // an utterance is read once this much of it is in
        this.moveDeg = 6.0;          // a bearing change past this is a move
        this.minAct = 0.30;          // frames below this activity do not count as speech
        this.reset();
      }

      reset() {
        if (this.inner.reset) this.inner.reset();
        this.last = null;            // what is held
        this.tPrev = null;           // last frame with speech on it
        this.readT = null;           // when the range was last re-read
        this.uttT0 = null;           // when the current utterance began
        this.uttP = [];              // the inner's windowed power, every frame of it so far
        this.pending = false;        // an utterance whose reading is still owed
        this.degRead = null;         // the bearing at the last reading
        this.oiRead = null;          // the gate open the current turn belongs to
      }

      _calibrating() {
        return (Inner.offset === null);            // undefined (no such static) reads as "not"
      }

      estimate(f) {
        const t = f.track;
        const r = this.inner.estimate(f);            // the inner runs every frame, as it always did
        if (this._calibrating()) {
          // pass-through: the scheme is still learning its scale, and the dot is where it says
          this.last = r;
          this.tPrev = f.t;
          if (typeof t.deg === "number") this.degRead = t.deg;
          return r;
        }
        // THE GATE EVENT IS THE AUTHORITY (Jay, 2026-09-30: "Bearing and range are calculated on gate
        // events, not speech decode events"; fixed here 2026-10-05). This read `level > 0 && talking &&
        // activity >= 0.3`. `talking` is a decode product, `level` is the DFN beam's, and on a sim the
        // tracker holds a source on only 7.5-20% of hops, so 85-92% of frames are pot-lane tracks with
        // level null and activity 0 -- every one of them took the hold branch, and the range froze at
        // its first value for most of every sim tape. onset_idx is stamped on every frame of an
        // utterance from the gate itself, which is what Playback.html already draws on.
        const speaking = (t.onset_idx !== null && t.onset_idx !== undefined);
        if (!speaking) return (this.last === null) ? r : this.last;          // held, not withheld

        const moved = (this.degRead !== null && typeof t.deg === "number" && Math.abs(t.deg - this.degRead) > this.moveDeg);
        const reopened = (t.onset_idx !== this.oiRead);                       // a new gate open is a new turn
        this.oiRead = t.onset_idx;
        if (this.tPrev === null || f.t - this.tPrev > this.turnGapS || this.uttT0 === null || reopened) {
          this.uttT0 = f.t; this.uttP = []; this.pending = true;              // a new turn
        } else if (moved) {
          // A MOVE OPENS FRESH EVIDENCE, it does not take a reading. The levels before it were
          // measured somewhere else; and a bearing that is still drifting keeps re-opening, so the
          // reading lands only once the bearing has HELD for readAfterS -- piggybacking on the
          // stabilised bearing, literally. A bearing that only wobbles inside moveDeg opens nothing.
          this.uttT0 = f.t; this.uttP = []; this.pending = true;
          this.degRead = t.deg;
        }
        if (typeof this.inner.power === "function") { const P = this.inner.power(f); if (P !== null && P > 0) this.uttP.push(P); }
        const ripe = (f.t - this.uttT0 >= this.readAfterS) && (typeof this.inner.power !== "function" || this.uttP.length >= 8);
        if (!ripe || !this.pending) { this.tPrev = f.t; return (this.last === null) ? r : this.last; }

        // A READING: the inner's law on the utterance's median windowed power, or its own estimate if it exposes neither
        let raw = null;
        if (typeof this.inner.metres === "function" && this.uttP.length) {
          // the scheme may define how an utterance's powers become one number (Relative: the active
          // speech level, whole speech); otherwise the median, the statistic Presenter calibrates on
          let P;
          if (typeof this.inner.utterance === "function") P = this.inner.utterance(this.uttP);
          else { const v = this.uttP.slice().sort((x, y) => x - y); P = v[v.length >> 1]; }
          raw = (P !== null && P > 0) ? this.inner.metres(P) : null;
        } else {
          raw = r;
        }
        this.tPrev = f.t;
        if (!(typeof raw === "number" && isFinite(raw) && raw > 0)) return (this.last === null) ? r : this.last;
        this.pending = false;
        if (typeof t.deg === "number") this.degRead = t.deg;
        // step in at walking speed; dt is the time since the last reading, so a long pause is free to move him far
        if (this.last === null || this.readT === null) {
          this.last = raw;
        } else {
          const step = this.vmax * Math.max(0, f.t - this.readT);
          const diff = raw - this.last;
          this.last = (Math.abs(diff) <= step) ? raw : this.last + (diff > 0 ? step : -step);
        }
        this.readT = f.t;
        return this.last;
      }

      facing(f) { return this.inner.facing ? this.inner.facing(f) : null; }
      // EVERY ANSWER THE INNER GIVES PASSES THROUGH (2026-09-30). This wrapper is on by default and
      // used to expose only estimate/facing/acousticMode, so anything a scheme added later --
      // the held bearing, the Stage-1 candidate rays, the facing magnitude for the chevron --
      // silently vanished whenever +steady was on, which is always. The chevron drew nothing for
      // exactly this reason. Steadying is about the RANGE; nothing else the scheme says is changed.
      bearing(f) { return (typeof this.inner.bearing === "function") ? this.inner.bearing(f) : null; }
      rays(f) { return (typeof this.inner.rays === "function") ? this.inner.rays(f) : null; }
      facingDeg(f) { return (typeof this.inner.facingDeg === "function") ? this.inner.facingDeg(f) : null; }

      acousticMode(f) {
        if (this.last === null) return this.inner.acousticMode ? this.inner.acousticMode(f) : "acquiring";
        const t = f.track;
        if (this.inner.farM && this.last > this.inner.farM) return "beyond";
        return (t.talking && t.level > 0) ? "direct" : "silent";
      }
    }
    // the statics the page and the bench set on a scheme go to the inner, which is what reads them
    Steady.Inner = Inner;
    Steady.label = (Inner.label || Inner.name) + " [steady]";
    for (const k of ["anchors", "anchorsNeeded", "offset", "solved", "fault", "captured"]) {
      if (Inner[k] === undefined) continue;
      Object.defineProperty(Steady, k, { get() { return Inner[k]; }, set(v) { Inner[k] = v; }, configurable: true });
    }
    return Steady;
  }

  if (typeof module !== "undefined" && module.exports) module.exports = { steady };
  root.steady = steady;
})(typeof window !== "undefined" ? window : globalThis);
