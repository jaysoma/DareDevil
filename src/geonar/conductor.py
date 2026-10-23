"""THE CONDUCTOR (Jay, 2026-10-09): the one agent that directs the orchestra -- and plays none of it.

SEPARATION OF ROLES (Jay: "The whole idea is separation of roles"). The Conductor holds no math. It knows the session
and its floor, it is handed the gate's decisions as the gate makes them, and it decides what each instrument is given
and when: the bearing gets the utterance's raw audio from its onset as it comes, the range gets the CDR frames of that utterance as
they come -- CDR is a Python instrument (cdr_direct.CdrFreeStream) and stays one, so the Conductor runs it and hands
over what it makes. The math schemes themselves are the JavaScript ones in Voice, untouched ("We spent countless weeks
coming up with the correct math for bearing and range"); they take what is streamed to them and set Render's
properties directly. Nothing comes back here.

EVERY ITEM IS ADDRESSED (`to`): render (the session, the floor, each gate open and close), bearing (a packet), range
(CDR frames). Every item carries `at`, the tape time it was handed over.

PACED BY THE TAPE (Jay, 2026-10-09: Render is "completely blind to when they change", so a value has to arrive when it
applies). Live, the phone paces everything by speaking when it speaks. A tape goes the same path: play() hands the
Conductor each of the gate's passes when the tape reaches it -- one wait per pass, the only timer anywhere, and it is
the tape's. Before `from` (a resume or a seek) the passes are handed over at once, so the schemes downstream are given
everything that came before. A replay streams the recording the same way.

THE RULES (Jay: "Absolutely no buffers, no loops, no pollers, no daemons, no watchers, no spawning of threads"). No
audio is held: a span is read from the tape where it lies -- the tape stands in for Capture's ring -- and dropped once
handed over. Nothing asks again. The recording is written one line at a time as the items are made, and kept only if
the play reached the end.

TAPES ONLY FOR NOW (Jay: "We are not thinking about the actual live path from the phone for now"). The gate's
decisions are the tape's record (siri_gate.json, the phone's own gate replayed on the desktop JVM); a tape without a
current one is refused, never run here -- that would launch a process.
"""
import base64
import json
import math
import os
import re
import time
import uuid
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

from geonar import siri_gate
from geonar.attacks import Attacks, settings as attack_settings, MF_HZ, ROOM_MS, CLIMB_MS, CONFIRM_DB
from geonar.bandfloor import BandFloor, settings as floor_settings
from geonar.cdr_direct import CdrFreeStream, HOP as CDR_HOP, NFFT as CDR_NFFT

VERSION = 13                                 # 13: the range is handed only its utterance's first RANGE_READ_S of CDR
                                             #     frames, then nothing until the next utterance: one read, held
                                             # 12: the ears' quiet count rides through flickers (attacks.HOLD_MS), and
                                             #     the bearing is handed the pause before each read (BEARING_HISTORY)
                                             # 11: a recogniser begin inside an open utterance, snapped to its onset by
                                             #     the ears' own rule, starts a new bearing read (a 'phrase' item)
                                             # 10: and BEARING_HISTORY before that, which a bearing may look at but not
                                             #     read from; every open/onset says where the read starts
                                             # 9: the bearing's audio starts BEARING_PREROLL (one Angle frame step) before
                                             #    each onset
                                             # 8: every onset carries the band's floor per frequency (geonar/bandfloor.py),
                                             #    which the bearing's read is weighted by
                                             # 2: no math; items addressed to Render and the JS schemes; paced
                                             # 6: the Conductor finds its own onsets in the audio it streams
                                             #    (geonar/attacks.py): nothing upstream, no record file
                                             # 7: WHEN is MF, WHERE is HF -- the ears confirm an onset on MF's
                                             #    climb over the room and walk back to where it left it
                                             # 5: the onsets are the phone's own VAD (geonar/recognizer.py), handed on
                                             #    as they are -- no gate replay, no walk-back
                                             # 3: the bearing gets the utterance's audio as it comes, not one packet;
                                             #    the speech flag is true from the session's first sample
                                             # 4: audio at the floor was not handed to the bearing -- reverted the same day;
                                             #    the floor record carries its loudest chunk (ceiling_db); the gate's
                                             #    onset for the session's first utterance goes out as an `onset` item
SR = 48000
CAP = Path(__file__).resolve().parents[1] / 'captures/geonar'
RECORDING = 'conductor.jsonl'                # beside the tape's own files: captures/geonar/<tape>/conductor.jsonl

