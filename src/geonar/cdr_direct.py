r"""THE DIRECT LEVEL, BY SPACE NOT TIME (Jay, 2026-09-26). Standalone: nothing here touches RangeSteady or RangeMath.

What the phone hears is direct sound plus the room. The room cannot be taken out of one stream by time (a syllable
ramps slower than the first reflections arrive) or by amplitude, but it can be taken out by SPACE: with two capsules
d apart, the direct sound is coherent between them at the talker's delay, while a diffuse field above ~c/(2d) is not
(sinc(kd) has its first zero at 1.1 kHz for 157 mm). So per hop, per frequency bin, the coherent-to-diffuse ratio
(Schwarz & Kellermann, "Coherent-to-Diffuse Power Ratio Estimation for Dereverberation", 2015) says what fraction of
the power arrived straight from the mouth; that fraction times the power is the direct level, with the room's part --
whatever the room is, tile, step-down, hallway -- thrown away cell by cell.

Per hop this emits: total power (band), direct power (band), CDR in dB, and the delay it locked to. The report per
marked stop is the point: does the direct level ignore the room the way the total does not.

  Gx  = measured coherence    = Phi12 / sqrt(Phi11 Phi22)         (recursively smoothed PSDs)
  Gn  = diffuse coherence     = sinc(k d)                          (real)
  Gs  = direct coherence      = exp(j 2 pi f tau), tau from the smoothed cross-spectrum itself (GCC-PHAT, |tau| <= d/c)
  Gx  = (CDR Gs + Gn) / (CDR + 1)  ->  CDR = Re[(Gn - Gx) conj(Gx - Gs)] / |Gx - Gs|^2, clamped at 0
  direct fraction = CDR / (1 + CDR)
"""
import sys, json, wave, math
import numpy as np

SR, HOP, NFFT = 48000, 512, 2048
C = 343.0
ALPHA = 0.92                 # PSD smoothing per hop: ~130 ms memory. A coherence needs INDEPENDENT frames averaged:
                             # at 0.7 with 75% frame overlap it was near single-frame, whose magnitude is ~1 whatever the room,
                             # and the estimator saturated at -9 dB everywhere (first run, 2026-09-26)
F_LO, F_HI = 1100.0, 8000.0  # the band where a diffuse field is incoherent across the pair, and speech still has energy


def cdr_direct(x, baseline_m, f_lo=None, f_hi=None):
    """x: (samples, 2) float. Returns per-hop arrays: total, direct (band power), cdr_db, tau_ms.

    f_lo/f_hi OVERRIDE THE BAND (2026-10-02), defaulting to the module's F_LO/F_HI so every existing
    caller is untouched. Added for the two-band split: run this once over 1.1-2 kHz, where mouth
    directivity is weak, and once over 4-8 kHz, where front-to-back is 15-20 dB. Both bands sit above
    c/2d, so the coherence model is valid in each -- which is what makes the pair separable at all.
    The DIFFERENCE between the two is a directivity tilt measured on the direct component only, with
    the room already divided out of both; their mean is the range cue. One scalar carrying three
    unknowns becomes two scalars carrying two.

    ONE DIRECT LEVEL PER TRACK, when `steer` is given (2026-09-28). Without it the estimator locks to
    the single strongest delay in the band -- whoever is loudest -- and every track at that hop inherits
    that one number. With two people talking that is visibly wrong: the sample log showed three tracks
    at -2.7, +36.1 and +1.7 degrees all reporting 1.82 m at the same instant, because they were all
    reading one talker's level. A picture built on that renders everybody at one distance.

    NOT NAMED `steer`: this function already had a local of that name -- the 61-row GCC-PHAT steering
    matrix -- and a parameter called `steer` was silently overwritten by it before the loop, so every
    hop read a row of that matrix instead of the caller's delays and wrote 295 NaNs. Found by a test
    that asked the on-bearing steer to beat a 60-degree-off one; it would otherwise have quietly filled
    the fixtures with rubbish.

    Steering Gs at each track's own bearing instead of the argmax WAS TRIED AND DOES NOT WORK: on
    a stop measured at -13 degrees, aiming 60 degrees away returned a HIGHER direct level than aiming
    on the bearing, by 2.5 dB. This is not a beamformer -- it solves Gx = (CDR*Gs + Gn)/(CDR + 1) for
    CDR on the assumption Gs is the RIGHT direction, so a wrong Gs yields a projection with no
    physical meaning rather than a smaller number. A single-source model inversion cannot be aimed.

    Separating two talkers' levels needs a real spatial filter -- a null on the other source -- which
    is what DareDevil's separated beams are for. Those are mono in every tape measured (see
    tape_fixture's channel-count note), so that path starts there, not here.
    from each track's own bearing -- and a fifth return value gives each of them its own direct power,
    measured by asking the coherence how much of this hop arrived from THAT direction instead of from
    the loudest one. The expensive parts (the FFT and the recursive PSDs) are shared; only the CDR
    algebra repeats, on the band bins alone since nothing outside the band is ever summed.
    """
    n = (len(x) - NFFT) // HOP + 1
    win = np.hanning(NFFT)
    f = np.fft.rfftfreq(NFFT, 1.0 / SR)
    f_lo = max(F_LO if f_lo is None else f_lo, C / (2 * baseline_m))   # the diffuse field is coherent below c/2d: 1.1 kHz at 157 mm, 2.9 kHz at 60 mm
    band = (f >= f_lo) & (f <= (F_HI if f_hi is None else f_hi))
    k = 2 * np.pi * f / C
    Gn = np.sinc(k * baseline_m / np.pi)                     # numpy sinc is sin(pi x)/(pi x): sinc(kd/pi) = sin(kd)/(kd)
    tmax = baseline_m / C
    taus = np.linspace(-tmax, tmax, 61)
    steer = np.exp(-1j * 2 * np.pi * np.outer(taus, f[band]))  # (taus, band bins)
    P11 = P22 = None; P12 = None
    total = np.zeros(n); direct = np.zeros(n); cdr_db = np.zeros(n); tau_ms = np.zeros(n)

    for i in range(n):
        seg = x[i * HOP:i * HOP + NFFT]
        X1 = np.fft.rfft(seg[:, 0] * win); X2 = np.fft.rfft(seg[:, 1] * win)
        a11, a22, a12 = np.abs(X1) ** 2, np.abs(X2) ** 2, X1 * np.conj(X2)
        if P11 is None: P11, P22, P12 = a11, a22, a12
        else:
            P11 = ALPHA * P11 + (1 - ALPHA) * a11; P22 = ALPHA * P22 + (1 - ALPHA) * a22; P12 = ALPHA * P12 + (1 - ALPHA) * a12
        Gx = P12 / (np.sqrt(P11 * P22) + 1e-20)
        # the delay: where the whitened cross-spectrum agrees best across the band
        phat = P12[band] / (np.abs(P12[band]) + 1e-20)
        score = np.real(steer @ phat)
        tau = taus[int(np.argmax(score))]
        Gs = np.exp(1j * 2 * np.pi * f * tau)
        num = np.real((Gn - Gx) * np.conj(Gx - Gs)); den = np.abs(Gx - Gs) ** 2 + 1e-12
        cdr = np.clip(num / den, 0.0, 1e4)
        frac = cdr / (1.0 + cdr)
        pw = 0.5 * (P11 + P22)
        total[i] = pw[band].sum(); direct[i] = (frac * pw)[band].sum()
        cdr_db[i] = 10 * np.log10(direct[i] / max(total[i] - direct[i], 1e-20)); tau_ms[i] = tau * 1000
    return total, direct, cdr_db, tau_ms


