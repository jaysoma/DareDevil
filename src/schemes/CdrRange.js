/*
 * CdrRange -- GCC-PHAT bearing over the first 0.5 s, range from the COHERENT-TO-DIFFUSE RATIO in units
 * of the tape's opening utterance. Measured once per utterance and held.
 *
 * Jay, 2026-10-05: "We can certainly try CDR as the range cue since what we have seems to have not
 * worked." What we had was the steered 5 ms onset (Wavefront, potamp's ray_amp). Scored per utterance
 * on 38 simulated rooms against exact truth (geonar/utt_measure.py), as the share of utterance pairs
 * put in the right order (50% = a coin):
 *
 *     cdr 65% (71% facing)    direct level 60-62%    potamp 55-56%    onset d5 55%
 *
 * and on 46 real walk tapes cdr 58%, potamp 51-52%. CDR leads on both, and potamp is at chance on both.
 *
 * WHY CDR SHOULD CARRY DISTANCE. cdr_db is the ratio, per hop, of the sound that reaches the two
 * capsules coherently at the talker's delay (the direct path) to the part that arrives diffusely (the
 * room). The direct part falls as 1/r^2 in power; a room's diffuse field is roughly the same everywhere
 * in it. So the ratio falls with distance and -- the reason it beats a level -- the talker's vocal
 * effort divides out of it: shouting raises both terms. A level cue has to assume he spoke as loudly as
 * he did at the opening; this one does not.
 *
 * UNITS (Jay, 2026-10-05: "measure accuracy based on units first, we'll deal with the conversion
 * later"). The opening utterance's CDR is the reference, 1.000 u by construction. Later utterances are
 *     u = 10 ^ ((cdr_open - cdr) / (20 * SLOPE))
 * SLOPE = 1 is the free-field law (20 dB per decade of distance). The sims say CDR falls less steeply
 * (S = 0.75) but applying it makes the drawn ranges worse -- see the constant. The SLOPE changes how far
 * apart talkers are drawn, never their order.
 *
 * OUTPUT. Opening-distance units, without a metre assumption or clamp. Metre conversion is a
 * separate presentation step; this estimator never reads open_m.
 *
 * THE STATISTIC -- CHANGED 2026-10-05 (Jay: "change the estimator"). Range now reads the DIRECTION-FREE
 * CDR (`cdrf`: per hop, three bands' direct and diffuse powers in dB), summed per band over the first
 * RANGE_S = 0.8 s of the utterance, the ratio taken once per band, and the three bands averaged. On
 * LOCATA's real rooms and talkers that statistic ordered 89% of same-talker 0.8 s window pairs by tracked
 * distance (91% at 2.4 s), against 57-65% for the GCC-steered cdr_db this scheme read until now and 64%
 * for loudness. Steering is what hurt: the direction-free estimator counts early reflections as direct
 * too, and that is what moves with distance. The bearing still locks at BOOT_S = 0.5 s; the range settles
 * at 0.8 s -- live either way, the disc placed at once and corrected once. A fixture with no `cdrf` falls
 * back to the old steered statistic so older tapes still draw.
 */
class RangeScheme {
  static label = "CdrRange: first arrival bearing, first 1 ms per utterance; CDR range in opening units";
  static current = true;
  static outputUnit = "opening";
  // IT HOLDS ITS OWN POSITION (2026-10-05): the dot moves only at this scheme's draws, so the page's
  // rangesteady wrapper -- which re-reads range whenever DareDevil's lane bearing wobbles -- stays off it.
  static selfSteady = true;
  static anchorsNeeded = 0;
  static anchors = null;
  static solved = null;
  static fault = null;
  static captured = [null];