CHUNK = 512        # samples per chunk of audio handed on, as the phone's capture hands it over (the gate's passes fall on them)
# ONE FRAME BEFORE THE ONSET (Jay, 2026-10-12: "one frame before" -- "That actually gives us a confirmation on our angle. Or
# at least 2 contenders"). The ears confirm an onset on MF's climb, but the voice can reach the high band first: on
# walk-203939 at 37.7 s Jay's direction (+50 deg) was clean from 40 ms before the MF onset to 5 ms after it, then scattered.
# So the bearing is handed its audio from one of Angle's frame steps (512 samples, 10.7 ms) before each onset. That frame
# becomes the onset only if the next agrees with it (Angle's two-frames rule); room sound does not, and the onset stays
# where it was. Two steps back let the room's own two frames agree (walk-205606, 23.8 s read -1 deg), so it is one. The
# audio is there: an onset is named up to ~100 ms after it began, from the capture ring (live) or the file (a tape).
# This reverses "the app is handed the EXACT onset of speech, no more pre-hiss" (2026-10-10) by one frame, at Jay's go.
BEARING_PREROLL = 512
# AND A LITTLE HISTORY BEFORE THAT (Jay, 2026-10-12: "I'd need to see it" -- the rule that asks whether the frame ahead of
# the onset shows a NEW direction). Four more frame steps (42.7 ms) go to the bearing ahead of where it reads, so it can
# see which directions were already sounding; every open and onset item names where the read itself starts
# (read_from_sample), and the bearings start there. Nothing is read from the history.
BEARING_HISTORY = 20 * 512
# ...AND THE PAUSE BEFORE IT (2026-10-21, v12): twenty frame steps (213 ms) instead of four, so the bearing holds the pause
# the ears just measured before each onset; GccPhat weighs each frequency's vote by how far the voice stands above it
# (RangeMath/GccPhat.mjs PAUSE_MS). Still nothing is READ from the history: the read starts at read_from_sample.
# A NEW PHRASE INSIDE AN OPEN UTTERANCE (Jay, 2026-10-21: "What I actually want is for the recognizer to break up an
# existing utterance. So we keep what Conductor is doing, and while open, we use the Recognizer to trigger new angle (and
# range) measurement" -- then "maybe we leave range unchanged for now"). The phone's recogniser record (geonar/recognizer.py:
# each begin minus its latency) says a phrase starts NEAR a frame. Its timing is not the onset -- tested 10-21 on
# walk-225905, 170343 and 194940: re-begins in the middle of speech open 0.2-1.5 s after the voice, and opens before the
# voice read the gap and flip the lock -- so the ears find the onset near it: the first MF climb in the PHRASE_AFTER_MS
# after the open, else the latest one in the PHRASE_BEFORE_MS before it, by attacks.py's own rule run fresh. No climb: no
# new read. A new read never starts inside the half second the bearing is still reading (READ_SPAN: GccPhat's 47 frames
# of 512 from its read start). The close (attacks.CLOSE_MS, the one second) is untouched: a begin while no utterance is
# open does nothing.
PHRASE_AFTER_MS, PHRASE_BEFORE_MS = 500, 1500
READ_SPAN = 46 * 512 + 2048
# NO WARM-UP ON THE HISS (Jay, 2026-10-10: "the app is handed the EXACT onset of speech, no more pre-hiss"). Until today
# the CDR instrument's recursive PSDs (cdr_direct.ALPHA 0.92 per hop, ~130 ms memory) were run over WARM_S = 0.5 s
# BEFORE the onset so the first frames did not come from a cold estimator -- which folded half a second of room hiss
# into every utterance's first ~130 ms of range (walk-125621: the "direct" climbing -26 -> -9 dB over the first 100 ms,
# the dot landing far and retreating). The instrument now starts cold AT the onset, so nothing but the voice ever
# enters it; and because a coherence from one frame is 1 (CDR -> infinity), the frames of its first SETTLE_S are the
# instrument's own business and are not handed on. The first range frame is onset + SETTLE_S, from speech only.
PHONE_R = -1.1     # OFF (2026-10-11). The sign-of-correlation test was measured over 20 s blocks and implemented per
                   # 10 ms CHUNK, where correlation is dominated by the instantaneous phase of an off-axis talker: it
                   # fired 952 times across walk-205043, dropping real speech. -1.1 is below the range of a
                   # correlation, so it never fires. The replacement is not a correlation at all -- measured the same
                   # night, the two prompts are BALANCED across the pair (+0.8 dB, against up to +4.1 dB for humans),
                   # so no inter-channel test separates them; what does is absolute level, -10.8 to -12.9 dBFS against
                   # -17 to -45 for every human stretch, which is physical rather than tuned: a driver centimetres
                   # from the capsules cannot be matched by a talker a metre out.