FREE_BANDS = ((1100.0, 2000.0), (2000.0, 4000.0), (4000.0, 8000.0))


def cdr_free_bands(x, baseline_m, bands=FREE_BANDS):
    """THE DIRECTION-FREE CDR, PER BAND (2026-10-05) -- the range cue.

    Schwarz & Kellermann's DOA-independent estimator. The model is the same as cdr_direct's,
    Gx = (c Gs + Gn)/(c + 1), but Gs = exp(j2 pi f tau) is left UNKNOWN except for |Gs| = 1, which gives
        c^2 (X - 1) + 2c (X - Gn R) + (X - 2 Gn R + Gn^2) = 0,   X = |Gx|^2,  R = Re Gx
        c = (X - Gn R + sqrt(Gn^2 R^2 - Gn^2 X + Gn^2 - 2 Gn R + X)) / (1 - X)
    -- no delay, no steering. It counts EVERY coherent arrival as "direct", early reflections included,
    and that is what tracks distance: on LOCATA's DICIT 160 mm pair (12 recordings, real rooms and
    talkers, tracked distance, line of sight), the mean of these three bands' CDR ordered 89% of
    same-talker 0.8 s window pairs and 91% at 2.4 s, against 64-67% for loudness, 57-65% for
    cdr_direct's GCC-steered CDR above, and 38-47% steered by the EXACT tracked delay.

    Returns per hop, per band, the direct and diffuse POWERS (n, len(bands)) each -- not a per-hop ratio,
    so a caller sums each over whatever window it commits on and takes the ratio once. That is how it was
    scored; a mean of per-hop ratios is a different and noisier statistic.
    """
    n = (len(x) - NFFT) // HOP + 1
    win = np.hanning(NFFT)
    f = np.fft.rfftfreq(NFFT, 1.0 / SR)
    Gn = np.sinc(2 * np.pi * f / C * baseline_m / np.pi)
    lo_ok = C / (2 * baseline_m)                        # below c/2d the diffuse field is coherent too
    masks = [(f >= max(lo, lo_ok)) & (f < hi) for lo, hi in bands]
    dirp = np.zeros((n, len(bands))); difp = np.zeros((n, len(bands)))
    P11 = P22 = P12 = None
    for i in range(n):
        seg = x[i * HOP:i * HOP + NFFT]
        X1 = np.fft.rfft(seg[:, 0] * win); X2 = np.fft.rfft(seg[:, 1] * win)
        a11, a22, a12 = np.abs(X1) ** 2, np.abs(X2) ** 2, X1 * np.conj(X2)
        if P11 is None: P11, P22, P12 = a11, a22, a12
        else:
            P11 = ALPHA * P11 + (1 - ALPHA) * a11; P22 = ALPHA * P22 + (1 - ALPHA) * a22; P12 = ALPHA * P12 + (1 - ALPHA) * a12
        Gx = P12 / (np.sqrt(P11 * P22) + 1e-20)
        X = np.abs(Gx) ** 2; R = np.real(Gx)
        disc = np.maximum(Gn ** 2 * R ** 2 - Gn ** 2 * X + Gn ** 2 - 2 * Gn * R + X, 0.0)
        c = np.clip((X - Gn * R + np.sqrt(disc)) / np.maximum(1 - X, 1e-6), 0.0, 1e4)
        frac = c / (1.0 + c); pw = 0.5 * (P11 + P22)
        for b, m in enumerate(masks):
            dirp[i, b] = (frac * pw)[m].sum(); difp[i, b] = ((1 - frac) * pw)[m].sum()
    return dirp, difp