  static BOOT_S = 0.5;               // the bearing's decision window
  static RANGE_S = 0.8;              // the range's single read before the steps (kept for the record; STEPS_S below rules)
  // THE LAW, SET BY THE OPENING (2026-10-05). dB of CDR per 20 dB/decade of distance; 1 = free field.
  // Free field is right where everyone stands 1.5-3.5 m out and too steep over long spans: in the sim
  // halls a talker at 7 m was drawn at ~4. The room's own slope follows the OPENING's CDR (rho +0.72
  // over 37 sim rooms), so the slope is set once, at the opening, from that utterance's own reading:
  //     S = SLOPE_A + SLOPE_B * cdr_open,  clamped to [SLOPE_MIN, SLOPE_MAX]
  // Jay, 2026-10-05: de-prioritise the small rooms. Scored in METRES (what the eye sees), leave-one-room-
  // out: wide-span rooms 1.66 -> 1.18 m median miss, narrow rooms 0.52 -> 0.63 m. Without the clamp the
  // narrow rooms blow up (a slope of 0.19 multiplies their scatter ~5x). Fitted on sims only (one
  // shoebox simulator): check against LOCATA before trusting it in a real room.
  static SLOPE_A = -0.0274;
  static SLOPE_B = 0.1585;
  static SLOPE_MIN = 0.6;
  static SLOPE_MAX = 1.0;
  static SLOPE = 1.0;                // the steered fallback's law, and the free-direction one until the opening
  // THE LAW IS HELD AT -20 (2026-10-23, brief 20). The opener-set slope above was fitted on one shoebox
  // simulator. On LOCATA's real room (160 mm pair, 207 reads after the opener;
  // harness/range_facing/opener_slope_check.py) -20 puts 68% within 1.5x of the true distance ratio and
  // the opener's slope 66%, with more reads off by 2x (26 against 20). Held at -20, the opener only sets
  // the unit; with the opener's slope it also sets the law, so who spoke first would change the shape of
  // the room. The cost: far reads come out too near (the CDR falls about a third as fast as -20), a bit
  // more than with the opener's slope (0.67 against 0.61 doublings on reads 2x+ from the opener).
  // true brings the opener's slope back.
  static SLOPE_FROM_OPENING = false;
  // SAME TALKER, SAME SPOT, READINGS ACCUMULATE (Jay, 2026-10-05: "that's a good thing to add in"). An
  // utterance whose bearing is within POOL_DEG of the pool's and whose own reading is within POOL_DB of
  // the pool's adds its band powers to the pool, and the range is read from all of it -- scatter falls as
  // the talker keeps talking where they stand. A bearing move, or a jump bigger than ~1.6x in distance
  // (4 dB at 20 dB/decade), starts a fresh pool. On the 37 sims (about one utterance per position, so
  // little to pool) it moved pair ordering 70% -> 71%; a talker who stays put is where it pays.
  // POOLING OFF (2026-10-06). It joins a window to the previous pool when both the bearing and the
  // reading are close, and then reads from the pool's accumulated sums. That was rare while bearings
  // scattered. With ODAS's bearing it is steady to ~2 degrees across this whole tape, so all 20
  // windows pool into one accumulation, every new utterance is diluted by everything before it, and
  // the reading asymptotes -- the dot stops moving near the opening's own value. A running window
  // measures the utterance it is in; set this back above 0 only if pooling is wanted again.
  static POOL_DEG = 0.0;   // OFF 2026-10-06: its gate is a bearing match, and ODAS's bearing is steady
                         // to ~2 deg across this whole tape, so every window pools into one
                         // accumulation and the reading freezes at the opening's value (2.0 m).
                         // It only ever worked because the old bearing scattered. 5.0 to restore.
  static POOL_DB = 4.0;
  // WINDOWS, NOT POINTS -- AND THE DOT MOVES ONLY AT STEPS (Jay, 2026-10-05). Until today the range was
  // read from the first RANGE_S of an utterance and the rest of it was ignored, so a talker who walks
  // while talking was ranged once at the gate and never again. The first fix redrew every frame while
  // the window grew and re-locked the bearing at every restart, and it looked frantic. Jay's rule: "keep
  // a window and move the position at 0.5, 1.0, 2.0 etc (only for range) until the utterance ends OR
  // the bearing changes 5 degrees or more."
  //   A window opens at the gate. Band powers are SUMMED over it from its first frame -- a fricative, a
  //   plosive and a vowel are all inside every reading, never one of them standing for it.
  //   The dot moves only at the window's STEPS_S ages. At the first, the bearing locks (GCC, loudest
  //   fifth of the window's first 0.5 s) and the range draws; at each later step only the range
  //   redraws, from everything summed so far. Between steps the dot holds.
  //   After the lock a trailing BOOT_S GCC watches the bearing. A move past MOVE_DEG closes the window
  //   (its band powers stay in the pool) and opens a new one there; the dot holds until that window's
  //   own first step. Scored on geonar/stage1_bench.py (LOCATA, 38 sims, Jay's dot walks).
  // A RUNNING WINDOW, NOT STEPS (Jay, 2026-10-06: "I changed my mind about 0.5,1.0,2.0. Now keep a
  // window running"). One entry left, and it is only the LOCK: the bearing is decided once at BOOT_S
  // and held. After it the range redraws on every frame from everything summed so far, rather than
  // waiting for 1 / 2 / 4 / 8 s -- so the dot settles continuously instead of jumping five times.
  static STEPS_S = [0.5, 1.0, 2.0, 4.0, 8.0];
  // RESTARTS OFF (Jay, 2026-10-05): a bearing-move restart re-locked 2-3x worse than an utterance's first
  // lock on a talker who stood still (sims 8.7-11 vs 3.2 deg, house 8.6-9.6 vs 3.8-5.4) -- the 'mad
  // flitting'. Moving talkers are tabled for Stage 1, so the bearing locks once per utterance and holds;
  // range keeps stepping on it. Infinity disables the watch; a number brings it back.
  // RESTART BACK ON AT 5 DEG (Jay, 2026-10-06): "keep a running window until the end of the utterance
  // or bearing changes more than 5 degrees". The 10-05 measurement that disabled this re-locked with
  // the LOUDEST fifth of dir_deg, which is the strength ranking that picks reflections past the
  // critical distance -- so the 'mad flitting' was the re-lock landing on a mirror image, not the
  // restart being wrong. The watch below now reads ODAS's tracked deg, already smoothed by SST.
  static MOVE_DEG = 5.0;
  // A NEW WINDOW AT EACH VOICE HAND-OVER, AND EVERY 8 S (Jay, 2026-10-05, walk-205043: one window held
  // +26 deg for 53 s across him, Julie and his roommate, because nobody paused for half a second, and
  // Julie was drawn at his reverb's angle). `turn_idx` is stamped by tape_fixture from
  // geonar/seg_turns.py -- segmentation-3.0's own single-voice switches, no embedding. A hand-over
  // opens a fresh window once the current one is MIN_TURN_S old (younger, it merges -- cross-talk is
  // preferred merged). Benched: no cost to single talkers (sims, house, LOCATA unchanged). On
  // walk-205043 Julie gets her own locks (-10 / -8 deg) instead of Jay's +26 deg reverb for 53 s.
  // CAP_S (a fresh window every 8 s of unbroken speech) exists but is OFF -- see its line.
  static MIN_TURN_S = 1.0;
  // RENDER WHAT THE PHONE HEARS (Jay, 2026-10-06). A talker who starts an utterance turned away from the
  // phone is heard loudest by their reflection off the wall they face; turned back, by their direct sound.
  // Neither is a mistake to correct -- it is what the phone hears, and the page draws exactly that:
  //   - the onset's own lock is the MAIN arrival (the dot and the speech bubble);
  //   - when a second arrival is NEAR-IDENTICAL (within TIE_RATIO, at least TIE_SEP away) it is drawn too,
  //     as a GHOST -- a dimmed bubble with the same words at the same range -- and the dot dims;
  //   - at every later range step the interval's dominant arrival is the main. The incumbent holds unless
  //     it is beaten outright (by more than TIE_RATIO), so a near-tie keeps it and names the challenger as
  //     the ghost; a talker who turns back to face the phone swaps the main bubble and the ghost.
  // Jay: "If a speaker stays turned away and in fact turns to face other directions, EXACTLY the same
  // thing. We render where their voice is coming from and ONLY if there's a near-identical reflection,
  // render the secondary bubble." No memory crosses an utterance -- an earlier draft drew a tie at the
  // last clean bearing, which is identity by the back door (it would have put Jay's roommate on Jay).
  // `srp2` is the fixture's two strongest arrivals over the trailing half-second (cdr_direct.srp_top2).
  // No distance is named anywhere: past a room's own far boundary the direct weakens and a reflection
  // holds (walk-205043, Julie backing away: +45 deg 2682 vs +6 deg 2303), so the tie IS the boundary.
  static TIE_RATIO = 1.3;
  static TIE_SEP = 10.0;
  // What a step weighs. "loud": the onset lock's own estimator, run on the interval -- per-hop GCC bearings
  // of its loudest fifth by coherent direct level. "srp": the summed two-arrival SRP. "off": the onset
  // decides the whole window (main and ghost both).
  static STEP_EV = "srp";            // srp: walk-212347 77 -> 89% within 12 deg of truth, every move toward it; loud made two wrong moves (-26 -> +71)
  static ARR_BIN = 4.0;              // degrees per bin when finding an interval's arrivals
  static ARR_NEAR = 6.0;             // an arrival this close to a bearing counts for it
  static STEP_MIN = 8;               // fewer points than this in an interval and the step changes nothing
  static STEP_BEAT = 1.3;            // how far another arrival must out-weigh the incumbent for the main to move
  // A VIEW, NOT A RULE (2026-10-06, the rotation tape): true shows the strongest second arrival ALWAYS, with
  // its strength against the main (ghostRatio) so the page can fade it -- the diffuse floor faint, a
  // near-tie bright. Dimming the dot still means a near-tie only. Playback sets it from &ghost=all.
  static GHOST_ALL = false;
  // One bearing from the first ms after speech rises in the gate audio.
  // The utterance's first arrival is published once; range refinements cannot
  // change it. The next utterance opens a new decision.
  static ONSET_LOCK = true;
  static MAIN_HOLDS = true;
  static ONSET_ONLY = true;
  static CAP_S = Infinity;           // the 8 s cap is OFF: a capped window starts mid-sentence, and its lock takes smeared, reflection-heavy speech (walk-205043: Julie +6/+44/+6/+44 every 8 s). Clean locks come at onsets.
  // RANGE FROM THE DIRECT LEVEL (Jay, 2026-10-06: "Range is cdr_direct ... computed from onset and
  // maintain a running window"). "direct" uses cdr_direct's coherent share as a LEVEL and the
  // free-field 1/r law; "free" is the old dir/dif ratio with the fitted slope. Measured on
  // walk-205043: the level spans ~50 dB across the twenty windows against the ratio's ~20, and it
  // tracks the walk the decode announces ("stand back here" 2.0 -> 5.3 m, "even further" -> 7.1 m).
  static RANGE_FROM = "free";   // REVERTED 2026-10-06: the ratio is what worked; "direct" was my substitution
  // Range estimates are dimensionless opening-distance units. Conversion belongs downstream.