SETTLE_S = 0.13    # ~ the PSD memory: ALPHA 0.92 per 10.7 ms hop
# ONE RANGE READ PER UTTERANCE, FROM ITS FIRST HALF SECOND (Jay, 2026-10-23: "for holds and general re-sampling ... just
# implement it"). Brief 21 (results/resample/report.md s3) scored range policies against LOCATA's tracked distance:
# the CDR of the utterance's first half second, held, was within 25% of the truth 51% of the time; sliding 0.5 s and
# 1 s windows managed 30-35%, and followed a real 20% change of distance about as often as a coin. People move about 5%
# a second; the CDR's scatter over half a second is far bigger. So the range is handed the frames whose window ENDS by
# onset + RANGE_READ_S (from SETTLE_S on, as before), then nothing more for that utterance: the range reads once and
# holds by construction. A new phrase inside the utterance doesn't reopen it (Jay, 2026-10-21: "maybe we leave range
# unchanged"). Render's notes say CdrRange sums the first 0.8 s; this makes that 0.5 s. None hands every frame, as v12.
RANGE_READ_S = 0.5
# THE ACTUAL ONSET (Jay, 2026-10-11: "it belongs in Conductor, so it hands Angle, Range and Orientation ACTUAL onset of
# speech" -- "implement the walkback all the way till the beginning of the handed frame"). The gate's edge is EARLY:
# segmentation-3.0 reads its 5 s window both ways and lifts the speech score on frames before the voice arrives, so on
# walk-205606 the voice rose 20-160 ms after the edge at seven of eight onsets, and the first 5 ms handed were the room.
# The Conductor walks back from speech the gate has confirmed: from the loudest millisecond between the edge and
# CONFIRM_MS after it, back one millisecond at a time while each stays within DIP_DB of it, through dips shorter than
# GAP_MS (a voice falls between its own glottal pulses, and for a closure inside a word), and stops at a drop that lasts
# GAP_MS: the room before the voice. The onset is the first millisecond after that drop. Never before the edge -- the
# beginning of the handed frame. NO FLOOR AND NO RUNNING LEVEL (Jay: "a running floor ... itself will be error-prone"):
# the reference is the voice's own loudest millisecond. Levels are the pre-emphasised (x[n] - 0.97 x[n-1]) energy of
# both capsules, so rumble is not a level.
CONFIRM_MS = 300    # the gate opens after this much of what it calls speech (min_on_ms)
DIP_DB = 12.0
GAP_MS = 20
# THE WALK-BACK IS OFF (Jay, 2026-10-11: "We use Android as our VAD, Conductor no longer needs any gymnastics"). The
# onsets come from the phone's recogniser (geonar/recognizer.py), which agreed with the voice to +-3 ms on walk-205606's
# clean onsets; the gate replay and _actual stay on disk, unused, until they are deleted.
WALK_BACK = False

# THE FLOOR: the session's first audio (Jay, 2026-10-09: "the very first anything is the floor. Conductor takes a note
# of it"), taken as it is -- its first 125 ms, read once, chunk by chunk; the loudest chunk is its ceiling. No window
# slides looking for a quieter stretch ("Another sliding window, searching for floor ...?").
# A rule that withheld chunks at the floor from the bearing lived here for a few hours on 2026-10-09 and was reverted
# (Jay: "trying to fight the hiss broke everything else"): the floor's ceiling from 125 ms leaked a hiss chunk every
# second or so, and widening it cut the first 75-300 ms of every onset. Known, not acted on.
FLOOR_WIN_S = 0.125


def tape_name(name):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', name or ''):
        raise ValueError('A recording name is required')
    return name


class TapeSource:
    """The tape where Capture's ring will be: a span is read where it lies when asked for, and nothing is kept."""

    def __init__(self, name):
        # THE RAW TAPE (Jay, 2026-10-11: "Ok let's not use the denoised version"). From 2026-10-09 the Conductor played
        # a tape's dfn.wav whenever DeepFilterNet had written one, but the gate never did: it decides on the raw tape. So
        # its onsets were placed on audio the readers never received. Gate and readers now hear the same tape.
        self.path = CAP / 'tapes' / (name + '.wav')
        self._wav = wave.open(str(self.path))
        if (self._wav.getframerate(), self._wav.getnchannels(), self._wav.getsampwidth()) != (SR, 2, 2):
            raise ValueError('%s: the Conductor reads the original 48 kHz stereo int16 capsules' % self.path.name)
        self.frames = self._wav.getnframes()
        meta = CAP / name / 'audio-input.json'
        order = json.loads(meta.read_text()).get('channel_order', 'LR') if meta.is_file() else 'LR'
        if order not in ('LR', 'RL'):
            raise ValueError('channel_order must be LR or RL')
        self.swap = order == 'RL'                 # the recording's swap, applied at every read

    def raw(self, start, n):
        """n frames from `start` as the capsules' own int16 (L, R), canonical order, or None outside the tape."""
        if start < 0 or n <= 0 or start + n > self.frames:
            return None
        self._wav.setpos(start)
        x = np.frombuffer(self._wav.readframes(n), dtype='<i2').reshape(-1, 2)
        return (x[:, 1], x[:, 0]) if self.swap else (x[:, 0], x[:, 1])

    def close(self):
        self._wav.close()