def cdr_free_db(dirp, difp):
    """One number from summed band powers (any window): the mean over bands of 10 log10(direct/diffuse)."""
    d = np.asarray(dirp, float).sum(axis=0); r = np.asarray(difp, float).sum(axis=0)
    return float(np.mean(10 * np.log10(np.maximum(d, 1e-30) / np.maximum(r, 1e-30))))


class CdrFreeStream:
    """The existing direction-free estimator, retaining PSD state between raw frames."""
    def __init__(self, baseline_m, bands=FREE_BANDS):
        self.win = np.hanning(NFFT)
        f = np.fft.rfftfreq(NFFT, 1.0 / SR)
        self.gn = np.sinc(2*f*baseline_m/C)
        self.masks = [(f >= max(lo, C/(2*baseline_m))) & (f < hi) for lo, hi in bands]
        self.psd = None

    def frame(self, raw):
        if raw.shape != (NFFT, 2):
            raise ValueError('CDR needs one full raw stereo FFT frame')
        x1 = np.fft.rfft(raw[:, 0]*self.win)
        x2 = np.fft.rfft(raw[:, 1]*self.win)
        now = (np.abs(x1)**2, np.abs(x2)**2, x1*np.conj(x2))
        self.psd = now if self.psd is None else tuple(ALPHA*old+(1-ALPHA)*new for old, new in zip(self.psd, now))
        p11, p22, p12 = self.psd
        gx = p12/(np.sqrt(p11*p22)+1e-20)
        x, r, gn = np.abs(gx)**2, np.real(gx), self.gn
        disc = np.maximum(gn**2*r**2-gn**2*x+gn**2-2*gn*r+x, 0.)
        c = np.clip((x-gn*r+np.sqrt(disc))/np.maximum(1-x, 1e-6), 0., 1e4)
        fraction, power = c/(1+c), .5*(p11+p22)
        return (np.array([(fraction*power)[m].sum() for m in self.masks]),
                np.array([((1-fraction)*power)[m].sum() for m in self.masks]))


# ---- BAND POWER -> AMPLITUDE, so a fixture can carry this next to `level` -------------------------
# total[] and direct[] are one-sided sums of |X|^2 over the band, which is a ratio-only quantity: every
# use divides one by another and the constant cancels. A fixture is read by schemes that also hold
# `level` and `level_raw` as RMS amplitudes in 0..1, so the constant is worth applying once here rather
# than leaving a third scale in the file for someone to trip over.
#
#   mean(x^2) in band  =  2 * sum_band |X_k|^2 / (N^2 * mean(win^2))        (Parseval, one-sided)
#
# so amplitude = sqrt(power) * sqrt(2/mean(win^2)) / N. Hanning has mean(win^2) = 3/8.
AMP = math.sqrt(2.0 / float((np.hanning(NFFT) ** 2).mean())) / NFFT


def amp(power):
    """A band power from cdr_direct() as an RMS amplitude in the same 0..1 units as track.level."""
    return np.sqrt(np.maximum(power, 0.0)) * AMP


def gap_floor(direct, secs=8.0, pct=20.0):
    """THE FLOOR OF THE DIRECT ESTIMATE, CAUSALLY, WITH NO TALK MASK (2026-09-28).

    The margin that decides whether a range is claimable is the direct level during speech minus the
    direct level in the silences inside the same stop. Offline that is easy -- the fixture knows which
    hops are speech. Live it is not, and a gate that needs the decode to say whether the decode can be
    trusted is the wrong shape.

    It does not need the mask. Speech is intermittent at the scale of a second, so a low percentile of
    the direct level over a trailing window lands in the gaps between words on its own, which is how a
    noise floor is tracked everywhere else. Causal by construction: hop i sees only hops <= i.

    A high floor is the tell that the estimator locked onto something coherent that is not the talker
    -- the phone's own spoken prologue at zero range, a chime, a fan -- and on the corpus the three
    worst margins are all at boresight, so this catches contamination rather than geometry.
    """
    n = len(direct)
    w = max(1, int(round(secs * SR / HOP)))
    out = np.zeros(n)
    for i in range(n):
        out[i] = np.percentile(direct[max(0, i - w + 1):i + 1], pct)
    return out