  // THE OPENING IS THE TAPE'S, NOT THE TRACK'S. Instances are per track id, and a tape can hand the
  // same talker several ids (DareDevil's tracker and the pot lane), so the reference lives on the class
  // and is cleared when the clock restarts -- one run per tape on the page, many in a batch.
  static refCdr = null;
  static refKind = null;             // "free" or "steered": the opening and every later reading must match
  static slopeNow = null;            // this tape's law, set at the opening (free kind only)
  static pool = null;                // { deg, d[3], r[3] } -- the spot the current talker is standing at
  static _lastT = null;
  static _newTape(t) {
    const R = RangeScheme;
    if (typeof t !== "number" || !isFinite(t)) return;
    if (R._lastT !== null && t < R._lastT - 1.0) { R.refCdr = null; R.refKind = null; R.slopeNow = null; R.pool = null; R.fault = null; }
    R._lastT = t;
  }

  // ONE INSTANCE PER TAPE, NOT PER TRACK (2026-10-05). Everything this reads -- dir_deg, level_direct,
  // cdrf -- is the PAIR's, identical on every track of a frame. One instance per DareDevil track gave
  // each track its own windows, and when the page's loudest-beam pick switched tracks the dot jumped to
  // the other instance's reading (walk-212347 carries a second track on 31% of frames). A zero-argument
  // constructor gets one shared instance, and each frame is read once, by whichever track comes first --
  // which is what geonar/stage1_bench.py scores.
  // Compose an onset bearing with the existing range engine. Its range inputs and
  // windowing are unchanged; only the bearing returned to the renderer is replaced.
  static withBearing(source, label) {
    const Base = this;
    return class {
      static label = label;
      static current = true;
      static outputUnit = "opening";
      static selfSteady = true;
      static anchorsNeeded = 0;
      constructor() { this.range = new Base(); this.reset(); }
      reset() { this.range.reset(); this.deg = null; this.event = null; this.ft = null; }
      estimate(f) {
        if (this.ft !== null && f.t < this.ft) this.reset();
        this.ft = f.t;
        const event = f.onset_bearing, read = event && event[source];
        if (event && event.index !== this.event && read && Number.isFinite(read.deg)
            && Number.isFinite(read.available_t_s) && f.t >= read.available_t_s) {
          this.deg = read.deg;
          this.event = event.index;
        }
        // Both channels use this phone gate. A displayed bearing must not leave range
        // reading the old refined onset or rejecting its own missing bearing field.
        const active = event && f.t >= event.t_s && f.t <= event.end_t_s
          && read && Number.isFinite(read.deg) && f.t >= read.available_t_s;
        const track = f.track && { ...f.track, onset_idx: active ? event.index : null,
          onset_deg: active ? read.deg : null,
          deg: this.deg === null ? f.track.deg : this.deg };
        const distance = this.range.estimate({ ...f, track });
        return this.deg === null ? null : distance;
      }
      bearing() { return this.deg; }
      moveId() { return this.event; }
      acousticMode(f) {
        if (this.deg === null) return "acquiring";
        return f.track && f.track.onset_idx != null ? "held" : "silent";
      }
    };
  }