def level_db(left, right):
    """A span's level in dBFS -- what the Conductor knows of the floor."""
    l, r = left / 32768.0, right / 32768.0
    return 10 * math.log10(max(float(np.mean(l ** 2) + np.mean(r ** 2)) / 2, 1e-20))


def b64(samples):
    return base64.b64encode(np.ascontiguousarray(samples, dtype='<i2').tobytes()).decode('ascii')


class Conductor:
    """One session. Each of the gate's passes is handed over once, with the edges it made; what is due by it is handed
    on in it. `send` takes every item the moment it exists."""

    def __init__(self, name, source, baseline_m, send):
        self.name, self.src, self.baseline, self.send = name, source, baseline_m, send
        self.floor = None
        self.utt = None             # the open utterance: the handset's gate holds one at a time
        self.count = 0              # utterances opened so far: the next one's index
        self.live = False           # the gate has made its first decision
        self.now = 0
        # THE CONDUCTOR'S OWN EARS (Jay, 2026-10-11: "we don't need Segmentation-3.0 or actually anything upstream"):
        # every span it streams goes to the attack detector first, and its onsets and closes are the decisions.
        self.ears = Attacks()
        self.heard = 0              # the audio handed to the ears so far
        # THE BAND'S FLOOR, PER FREQUENCY (Jay, 2026-10-12: "Sounds good. Let's see if it works."): kept through the
        # silence, which only the Conductor hears, and handed over with every onset for the bearing's weighted read.
        self.band = BandFloor()
        # the recogniser's phrase opens for this tape, oldest first; none without a record (a live session, an unplayed tape)
        self.phrases = recognizer_opens(name)

    def _out(self, **item):
        item.setdefault('at', round(self.now / SR, 4))
        self.send(item)

    def open(self, **facts):
        """The session opens. THE SPEECH FLAG IS TRUE FROM THE FIRST SAMPLE (Jay, 2026-10-09: "We engineered it so the
        speech flag is true from the first moment. If speech flag is true, Conductor should be calling math functions,
        and render should have a dot"): the session's audio is an utterance from sample 0, handed to the math as it
        comes, while the gate spends its first 5 s warming up. Its first decision then sets the already true flag to true
        -- nothing changes, the utterance carries on -- or, hearing no speech, ends it."""
        self._out(to='render', event='session', tape=self.name, sr=SR, frames=self.src.frames,
                  duration_s=self.src.frames / SR, baseline_m=self.baseline, conductor=VERSION, at=0.0, **facts)
        self._open(0, 0, provisional=True)

    def _actual(self, frame, now):
        """The millisecond the voice arrives: walked back from the speech the gate confirmed to the drop before it, never
        before the edge it handed (see DIP_DB)."""
        ms = SR // 1000
        n = (min(now, frame + CONFIRM_MS * ms, self.src.frames) - frame) // ms
        if n < 2 or frame < 1:
            return frame
        pair = self.src.raw(frame - 1, n * ms + 1)              # one sample before the edge, for the pre-emphasis
        if not pair:
            return frame
        l, r = (np.asarray(x, dtype=np.float64) for x in pair)
        pl, pr = l[1:] - 0.97 * l[:-1], r[1:] - 0.97 * r[:-1]
        level = 10 * np.log10((pl ** 2 + pr ** 2).reshape(n, ms).sum(axis=1) + 1e-12)
        peak = int(np.argmax(level))
        bar = level[peak] - DIP_DB
        start, below = peak, 0
        for k in range(peak - 1, -1, -1):
            if level[k] >= bar:
                start, below = k, 0
            else:
                below += 1
                if below >= GAP_MS:
                    break
        return frame + start * ms

    def _open(self, onset, now, provisional=False, **extra):
        self.utt = {'index': self.count, 'onset': onset, 'read': max(0, onset - BEARING_PREROLL),
                    'sent': max(0, onset - BEARING_PREROLL - BEARING_HISTORY),
                    'provisional': provisional, 'cdr': CdrFreeStream(self.baseline), 'next': onset}
        self.count += 1
        self._out(to='render', event='open', utt=self.utt['index'], onset_s=onset / SR, decided_s=now / SR,
                  provisional=provisional, read_from_sample=max(0, onset - BEARING_PREROLL), **extra)

    def _close(self, end, now, **extra):
        self._due(self.utt, now, end=end)
        self._out(to='render', event='close', utt=self.utt['index'], end_s=end / SR, decided_s=now / SR, **extra)
        self.utt = None

    def _listen(self, now):
        """The audio since the last chunk, to the ears; what they decide, as edges. EVERY ONSET IS A FRESH UTTERANCE (Jay):
        one already open closes where the new one begins."""
        if now <= self.heard:
            return []
        pair = self.src.raw(self.heard, now - self.heard)
        self.heard = now
        if not pair:
            return []
        edges = []
        for kind, frame in self.ears.feed(*pair):
            if kind == 'open':
                if self.live and self.utt is not None:
                    edges.append({'type': 'close', 'frame': frame})
                edges.append({'type': 'open', 'frame': frame})
            else:
                edges.append({'type': 'close', 'frame': frame})
        return edges

    def step(self, now):
        """A chunk of audio has arrived (the tape's CHUNK, as the phone's capture would hand it over): the ears hear it
        first -- what they decide is a pass -- and while the flag is true, the math is handed it."""
        self.band.feed(self.src, now)
        edges = self._listen(now)
        if edges:
            return self.at(now, edges)
        self.now = now
        if self.floor is None and now >= FLOOR_WIN_S * SR:
            self._floor()
        if self.utt is not None:
            self._due(self.utt, now)
        self._phrases(now)

    def at(self, now, edges=()):
        """One of the gate's passes, at frame `now`, with the edges it made."""
        self.now = now
        if self.floor is None and now >= FLOOR_WIN_S * SR:
            self._floor()
        edges = list(edges)
        if not self.live:                       # the gate's first decision
            self.live = True
            if self.utt is not None and self.utt['provisional']:
                opens = [e for e in edges if e['type'] == 'open']
                if opens:                       # speech: the flag was already true -- nothing changes, the utterance
                    self.utt['provisional'] = False         # carries on ("set the already true flag to true")
                    # ...and THE GATE'S ONSET IS HANDED ON (2026-10-09): the first ms of speech, which the math has
                    # been walking from sample 0 for want of. The session's opening hiss anchored every range on
                    # walk-213150 (Jay: "the whole tape is anchored at the starting hiss"); from here the walk
                    # restarts at the voice. The flag never went false; the dot never left.
                    onset = self._actual(opens[0]['frame'], now) if WALK_BACK else opens[0]['frame']
                    self._out(to='render', event='onset', utt=self.utt['index'], onset_s=onset / SR,
                              onset_sample=onset, decided_s=now / SR, gate_onset_s=opens[0]['frame'] / SR,
                              floor_db=self.band.value(), read_from_sample=max(0, onset - BEARING_PREROLL))
                    self.utt['onset'] = onset
                    self.utt['read'] = max(0, onset - BEARING_PREROLL)
                    edges = edges[edges.index(opens[0]) + 1:]
                else:                           # no speech: the flag goes false here
                    self._close(now, now)
        for e in edges:
            if e['type'] == 'open':
                if self.utt is None:
                    self._open(self._actual(e['frame'], now) if WALK_BACK else e['frame'], now, gate_onset_s=e['frame'] / SR,
                               floor_db=self.band.value())
            elif self.utt is not None:
                self._close(e['frame'], now)
        if self.utt is not None:
            self._due(self.utt, now)
        self._phrases(now)

    def _phrases(self, now):
        """Recogniser opens whose search window has passed. One inside the open utterance, snapped to its onset, starts a
        new bearing read there (see PHRASE_AFTER_MS); the bearing already has the audio, so nothing is resent."""
        ms = SR // 1000
        while self.phrases and self.phrases[0] + PHRASE_AFTER_MS * ms <= now:
            p = self.phrases.pop(0)
            u = self.utt
            if u is None or u['provisional'] or p < u['onset']:
                continue
            onset = self._snap(p)
            if onset is None:
                continue
            read = max(0, onset - BEARING_PREROLL)
            if read < u['read'] + READ_SPAN:
                continue
            u['read'] = read
            self._out(to='render', event='phrase', utt=u['index'], onset_s=onset / SR, onset_sample=onset,
                      read_from_sample=read, recognizer_s=round(p / SR, 4), decided_s=now / SR)

    def _snap(self, p):
        """The onset near a recogniser open by the ears' own rule (geonar/attacks.py), or None: MF per millisecond over
        both capsules; a millisecond CONFIRM_DB over the room (the loudest of the ROOM_MS ending CLIMB_MS earlier), walked
        back to where MF left it. First after the open, then before it."""
        ms, settle = SR // 1000, 200                       # 200 ms for a fresh filter to settle
        lo = max(0, p - (PHRASE_BEFORE_MS + ROOM_MS + CLIMB_MS + settle) * ms)
        hi = min(self.src.frames, p + (PHRASE_AFTER_MS + 1) * ms)
        pair = self.src.raw(lo, hi - lo)
        if not pair:
            return None
        sos = butter(4, MF_HZ, btype='bandpass', fs=SR, output='sos')
        yl, yr = (sosfilt(sos, np.asarray(c, dtype=np.float64)) for c in pair)
        n = (hi - lo) // ms
        e = 10 * np.log10((yl[:n * ms].reshape(n, ms) ** 2).sum(1) + (yr[:n * ms].reshape(n, ms) ** 2).sum(1) + 1e-9)

        def climb(i):
            room = e[i - CLIMB_MS - ROOM_MS:i - CLIMB_MS].max()
            if e[i] < room + CONFIRM_DB:
                return None
            o = i
            for back in range(1, CLIMB_MS + 1):
                if e[i - back] <= room:
                    break
                o = i - back
            return o

        k, first = (p - lo) // ms, ROOM_MS + CLIMB_MS + settle
        after = range(max(k, first), min(k + PHRASE_AFTER_MS, n - 1) + 1)
        before = range(k - 1, max(k - PHRASE_BEFORE_MS, first) - 1, -1)
        for i in list(after) + list(before):
            o = climb(i)
            if o is not None:
                return lo + o * ms
        return None

    def _floor(self):
        win = min(int(FLOOR_WIN_S * SR), self.src.frames)
        l, r = self.src.raw(0, win)
        chunks = [level_db(l[s:s + CHUNK], r[s:s + CHUNK]) for s in range(0, win - CHUNK + 1, CHUNK)] or [level_db(l, r)]
        self.floor = {'level_db': round(level_db(l, r), 2), 'ceiling_db': round(max(chunks), 2), 'chunks': len(chunks),
                      'from_s': 0.0, 'to_s': win / SR}
        self._out(to='render', event='floor', **self.floor)


    # THE PHONE'S OWN VOICE IS NOT A TALKER (Jay, 2026-10-11: "always factor for initial ding -- this is general enough
    # to code into Conductor"). A session often opens with the handset speaking: walk-205043 says "Scanning heartbeat
    # signature" at 6.08 s and "Begin test recording" at 14.36 s. It is speech, so the gate opens on it; it comes from a
    # driver sitting between the capsules, so it is not a talker and every reading taken from it is nonsense -- on that
    # tape it read as the brightest thing on the recording (0.65 against a human maximum of 0.38) and would anchor a
    # range on a loudspeaker two centimetres away.
    #
    # THE TEST IS GEOMETRY, NOT LEVEL. A source out in the room reaches both capsules as the same wavefront, so L and R
    # correlate POSITIVELY at zero lag -- measured +0.43 to +0.61 across every human stretch of walk-205043. The phone's
    # own driver radiates into the two capsules through the body between them and arrives ANTI-correlated: that tape's
    # first 20 s, the stretch holding both prompts, measures -0.45. The sign of one correlation separates them, with no
    # threshold on loudness anywhere, which is what makes it general rather than tuned to one recording.
    def _phone_emitted(self, l, r):
        """True when a chunk arrives anti-correlated across the pair: the handset's own speaker, not the room."""
        if l is None or r is None or len(l) < 256:
            return False
        a = np.asarray(l, dtype=np.float64)
        b = np.asarray(r, dtype=np.float64)
        a -= a.mean(); b -= b.mean()
        da, db = math.sqrt(float(a @ a)), math.sqrt(float(b @ b))
        if da <= 0 or db <= 0:
            return False
        return (float(a @ b) / (da * db)) < PHONE_R

    def _due(self, u, now, end=None):
        """What this utterance's instruments are owed by `now`: the bearing its audio since the last pass, the range its
        new CDR frames.

        THE UTTERANCE'S AUDIO, AS IT COMES (Jay, 2026-10-09: "render the dot immediately and obviously the position should
        update continuously until the gate closes"). Each pass hands Bearing the raw pair from where the last one stopped
        to now -- from the gate's onset on the first, up to the gate's own backdated end on the close -- so the math
        reads the whole utterance in order. Nothing is held: the span is read off the tape where it lies.
        EVERYTHING IS HANDED (Jay, 2026-10-09, reverting the floor rule of earlier that day: "trying to fight the hiss
        broke everything else"): a chunk at the floor is handed like any other; the floor record is kept, not acted on."""
        upto = min(now if end is None else end, self.src.frames)
        if upto > u['sent']:
            pair = self.src.raw(u['sent'], upto - u['sent'])
            if pair:
                # the handset talking over itself: the span is skipped, and its CDR frames with it, so no reader ever
                # sees the phone as a talker. Recorded as an event so the page can show where it happened.
                if self._phone_emitted(pair[0], pair[1]):
                    u['phone_s'] = round(u['sent'] / SR, 3)
                    self._out(to='render', event='phone', utt=u['index'],
                              from_s=round(u['sent'] / SR, 3), to_s=round(upto / SR, 3))
                    u['next'] = max(u['next'], upto)          # its CDR frames are the phone's too
                else:
                    self._out(to='bearing', utt=u['index'], onset_sample=u['onset'], start_sample=u['sent'], sr=SR,
                              n=upto - u['sent'], baseline_m=self.baseline, L=b64(pair[0]), R=b64(pair[1]))
            u['sent'] = upto
        frames = []
        limit = u['onset'] + int(RANGE_READ_S * SR) if RANGE_READ_S else None
        while u['next'] + CDR_NFFT <= min(now, self.src.frames):
            if limit is not None and u['next'] + CDR_NFFT > limit:     # the range has its read: nothing more this utterance
                u['next'] = min(now, self.src.frames)
                break
            l, r = self.src.raw(u['next'], CDR_NFFT)
            direct, diffuse = u['cdr'].frame(np.stack([l, r], axis=1) / 32768.0)
            if u['next'] >= u['onset'] + int(SETTLE_S * SR):   # the settling frames are the instrument's own business
                cdrf = [round(10 * math.log10(max(float(v), 1e-30)), 4) for pair in zip(direct, diffuse) for v in pair]
                frames.append({'t': round((u['next'] + CDR_NFFT) / SR, 4), 'cdrf': cdrf})   # stamped at window END
            u['next'] += CDR_HOP
        if frames:
            self._out(to='range', utt=u['index'], frames=frames)

    def close(self, end):
        """Session end at frame `end`: an utterance still open is handed its last and closed there."""
        self.now = end
        if self.floor is None:
            self._floor()
        if self.utt is not None:
            self._due(self.utt, end)
            self._out(to='render', event='close', utt=self.utt['index'], end_s=end / SR, decided_s=end / SR,
                      open_at_end=True)
            self.utt = None
        self._out(to='render', event='end')