if __name__ == "__main__":
    CAP = r"C:\Projects\GithubRoot\Dictate\captures\geonar"
    for name in (sys.argv[1:] or ["walk-195454", "walk-210054", "walk-165255"]):
        with wave.open(CAP + r"\tapes\%s.wav" % name) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64).reshape(-1, w.getnchannels()) / 32768.0
        fx = json.load(open(CAP + r"\%s-causal\odas.json" % name, encoding="utf-8"))
        d = float(fx.get("baseline_mm") or 157.0) / 1000.0
        total, direct, cdr_db, tau_ms = cdr_direct(x, d)
        n = len(total)
        talk = np.zeros(n, bool)
        for fr in fx["frames"]:
            h = fr["hop"]
            if h < n and fr.get("tracks"): talk[h] = True
        # Presenter-style 0.75 s windows, so the number is the one a scheme would read
        W = int(0.75 / (HOP / SR)); kern = np.ones(W) / W
        tw, dw = np.convolve(total, kern, "same"), np.convolve(direct, kern, "same")
        print("===== %s  baseline %.0f mm, %d hops, talking hops %d" % (name, d * 1000, n, talk.sum()))
        print("  truth   hops   total dB   direct dB   CDR dB   direct-in-gaps dB")
        anchor = None
        for s in fx["truth"]["stops"]:
            h0, h1 = int(s["t0"] * SR / HOP), int(s["t1"] * SR / HOP); seg = slice(max(0, h0), min(n, h1))
            tk = talk[seg]
            if tk.sum() < 10: continue
            T = 10 * np.log10(np.median(tw[seg][tk]) + 1e-20); D = 10 * np.log10(np.median(dw[seg][tk]) + 1e-20)
            G = 10 * np.log10(np.median(dw[seg][~tk]) + 1e-20) if (~tk).sum() > 10 else float("nan")
            cd = float(np.median(cdr_db[seg][tk]))
            print("  %5.2f  %5d   %7.1f    %7.1f    %+6.1f     %7.1f" % (s["r"], tk.sum(), T, D, cd, G))
        np.savez(CAP + r"\%s-causal\cdr_direct.npz" % name, total=total, direct=direct, cdr_db=cdr_db, tau_ms=tau_ms)
        sys.stdout.flush()


# ---- ONE FRAME, ON DEMAND ----------------------------------------------------------------------
# THE BEARING IS NOT COMPUTED HERE AND NEVER WAS (2026-10-06). ODAS reports it: the tracked source's
# own deg, which on walk-205043 sits within 5.5 degrees of truth at all 20 gate onsets while every
# desktop re-derivation tried that night was worse. tape_fixture reads it straight from the pots and
# tracks ODAS already wrote. What belongs in this file is the RANGE primitive, called per frame by the
# calculation that owns the window -- not a whole-tape precompute, and not a window-finder.
ARRIVAL_SEP_DEG = 10.0     # two arrivals closer than this are one arrival; tape_fixture pairs pots by it
WARM_S = 0.15              # ALPHA 0.92 per hop is ~130 ms of PSD memory, so warm past it before reading


def cdr_at(x, baseline_m, t_s, sr=SR, warm_s=WARM_S, f_lo=None, f_hi=None):
    """CDR for ONE frame, on demand, warmed. cdr_direct's PSDs are recursive (ALPHA per hop), so a
    cold call reads a near-single-frame coherence whose magnitude is ~1 whatever the room -- the
    saturation already documented at the top of this file. Hand it warm_s of preceding audio and
    keep only the last hop. NFFT is 42.7 ms, so there is no CDR for a 1 ms frame and never will be:
    the bearing read above is time-domain for exactly that reason."""
    a = max(0, int(round((t_s - warm_s) * sr)))
    b = int(round(t_s * sr)) + NFFT
    if b > len(x) or b - a < NFFT:
        return None
    total, direct, cdr_db, tau_ms = cdr_direct(x[a:b], baseline_m, f_lo=f_lo, f_hi=f_hi)
    if not len(total):
        return None
    return {"total": float(total[-1]), "direct": float(direct[-1]),
            "cdr_db": float(cdr_db[-1]), "tau_ms": float(tau_ms[-1])}


# ---- THE FIRST MILLISECOND -----------------------------------------------------------------------
# BEARING AND RANGE BOTH COME FROM HERE (Jay, 2026-10-06). The gate hands over the sample where speech
# began -- Diarize.raise(win0 + t0) is the onset itself, with no pre-roll offset, and AAudio's 5.46 s
# ring is what makes reaching back to it possible at all. In the millisecond from that sample the
# direct sound is ALONE: one millisecond is 34 cm of excess path, and a directionally distinct
# reflection needs far more (a floor bounce ~1.2 m, a near wall ~0.8 m, and this room's measured
# echo_lag is 307 samples = 6.4 ms = 2.19 m). So ms 0 is the talker, by geometry rather than by
# assertion, and everything after it is the room.
#
# WHY NOT ODAS FOR THIS. ODAS runs hop 512 / frame 1024: its bearing is an average over 21.3 ms with
# the 6.4 ms echo inside it, Kalman-smoothed across earlier hops. That gives PERSISTENCE -- the track
# that exists resists being dragged -- which is stable and roughly right, but it is not PRECEDENCE.
# Only a window shorter than the echo can read the direct alone.
#
# WHY THE LEVEL AND NOT THE RATIO, FOR RANGE. The direct field falls as 1/r in amplitude -- 20 dB per
# decade, the free-field law, no fitted constant. A direct/diffuse ratio needs the diffuse part
# estimated, which takes a window far longer than this one; in the first millisecond there is nothing
# diffuse to divide by yet. So the level IS the range cue here, scaled off the opening.
MS1_BAND = (2000.0, 6000.0)   # 1 ms is 48 samples: 800 Hz is 60 samples and contributes no cycle at
                              # all, 1100 Hz barely one. 2 kHz gives 2 cycles, 6 kHz gives 8 -- and
                              # that is where plosives and fricatives put the transient.