  constructor() { this.reset(); }
  reset() { this.last = null; this.curIdx = null; this.pos = null; this.cur = null; this.u = null; this._ft = null; this.mv = 0; }

  static _median(v) {
    const s = v.slice().sort(function (a, b) { return a - b; });
    const m = s.length >> 1;
    return s.length % 2 ? s[m] : 0.5 * (s[m - 1] + s[m]);
  }
  /* the median of `key` over the loudest fifth (by coherent direct level) of what was banked */
  static _loudFifth(bank, key) {
    const v = bank.filter(function (p) { return isFinite(p[key]) && isFinite(p.w); });
    if (v.length < 3) return null;
    let keep = v;
    if (v.length > 10) {
      const ws = v.map(function (p) { return p.w; }).sort(function (a, b) { return a - b; });
      const cut = ws[Math.floor(0.8 * (ws.length - 1))];
      keep = v.filter(function (p) { return p.w >= cut; });
    }
    return RangeScheme._median(keep.map(function (p) { return p[key]; }));
  }
  static _wrapDeg(d) { return ((d + 180) % 360 + 360) % 360 - 180; }
  /* an interval's evidence as [deg, mass] points: its loudest fifth's per-hop bearings, or its SRP arrivals */
  static _points(ev, how) {
    const out = [];
    if (how === "srp") {
      ev.forEach(function (e) {
        const s = e.s2;
        if (!s) return;
        if (isFinite(s[0]) && s[1] > 0) out.push([s[0], s[1]]);
        if (s[2] !== null && isFinite(s[2]) && s[3] > 0) out.push([s[2], s[3]]);
      });
      return out;
    }
    const v = ev.filter(function (e) { return isFinite(e.d) && isFinite(e.w); });
    let keep = v;
    if (v.length > 10) {
      const ws = v.map(function (e) { return e.w; }).sort(function (a, b) { return a - b; });
      const cut = ws[Math.floor(0.8 * (ws.length - 1))];
      keep = v.filter(function (e) { return e.w >= cut; });
    }
    keep.forEach(function (e) { out.push([e.d, 1]); });
    return out;
  }
  static _massAt(pts, x) {
    let m = 0;
    for (let i = 0; i < pts.length; i++) if (Math.abs(RangeScheme._wrapDeg(pts[i][0] - x)) <= RangeScheme.ARR_NEAR) m += pts[i][1];
    return m;
  }
  /* the interval's arrivals, strongest first, each at least TIE_SEP from the others */
  static _arrivals(pts) {
    const R = RangeScheme, nb = Math.ceil(184 / R.ARR_BIN), m = new Float64Array(nb), wd = new Float64Array(nb);
    pts.forEach(function (p) {
      const b = Math.max(0, Math.min(nb - 1, Math.floor((p[0] + 92) / R.ARR_BIN)));
      m[b] += p[1]; wd[b] += p[1] * p[0];
    });
    const out = [], used = new Uint8Array(nb);
    for (let k = 0; k < 3; k++) {
      let best = -1, bm = 0;
      for (let b = 0; b < nb; b++) {
        if (used[b]) continue;
        const sm = m[b] + (b > 0 ? m[b - 1] : 0) + (b < nb - 1 ? m[b + 1] : 0);
        if (sm > bm) { bm = sm; best = b; }
      }
      if (best < 0) break;
      let sw = 0, sd = 0;
      for (let b = Math.max(0, best - 1); b <= Math.min(nb - 1, best + 1); b++) { sw += m[b]; sd += wd[b]; }
      const deg = sd / sw;
      out.push({ deg: deg, m: R._massAt(pts, deg) });
      for (let b = 0; b < nb; b++) if (Math.abs((b + 0.5) * R.ARR_BIN - 92 - deg) < R.TIE_SEP) used[b] = 1;
    }
    return out.sort(function (a, b) { return b.m - a.m; });
  }
  // No metre scale or distance clamp enters the unit estimate.