def gate_record(name):
    """No gate and no record any more (v6): the onsets are the Conductor's own (geonar/attacks.py)."""
    # NO RECORD ANY MORE (v6): the Conductor finds its own onsets in the audio as it streams it (geonar/attacks.py), so
    # every tape plays the moment it is loaded. Kept, returning None, because the relay's door still calls it.
    return None


def baseline_m(name):
    """The capsule spacing: physical geometry, never a calibration. 157 mm flat; a folded tape's chord from fold.json."""
    fold = CAP / name / 'fold.json'
    deg = float(json.loads(fold.read_text()).get('fold_deg', 180)) if fold.is_file() else 180.0
    return 0.157 * math.sin(math.radians(deg) / 2)


def recognizer_opens(name):
    """The phone recogniser's phrase opens for a tape (geonar/recognizer.py's record: each begin minus its latency), in
    tape frames, oldest first; [] when the tape has not been played through the phone."""
    path = CAP / name / 'recognizer.json'
    if not path.is_file():
        return []
    rec = json.loads(path.read_text(encoding='utf-8'))
    return sorted(int(e['frame']) for e in rec.get('edges', []) if e.get('type') == 'open')


def inputs_of(name):
    """What a recording is a function of: the tape, the ears (attacks.py), the band's floor (bandfloor.py), its geometry,
    this file, the CDR instrument and the recogniser's record (the phrases, v11)."""
    paths = [CAP / 'tapes' / (name + '.wav'), Path(__file__).resolve().parent / 'attacks.py',
             Path(__file__).resolve().parent / 'bandfloor.py', Path(__file__).resolve(),
             Path(__file__).resolve().parent / 'cdr_direct.py', CAP / name / 'audio-input.json', CAP / name / 'fold.json',
             CAP / name / 'recognizer.json']
    return [[p.name, p.stat().st_size, p.stat().st_mtime_ns] if p.is_file() else [p.name, None, None] for p in paths]