MS1_SEP_DEG = 10.0            # two peaks closer than this are one arrival


def onset_read(x, baseline_m, onset_s, sr=SR, band=MS1_BAND, ms=1.0):
    """The first millisecond at a GIVEN onset: bearing, its reflection, and the level. Nothing is
    searched for -- onset_s is the gate's own sample.

    Returns {deg, r, lag, ghost_deg, ghost_r, level_db} or None at a tape edge. Two peaks are kept,
    never one: keeping only the argmax is what made per-millisecond reads look random, because the
    curve's second peak -- the reflection -- was computed and thrown away.
    """
    from scipy.signal import butter, sosfiltfilt
    from numpy.lib.stride_tricks import sliding_window_view as swv
    n = int(round(ms * sr / 1000.0))
    L = int(np.ceil(baseline_m / C * sr)) + 2
    a = int(round(onset_s * sr))
    if a - L < 0 or a + n + L > len(x):
        return None
    lo = max(0, a - L - sr // 100)
    seg = sosfiltfilt(butter(4, band, btype="band", fs=sr, output="sos"), x[lo:a + n + L + 1, :2], axis=0)
    o = a - lo
    u = seg[o:o + n, 0] - seg[o:o + n, 0].mean()
    V = swv(seg[o - L:o + n + L, 1], n)
    V = V - V.mean(axis=1, keepdims=True)
    den = np.sqrt((u * u).sum() * (V * V).sum(axis=1))
    c = np.where(den > 1e-20, (V @ u) / np.maximum(den, 1e-20), 0.0)
    # Only physical lags may win: the pair can produce +-d/c*sr and no more, and asin's clamp turns
    # anything beyond it into a clean-looking +-90.
    lags = np.arange(c.size) - L
    c = np.where(np.abs(lags) <= baseline_m / C * sr, c, -9.0)
    sep = max(1, int(round(math.sin(math.radians(MS1_SEP_DEG)) * baseline_m / C * sr)))
    peaks, cc = [], c.copy()
    for _ in range(2):
        j = int(np.argmax(cc))
        if cc[j] <= -9.0:
            break
        lag = int(j - L)
        peaks.append((math.degrees(math.asin(max(-1.0, min(1.0, -(lag / float(sr)) * C / baseline_m)))),
                      float(c[j]), lag))
        cc[max(0, j - sep):j + sep + 1] = -9.0
    if not peaks:
        return None
    # THE LEVEL, over the same millisecond, both capsules. This is the range cue: amplitude falls as
    # 1/r, so r = r_open * (A_open / A), which in dB is the free-field 20 per decade.
    amp = float(np.sqrt((seg[o:o + n, :2] ** 2).mean()))
    out = {"deg": round(peaks[0][0], 2), "r": round(peaks[0][1], 3), "lag": peaks[0][2],
           "level_db": round(20.0 * math.log10(max(amp, 1e-12)), 2),
           "ghost_deg": None, "ghost_r": None}
    if len(peaks) > 1:
        out["ghost_deg"] = round(peaks[1][0], 2)
        out["ghost_r"] = round(peaks[1][1], 3)
    return out


def onset_lane(x, baseline_m, onset_s, dur_s=0.5, sr=SR, band=MS1_BAND, sep_deg=MS1_SEP_DEG):
    """THE DIRECT'S LANE (Jay, 2026-10-06). ms 0 names the lag; every later millisecond that lands in
    that lag's lane is the same arrival, and those are pooled. Milliseconds that land elsewhere are
    the room and are dropped, never averaged in -- which is the whole difference between this and the
    median that voided the 10-05/06 work. A median over ONE arrival is robust; a median ACROSS two
    points at neither.

    One millisecond resolves a bearing (measured on walk-212347/210054: reads at r >= 0.8 inside a
    stop agree to a few degrees) but cannot carry a level -- 25 dB of spread at a fixed distance,
    because 1 ms is a fraction of one phoneme's attack. Pooling the lane fixes exactly that: the
    bearing is already right and gets steadier, the level finally has enough speech behind it.
    """
    from scipy.signal import butter, sosfiltfilt
    from numpy.lib.stride_tricks import sliding_window_view as swv
    n = sr // 1000
    L = int(np.ceil(baseline_m / C * sr)) + 2
    a0 = int(round(onset_s * sr))
    hi = min(len(x), a0 + int(dur_s * sr) + n + L + 1)
    lo = max(0, a0 - L - sr // 100)
    if hi - lo < 4 * n or a0 - L < 0:
        return None
    seg = sosfiltfilt(butter(4, band, btype="band", fs=sr, output="sos"), x[lo:hi, :2], axis=0)
    lag_max = baseline_m / C * sr
    sep_lag = max(1, int(round(math.sin(math.radians(sep_deg)) * lag_max)))
    lags = np.arange(2 * L + 1) - L

    def read(o):
        if o - L < 0 or o + n + L > len(seg):
            return None
        u = seg[o:o + n, 0] - seg[o:o + n, 0].mean()
        V = swv(seg[o - L:o + n + L, 1], n)
        V = V - V.mean(axis=1, keepdims=True)
        den = np.sqrt((u * u).sum() * (V * V).sum(axis=1))
        c = np.where(den > 1e-20, (V @ u) / np.maximum(den, 1e-20), 0.0)
        c = np.where(np.abs(lags) <= lag_max, c, -9.0)
        amp = float(np.sqrt((seg[o:o + n, :2] ** 2).mean()))
        return c, amp

    first = read(a0 - lo)
    if first is None:
        return None
    seed = int(np.argmax(first[0])) - L                       # ms 0: the direct, alone by geometry
    keep_d, keep_l, keep_r = [], [], []
    steps = int(dur_s * 1000)
    for m in range(steps):
        rr = read(a0 - lo + m * n)
        if rr is None:
            break
        c, amp = rr
        j0, j1 = max(0, seed + L - sep_lag), min(len(c), seed + L + sep_lag + 1)
        if j1 <= j0:
            continue
        j = j0 + int(np.argmax(c[j0:j1]))                     # the lane's own peak, not the curve's
        if c[j] <= -9.0:
            continue
        keep_d.append(math.degrees(math.asin(max(-1.0, min(1.0, -((j - L) / float(sr)) * C / baseline_m)))))
        keep_r.append(float(c[j]))
        keep_l.append(amp)
    if len(keep_d) < 5:
        return None
    med = lambda v: float(np.median(np.asarray(v)))
    return {"deg": round(med(keep_d), 2), "r": round(med(keep_r), 3), "n": len(keep_d),
            "level_db": round(20.0 * math.log10(max(med(keep_l), 1e-12)), 2),
            "seed_deg": round(math.degrees(math.asin(max(-1.0, min(1.0, -(seed / float(sr)) * C / baseline_m)))), 2)}


def onset_phat(x, baseline_m, onset_s, sr=SR, ms=1.0, f_lo=None, f_hi=None, nfft=512):
    """GCC-PHAT on the supplied onset window only; no surrounding samples or timing search.

    The caller supplies the utterance's onset, not a later ODAS output-hop timestamp.
    The lag projection estimates inter-capsule delay within this one window. It does
    not choose between windows, tracks, or later arrivals. Padding adds no audio.
    """
    if not np.isfinite(baseline_m) or baseline_m <= 0:
        return None
    if not np.isfinite(onset_s) or sr <= 0 or not np.isfinite(ms) or ms <= 0:
        return None
    if np.ndim(x) != 2 or x.shape[1] < 2:
        return None
    n = int(round(ms * sr / 1000.0))
    if n < 2:
        return None
    a = int(round(onset_s * sr))
    if a < 0 or a + n > len(x):
        return None
    seg = x[a:a + n, :2].astype(np.float64)
    if seg.shape[1] != 2 or not np.isfinite(seg).all():
        return None
    seg = seg - seg.mean(axis=0, keepdims=True)
    if not np.any(seg):
        return None
    # A rectangular window retains the leading samples of the first arrival.
    X = np.fft.rfft(seg, n=nfft, axis=0)
    f = np.fft.rfftfreq(nfft, 1.0 / sr)
    lo = max(F_LO if f_lo is None else f_lo, C / (2 * baseline_m))
    band = (f >= lo) & (f <= (F_HI if f_hi is None else f_hi))
    if band.sum() < 3:
        return None
    P = X[band, 0] * np.conj(X[band, 1])
    mag = np.abs(P)
    if not np.any(mag > 0):
        return None
    phat = P / (mag + 1e-20)                       # the PHAT: every bin an equal vote
    tmax = baseline_m / C
    taus = np.linspace(-tmax, tmax, 181)
    steer = np.exp(-1j * 2 * np.pi * np.outer(taus, f[band]))
    score = np.real(steer @ phat)
    if not np.isfinite(score).all() or np.ptp(score) == 0:
        return None
    j = int(np.argmax(score))
    tau = taus[j]
    pk = float(score[j])
    rms = float(np.sqrt((score ** 2).mean()))      # peak-to-RMS: how clean this read is
    return {"deg": round(math.degrees(math.asin(max(-1.0, min(1.0, -tau * C / baseline_m)))), 2),
            "tau_ms": round(tau * 1000.0, 4),
            "ptr": round(pk / max(rms, 1e-12), 2),
            "n_bins": int(band.sum())}


ONSET_BEARING_VERSION = 10


def first_ms_bearings(x, baseline_m, onsets, sr=SR):
    """One immutable bearing per supplied utterance onset. No alternative input path."""
    out = []
    for index, onset in enumerate(onsets):
        sample = onset.get("onset_sample")
        if sample is None:
            if onset.get("t_s") is None:
                raise ValueError("An utterance must carry its onset sample or onset time")
            sample = int(round(float(onset["t_s"]) * sr))
        if not isinstance(sample, (int, np.integer)):
            raise ValueError("onset_sample must be an integer audio-frame offset")
        sample = int(sample)
        end = sample + sr // 1000
        read = onset_phat(x, baseline_m, sample / sr, sr=sr, ms=1.0)
        out.append({"t": round(sample / sr, 4), "t_on": sample / sr,
                    "index": index, "v": ONSET_BEARING_VERSION,
                    "policy": "first-ms-per-utterance", "onset_sample": sample,
                    "end_sample_exclusive": end, "available_t_s": end / sr,
                    "deg": read["deg"] if read else None,
                    "deg_raw": read["deg"] if read else None,
                    "gccphat": dict(read, available_t_s=end / sr) if read else None,
                    "r": None, "w": None, "ghost_deg": None, "ghost_r": None})
    return out


SRC_KEEP = 3          # arrivals extracted per millisecond. There is never only one after the room answers.
SRC_SPAN_MS = 8       # milliseconds followed from the burst: past the 6.4 ms echo, inside the ~40 ms fusion window
SRC_SEP_DEG = 10.0    # two peaks closer than this are one arrival
SRC_BURST_DB = 15.0   # the voice BURSTS out of the silence; this is how far over the pre-onset floor


def onset_sources(x, baseline_m, onset_s, sr=SR, band=MS1_BAND,
                  span_ms=SRC_SPAN_MS, keep=SRC_KEEP, sep_deg=SRC_SEP_DEG, burst_db=SRC_BURST_DB):
    """EVERY ARRIVAL IN EACH MILLISECOND, FOLLOWED (Jay, 2026-10-06).

    THE ONSET IS NOT THE BURST. The gate hands over a window that begins in silence; the voice bursts
    out of it a little later. That burst is found INSIDE the gate's own window -- the gate still owns
    the window, nothing is searched for outside it.

    THERE IS NEVER ONE SOURCE. From the burst, the direct arrives alone for about a millisecond --
    1 ms is 34 cm of excess path and a directionally distinct reflection needs far more. After that
    every millisecond carries the direct AND its reflections together, arriving 1-4 ms behind (this
    room's echo_lag is 307 samples = 6.4 ms). So a single lag per millisecond is not a thing that
    exists to be computed: each window is extracted for `keep` arrivals and they are FOLLOWED.

    THE TALKER IS THE ONE THAT WAS THERE FIRST, not the loudest and not the one in any single
    millisecond. Nothing is decided in ms 0: tracks are grown across the span and the earliest-born
    track is the direct, its bearing the median of its own members.
    """
    from scipy.signal import butter, sosfiltfilt
    from numpy.lib.stride_tricks import sliding_window_view as swv
    n = sr // 1000
    L = int(np.ceil(baseline_m / C * sr)) + 2
    a0 = int(round(onset_s * sr))
    pre = int(0.30 * sr)
    lo = max(0, a0 - pre - L)
    hi = min(len(x), a0 + int((span_ms + 40) * sr / 1000.0) + L + 1)
    if hi - lo < 4 * n:
        return None
    seg = sosfiltfilt(butter(4, band, btype="band", fs=sr, output="sos"), x[lo:hi, :2], axis=0)
    m2 = (seg ** 2).mean(axis=1)
    o0 = a0 - lo

    # THE BURST. The floor is the quiet the gate handed over ahead of the voice; the burst is the
    # first millisecond that stands burst_db over it. Searched forward only, inside this window.
    fl = m2[max(0, o0 - pre):o0]
    floor = float(np.sqrt(np.median(fl))) if len(fl) > n else float(np.sqrt(m2[:max(n, 1)].mean()))
    thr = floor * (10.0 ** (burst_db / 20.0))
    burst = None
    for k in range(0, int(40 * sr / 1000.0), n // 4 or 1):
        j = o0 + k
        if j + n > len(seg):
            break
        if float(np.sqrt(m2[j:j + n].mean())) >= thr:
            burst = j
            break
    if burst is None:
        burst = o0

    lags = np.arange(2 * L + 1) - L
    lag_max = baseline_m / C * sr
    sep_lag = max(1, int(round(math.sin(math.radians(sep_deg)) * lag_max)))
    per_ms = []
    for m in range(span_ms):
        j = burst + m * n
        if j - L < 0 or j + n + L > len(seg):
            break
        u = seg[j:j + n, 0] - seg[j:j + n, 0].mean()
        V = swv(seg[j - L:j + n + L, 1], n)
        V = V - V.mean(axis=1, keepdims=True)
        den = np.sqrt((u * u).sum() * (V * V).sum(axis=1))
        c = np.where(den > 1e-20, (V @ u) / np.maximum(den, 1e-20), 0.0)
        c = np.where(np.abs(lags) <= lag_max, c, -9.0)
        found, cc = [], c.copy()
        for _ in range(keep):                     # EVERY arrival, not the argmax
            q = int(np.argmax(cc))
            if cc[q] <= -9.0:
                break
            found.append((int(q - L), float(c[q])))
            cc[max(0, q - sep_lag):q + sep_lag + 1] = -9.0
        per_ms.append(found)
    if not per_ms:
        return None

    # FOLLOW THEM. A peak joins the track whose lag it sits nearest, within sep_lag; otherwise it is
    # a new arrival, born at this millisecond -- which is what a reflection landing looks like.
    tracks = []
    for m, found in enumerate(per_ms):
        for lag, r in found:
            hit = None
            for tk in tracks:
                if abs(lag - tk["lag"]) <= sep_lag:
                    hit = tk
                    break
            if hit is None:
                tracks.append({"born": m, "lag": lag, "lags": [lag], "rs": [r], "ms": [m]})
            else:
                hit["lags"].append(lag); hit["rs"].append(r); hit["ms"].append(m)
                hit["lag"] = int(np.median(hit["lags"]))
    if not tracks:
        return None
    tracks.sort(key=lambda tk: (tk["born"], -max(tk["rs"])))     # ORDER, then quality -- never loudness
    def bear(tk):
        lag = float(np.median(tk["lags"]))
        return round(math.degrees(math.asin(max(-1.0, min(1.0, -(lag / float(sr)) * C / baseline_m)))), 2)
    direct = tracks[0]
    out = {"burst_ms": round((burst - o0) * 1000.0 / sr, 2),
           "deg": bear(direct), "r": round(float(np.median(direct["rs"])), 3),
           "n": len(direct["ms"]), "born": direct["born"],
           "sources": [{"deg": bear(tk), "born": tk["born"], "n": len(tk["ms"]),
                        "r": round(float(np.median(tk["rs"])), 3)} for tk in tracks[:4]]}
    later = [tk for tk in tracks[1:] if tk["born"] > direct["born"]]
    if later:
        g = later[0]
        out["ghost_deg"] = bear(g); out["ghost_born_ms"] = g["born"]
        out["ghost_r"] = round(float(np.median(g["rs"])), 3)
    return out


RECUR_LO_MS = -5      # speech is already up before t_s: measured +22 dB over floor at ms -5 on walk-210054
RECUR_HI_MS = 25      # past the 6.4 ms echo, inside the ~40 ms fusion window
RECUR_KEEP = 3        # arrivals kept per millisecond. There is never only one once the room answers.


def onset_recur(x, baseline_m, onset_s, sr=SR, band=MS1_BAND,
                lo_ms=RECUR_LO_MS, hi_ms=RECUR_HI_MS, keep=RECUR_KEEP, sep_deg=MS1_SEP_DEG):
    """THE DIRECTION THAT KEEPS COMING BACK (Jay, 2026-10-06).

    One millisecond holds several arrivals, so no single millisecond decides anything -- ms 0 at
    walk-210054 21.82 s reads -33.1 while the talker is at +48.6, and the correct +50.7 appears at
    ms -5, -2, +1, +2, +7, +8 and +9 with r up to 0.98. The talker is the bearing that RECURS; a
    reflection recurs too but less consistently, and noise appears once and is gone.

    So: 1 ms windows across the span, every arrival kept, votes binned by lag and weighted by their
    own correlation. Order and persistence decide, never loudness. Scored against the fixtures' own
    true_deg: 3.5 deg median error on walk-210054, 4.8 on walk-212347.

    THE SPAN REACHES BACK. t_s is the gate's rewound onset and the voice is often already up before
    it -- +22 dB over the floor five milliseconds earlier on walk-210054 -- so looking backward is
    not optional. gate_t_s is the later DECISION time and reads 12 dB quieter; it is the wrong anchor.

    `w` is the winning bin's summed correlation and it is the confidence: the endfire failures
    (+-72.9) carry 6-12 against 14-22 for the reads that land inside 5 degrees.
    """
    from scipy.signal import butter, sosfiltfilt
    from numpy.lib.stride_tricks import sliding_window_view as swv
    n = sr // 1000
    L = int(np.ceil(baseline_m / C * sr)) + 2
    a0 = int(round(onset_s * sr))
    lo = max(0, a0 + lo_ms * n - 4 * L)
    hi = min(len(x), a0 + hi_ms * n + 4 * L)
    if hi - lo < 4 * n:
        return None
    seg = sosfiltfilt(butter(4, band, btype="band", fs=sr, output="sos"), x[lo:hi, :2], axis=0)
    off = a0 - lo
    lag_max = baseline_m / C * sr
    sep = max(1, int(round(math.sin(math.radians(sep_deg)) * lag_max)))
    lags = np.arange(2 * L + 1) - L
    votes = {}
    for k in range(lo_ms, hi_ms):
        j = off + k * n
        if j - L < 0 or j + n + L > len(seg):
            continue
        u = seg[j:j + n, 0] - seg[j:j + n, 0].mean()
        V = swv(seg[j - L:j + n + L, 1], n)
        V = V - V.mean(axis=1, keepdims=True)
        den = np.sqrt((u * u).sum() * (V * V).sum(axis=1))
        c = np.where(den > 1e-20, (V @ u) / np.maximum(den, 1e-20), 0.0)
        c = np.where(np.abs(lags) <= lag_max, c, -9.0)
        cc = c.copy()
        for _ in range(keep):
            q = int(np.argmax(cc))
            if cc[q] <= -9.0:
                break
            votes.setdefault(int(round((q - L) / float(sep))), []).append((q - L, float(c[q])))
            cc[max(0, q - sep):q + sep + 1] = -9.0
    if not votes:
        return None
    ranked = sorted(votes.items(), key=lambda kv: -sum(r for _, r in kv[1]))
    def bear(items):
        lag = float(np.median([l for l, _ in items]))
        return round(math.degrees(math.asin(max(-1.0, min(1.0, -(lag / float(sr)) * C / baseline_m)))), 2)
    main = ranked[0]
    out = {"deg": bear(main[1]), "votes": len(main[1]),
           "w": round(sum(r for _, r in main[1]), 2)}
    for b, items in ranked[1:]:
        if abs(bear(items) - out["deg"]) >= sep_deg:
            out["ghost_deg"] = bear(items)
            out["ghost_w"] = round(sum(r for _, r in items), 2)
            break
    return out