  /* the direction-free statistic: band powers summed over the window, ratio per band, bands averaged */
  static _free(sum) {
    if (!sum || sum.n < 3) return null;
    let acc = 0;
    for (let b = 0; b < 3; b++) acc += 10 * Math.log10(Math.max(sum.d[b], 1e-30) / Math.max(sum.r[b], 1e-30));
    return acc / 3;
  }

  /* THE DIRECT LEVEL, not the ratio (Jay, 2026-10-06). cdr_direct separates the coherent share that
   * arrived straight from the mouth from the room's part; `d` IS that share. Dividing it by the
   * diffuse part throws away most of the distance information: measured over walk-205043's twenty
   * windows, the direct level spans ~50 dB while dir/dif spans ~20. A direct field falls as 1/r in
   * amplitude, which in dB is 20 per decade -- exactly SLOPE = 1, so the existing
   * u = 10^((ref - v)/(20*slope)) gives the free-field law unchanged once v is a LEVEL. */
  static _directDb(sum) {
    if (!sum || sum.n < 3) return null;
    let p = 0;
    for (let b = 0; b < 3; b++) p += Math.max(sum.d[b], 1e-30);
    return 10 * Math.log10(p / sum.n);
  }

  static _window(t0) {
    return { t0: t0, degs: [], bank: [], ev: [], locked: false, deg: null, next: 0, kind: null, tie: false, ghost: null, ghostR: null, moves: 0, fa: null, src: null,
             free: { d: [0, 0, 0], r: [0, 0, 0], n: 0 }, base: null, poolDeg: null, opening: false };
  }