def recording_path(name):
    return CAP / tape_name(name) / RECORDING


def current(name):
    """The recording, if it was made from exactly today's inputs; else None."""
    path = recording_path(name)
    if not path.is_file():
        return None
    with path.open(encoding='utf-8') as fh:
        first = json.loads(fh.readline() or 'null')
    return path if first and first.get('conductor') == VERSION and first.get('inputs') == inputs_of(name) else None


class _Pace:
    """The tape's clock: the one wait in the system. Tape time `from_s` is now; anything earlier is due at once.
    It keeps the tape's pace and nothing else -- no sync with anyone's playback (Jay, 2026-10-09: "Forget the logic of
    trying to sync 'processing' with playback")."""

    def __init__(self, from_s):
        self.from_s, self.start = from_s, time.monotonic()

    def until(self, tape_s):
        ahead = (tape_s - self.from_s) - (time.monotonic() - self.start)
        if ahead > 0:
            time.sleep(ahead)


def play(name, send, from_s=0.0, paced=True):
    """Play a tape through the Conductor, paced by the tape, recording what it hands over. The recording is kept only
    if the play reaches the end; a reader that goes away (send raises) ends the play and the partial is dropped.
    Unpaced, the tape is played as fast as it computes -- ~100x real time (walk-125621, 152 s, in 1.4 s)."""
    name = tape_name(name)
    gate_record(name)                           # v6: no record; kept so the door that calls it stays one path
    source = TapeSource(name)
    target = recording_path(name)
    partial = target.with_name('%s.%s.partial' % (RECORDING, uuid.uuid4().hex[:8]))
    fh = partial.open('w', encoding='utf-8')
    kept = False
    try:
        def tee(item):
            fh.write(json.dumps(item, separators=(',', ':'), allow_nan=False) + '\n')
            send(item)
        conductor = Conductor(name, source, baseline_m(name), tee)
        conductor.open(gate={'version': 'attacks', 'settings': attack_settings(), 'floor': floor_settings()},
                       inputs=inputs_of(name))
        # THE TAPE ARRIVES IN CHUNKS, as the phone's capture hands it over, and the Conductor's own ears decide as each
        # one is heard: every chunk boundary, in order, one wait each.
        pace = _Pace(from_s)
        for now in range(CHUNK, source.frames + 1, CHUNK):
            if paced:
                pace.until(now / SR)
            conductor.step(now)
        if paced:
            pace.until(source.frames / SR)
        conductor.close(source.frames)
        fh.close()
        os.replace(partial, target)
        kept = True
    finally:
        source.close()
        if not kept:
            fh.close()
            partial.unlink(missing_ok=True)