  /* this window's reading: its own band powers plus the pool it joined at its first draw */
  static _reading(c) {
    const R = RangeScheme;
    if (c.kind !== "free") return null;
    const s = { d: [0, 0, 0], r: [0, 0, 0], n: c.free.n + (c.base ? c.base.n : 0) };
    for (let b = 0; b < 3; b++) {
      s.d[b] = c.free.d[b] + (c.base ? c.base.d[b] : 0);
      s.r[b] = c.free.r[b] + (c.base ? c.base.r[b] : 0);
    }
    return (R.RANGE_FROM === "direct")
      ? { v: R._directDb(s), sum: s, kind: "direct" }
      : { v: R._free(s), sum: s, kind: "free" };
  }

  _show(v, kind, c, f) {
    const R = RangeScheme;
    if (v === null) return;
    if (R.refCdr === null || (c.opening && kind === R.refKind)) {   // the opening: 1.000 u, and the law,
      R.refCdr = v; R.refKind = kind; c.opening = true;            // refined at each of its own steps
      R.slopeNow = (kind === "free" && R.SLOPE_FROM_OPENING)
        ? Math.max(R.SLOPE_MIN, Math.min(R.SLOPE_MAX, R.SLOPE_A + R.SLOPE_B * v)) : R.SLOPE;
    }
    if (kind === R.refKind) {
      this.u = Math.pow(10, (R.refCdr - v) / (20 * (R.slopeNow || R.SLOPE)));
      this.last = this.u;
    }
  }

  estimate(f) {
    const R = RangeScheme, t = f.track;
    R._newTape(f.t);
    if (!t) return this.last;
    if (this._ft === f.t) return this.last;                         // this frame was read via another track
    if (this._ft !== null && f.t < this._ft - 1.0) this.reset();    // the clock restarted: a new run
    this._ft = f.t;
    const oi = t.onset_idx;
    if (oi === null || oi === undefined) return this.last;          // between utterances: held
    const onsetOnly = true;
    if (oi !== this.curIdx) {
      this.curIdx = oi;
      this.cur = R._window(f.t);
      this.cur.fa = Number.isFinite(t.onset_deg) ? t.onset_deg : null;
      this.cur.deg = this.cur.fa;
      this.cur.src = this.cur.fa === null ? "none" : "onset";
      this.pos = this.cur.fa === null ? null : { deg: this.cur.fa };
    }
    const dirDeg = typeof t.dir_deg === "number" ? t.dir_deg : NaN;
    const c = this.cur, el = f.t - c.t0, steps = R.STEPS_S;
    if (onsetOnly && c.fa === null && Number.isFinite(t.onset_deg)) {
      c.fa = t.onset_deg; c.deg = c.fa; c.src = "onset";
      this.pos = { deg: c.fa };
    }
    if (c.locked) {                                                 // after the lock: the next step's evidence
      c.ev.push({ w: (typeof t.level_direct === "number") ? t.level_direct : NaN, d: dirDeg,
                  s2: (Array.isArray(t.srp2) && t.srp2.length === 4) ? t.srp2 : null });
    } else {
      if (!onsetOnly && typeof t.deg === "number" && isFinite(t.deg)) c.degs.push(t.deg);
      if (c.fa === null && typeof t.onset_deg === "number" && isFinite(t.onset_deg)) c.fa = t.onset_deg;   // the window's gate-anchored onset
      if (typeof t.level_direct === "number")
        c.bank.push({ w: t.level_direct, d: dirDeg, c: (typeof t.cdr_db === "number") ? t.cdr_db : NaN });
    }
    // NO CEILING ON THE ACCUMULATION: it used to stop at the last step age (8 s) because nothing
    // redrew past it. A running window keeps summing until the utterance ends or the bearing moves.
    if (Array.isArray(t.cdrf) && t.cdrf.length === 6 && el < steps[steps.length - 1]) {
      for (let b = 0; b < 3; b++) { c.free.d[b] += Math.pow(10, t.cdrf[2 * b] / 10); c.free.r[b] += Math.pow(10, t.cdrf[2 * b + 1] / 10); }
      c.free.n++;
    }
    // THE STEPS: the only frames on which the dot moves.
    while (c.next < steps.length && el >= steps[c.next]) {
      if (c.next === 0) {
        // THE FIRST STEP: the bearing locks, and the window decides whether it stands where the pool
        // does. Direction-free CDR when the fixture carries it, else the old steered statistic, once.
        c.locked = true;
        c.deg = c.fa;
        c.src = c.fa === null ? "none" : "onset";
        c.deg0 = c.deg;
        // THE ONSET'S TIE TEST: the lock is the main either way; a near-tie names the other arrival -- the
        // one of the two farther from the lock -- as the ghost.
        const s2 = (Array.isArray(t.srp2) && t.srp2.length === 4) ? t.srp2 : null;
        c.tie = !!(s2 && s2[1] > 0 && s2[3] !== null && s2[3] > 0 && s2[3] * R.TIE_RATIO >= s2[1] &&
                   Math.abs(R._wrapDeg(s2[0] - s2[2])) >= R.TIE_SEP);
        c.ghost = null; c.ghostR = null;
        if (s2 && s2[1] > 0 && s2[3] !== null && s2[3] > 0) {
          const aFar = (c.deg === null) || Math.abs(R._wrapDeg(s2[0] - c.deg)) >= Math.abs(R._wrapDeg(s2[2] - c.deg));
          const far = aFar ? s2[0] : s2[2], sFar = aFar ? s2[1] : s2[3], sNear = aFar ? s2[3] : s2[1];
          if (c.deg === null || Math.abs(R._wrapDeg(far - c.deg)) >= R.TIE_SEP) { c.ghost = far; c.ghostR = sFar / sNear; }
        }
        c.tie = c.tie && (c.ghost !== null);
        if (c.deg !== null) this.pos = { deg: c.deg };
        const own = R._free(c.free);
        if (own !== null) {
          c.kind = "free";
          const P = R.pool;
          if (P && Math.abs(R._wrapDeg(c.deg - P.deg)) <= R.POOL_DEG && Math.abs(own - R._free(P)) <= R.POOL_DB) {
            c.base = { d: P.d.slice(), r: P.r.slice(), n: P.n }; c.poolDeg = P.deg;
          } else {
            c.base = null; c.poolDeg = c.deg;
          }
        } else {
          const v = R._loudFifth(c.bank, "c");
          if (v !== null) { c.kind = "steered"; this._show(v, "steered", c, f); }
          else if (R.refCdr === null) R.fault = "no cdrf or cdr_db on this fixture -- rebuild it with tape_fixture";
        }
      }
      if (c.next > 0 && R.STEP_EV !== "off" && c.deg !== null) {
        // A LATER STEP: the interval since the last step decides the main and the ghost afresh. The
        // incumbent holds unless another arrival beats it by more than TIE_RATIO; then the voice is
        // coming from there now, and the main moves (a talker who turned back to the phone swaps them).
        const pts = R._points(c.ev, R.STEP_EV);
        c.ev = [];
        if (pts.length >= R.STEP_MIN) {
          const arr = R._arrivals(pts);
          if (arr.length) {
            const inc = c.deg, incM = R._massAt(pts, inc), top = arr[0];
            let main = inc;
            if (!R.MAIN_HOLDS && c.src !== "onset" && Math.abs(R._wrapDeg(top.deg - inc)) > R.ARR_NEAR && incM * R.STEP_BEAT < top.m) main = top.deg;
            const mainM = R._massAt(pts, main);
            let gh = null, gm = 0;
            arr.concat([{ deg: inc }]).forEach(function (a) {
              if (Math.abs(R._wrapDeg(a.deg - main)) < R.TIE_SEP) return;
              const m = R._massAt(pts, a.deg);
              if (m > gm) { gm = m; gh = a.deg; }
            });
            c.tie = (gh !== null && gm * R.TIE_RATIO >= mainM);
            c.ghost = gh; c.ghostR = (gh !== null && mainM > 0) ? gm / mainM : null;
            if (main !== inc) { c.deg = main; c.moves++; this.mv++; this.pos = { deg: main }; }
          }
        }
      }
      c.next++;
      // EVERY STEP REDRAWS THE RANGE from all of the window so far, and the pool carries it, so the
      // next window to stand here starts from everything said here.
      if (c.kind === "free") {
        const rd = R._reading(c);
        if (rd && rd.v !== null) {
          R.pool = { deg: c.poolDeg, d: rd.sum.d, r: rd.sum.r, n: rd.sum.n };
          this._show(rd.v, rd.kind, c, f);
        }
      }
    }
    // ONE READING PER ONSET, HELD (Jay, 2026-10-06: "at every onset, we calculate range right on the
    // same onset. And we hold it there for now."). The range is drawn once, at the lock, from the
    // onset's own evidence -- then it holds for the rest of the window exactly as the bearing does.
    // NOT re-averaged as the utterance runs: a cumulative mean over a long utterance goes numb (frame
    // 6000 moves it by 0.017%), and a radial walk never trips MOVE_DEG because walking toward the
    // phone changes range without changing bearing. Measuring once, at the onset, sidesteps both.
    // PLACE AT ONCE (Jay's Stage-1 tenet): before the first range of the tape the talker is drawn at
    // the opening's own distance, 1 u, which is exactly what the opening will settle to.
    if (this.last === null && !onsetOnly) this.last = 1.0;
    return this.last;
  }