def replay(name, send, from_s=0.0):
    """Stream a current recording the way it was made: each item when the tape reaches its `at`."""
    pace = _Pace(from_s)
    with recording_path(name).open(encoding='utf-8') as fh:
        for line in fh:
            item = json.loads(line)
            pace.until(item.get('at', 0.0))
            send(item)


def _progress(send):
    """What a processing reader is sent instead of the items: how far through the tape the play has got, about once
    per second of tape, and once at the end."""
    state = {'of': None, 'last': -1.0}

    def report(item):
        if item.get('event') == 'session':
            state['of'] = item.get('duration_s')
        at = item.get('at', 0.0)
        if at - state['last'] >= 1.0 or item.get('event') == 'end':
            state['last'] = at
            send({'to': 'render', 'event': 'progress', 'at': at, 'of': state['of']})
    return report


def _after(send, start_s):
    """A reader that only wants the tape from start_s on (Jay, 2026-10-11: "start the actual measuring after the
    prompts").

    IT FILTERS WHAT IS SENT, NOT WHAT IS PLAYED. The phone emits spoken prompts of its own -- walk-205043 says
    "Scanning heartbeat signature" at 6.08 s and "Begin test recording" at 14.36 s -- from a speaker between the
    capsules, so they arrive with near-zero delay between the mics and a direct-to-diffuse ratio no talker in the room
    can produce. A reader that takes them for speech anchors its range on the phone's own voice. Filtering here rather
    than in the play means the RECORDING stays complete (it is the tape's record, not one reader's view), the floor is
    still taken where it always was, and nothing in the Conductor's own walk changes.

    The session item always goes, since it carries the duration and the baseline. Everything else earlier than
    start_s is dropped -- including the gate's opens, so an utterance that began before the start never opens for
    this reader. Its later audio and CDR frames then arrive for an utterance the reader has no record of, which
    MathPass already ignores (it matches every item against the utterance it is holding), so the first utterance a
    reader sees is the first gate open AFTER the start."""
    if start_s <= 0:
        return send

    def gate(item):
        if item.get('to') == 'render' and item.get('event') == 'session':
            send(item)
        elif item.get('at', 0.0) >= start_s:
            send(item)
    return gate


def stream(name, send, from_s=0.0, process=False, start_s=0.0):
    """A tape to whoever is reading: its current recording paced by the tape, or a paced play that makes one.

    `process` is a tile's first click (Jay, 2026-10-09: "if a tile click has an unprocessed tape, just play it at 100x
    and scrollbar, pause/play, whatever are disabled. That will take no time, and then it can actually be played in
    real time"): an unrecorded tape is played at full speed into its recording, and the reader is sent only how far
    it has got -- "just have a progress bar and only start after processed"; the items themselves go to the recording,
    not down the wire. A recorded tape sends nothing and the stream ends at once."""
    name = tape_name(name)
    if process:
        if not current(name):
            play(name, _progress(send), 0.0, paced=False)     # the recording is always made whole
        return
    send = _after(send, start_s)
    if current(name):
        replay(name, send, from_s)
    else:
        play(name, send, from_s)