  /* One first-ms bearing per utterance, held until the next utterance onset. */
  bearing(f) { return this.pos ? this.pos.deg : null; }
  /* the near-identical second arrival, while there is one -- the page puts a dimmed ghost bubble there */
  ghost(f) {
    const t = f && f.track;
    if (!t || t.onset_idx === null || t.onset_idx === undefined || !this.cur || !this.cur.locked) return null;
    if (!this.cur.tie && !RangeScheme.GHOST_ALL) return null;
    return this.cur.ghost;
  }
  /* the ghost's strength against the main's (1 = identical), while a ghost is shown */
  ghostRatio(f) { return (this.ghost(f) === null) ? null : this.cur.ghostR; }
  /* counts every in-window switch of the main arrival; the page SNAPS the dot when it changes, no glide */
  moveId(f) { return this.mv; }
  facing(f) { return null; }
  rays(f) { return null; }
  acousticMode(f) {
    const t = f && f.track;
    if (!t || t.onset_idx === null || t.onset_idx === undefined) return this.last === null ? "silent" : "held";
    if (!this.cur) return "silent";
    if (this.cur.locked && this.cur.tie) return "uncertain";          // a near-identical second arrival: the page dims the dot
    return (this.cur.locked || this.pos) ? "held" : "acquiring";
  }
}
