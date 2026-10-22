"""THE CONDUCTOR'S EARS: WHEN IS IN MF, WHERE IS IN HF (Jay, 2026-10-11: "We use MF for onset then?" -- "If you can
implement that MF HF for when and where, it will be a really good story to tell with this demo if it works").

Nothing upstream decides anything: no segmentation gate, no recogniser stamp, no record file. The Conductor hands every
span of audio it streams to this, in order, and gets back the decisions it makes. Angle then reads its 5 ms from each
onset in HF (3-8 kHz), whose short wavelengths are what make a sharp precedence read. This decides only WHEN.

WHY MF (measured 2026-10-11, walk-203939): in MF (600 Hz-1.1 kHz) his speech starts stand 25-33 dB above his loudest
footstep within their first 300 ms, and footsteps never rise above the room at all. In HF the footsteps come within
0-11 dB of his starts, and his soft starts ("Okay", "I", "And", "I'm") make no HF attack -- the HF attacks on that tape
were twelve footsteps, two phone sounds and one mid-sentence syllable, and none of his six starts.

MF CLIMBS, IT DOES NOT JUMP: a voice builds over tens of ms, so no single millisecond clears a running maximum. The room
is therefore measured BEFORE the climb, and the onset is found by walking back down it:

    MF            CAUSAL 4th-order Butterworth band-pass, state carried span to span (nothing looks ahead); each
                  millisecond's energy over both capsules, in dB
    THE ROOM      the loudest MF millisecond of the ROOM_MS window that ends CLIMB_MS before now
    CONFIRMED     MF this millisecond is CONFIRM_DB above that room
    THE ONSET     walked back from there, millisecond by millisecond, to where MF left the room: the first millisecond
                  above it. It opens a fresh utterance (every onset is one -- Jay).
    RE-ARMED      after REARM_MS of MF back at that room -- a pause between phrases makes a new utterance, a gap
                  between words does not
    A CLOSE       CLOSE_MS of MF back at the room: the utterance ends where that quiet began (min_off, the old gate's
                  one second)
    A FLICKER     MF above that room for fewer than HOLD_MS in a row neither counts as quiet nor resets the count
                  (Jay, 2026-10-21: "No matter what I do, it JUST WILL NOT MOVE TO POSITION 2" -- walk-194940's pauses
                  each held 1-6 single milliseconds up to 2.7 dB over the stored level, so the count never reached 200 and
                  one utterance ran 26 s across three positions; a 5, 10 or 20 ms hold breaks it at the same places)

An onset is confirmed at most CLIMB_MS after it began, plus the span it arrived in.
"""
from collections import deque

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
MS = SR // 1000
MF_HZ = (600, 1100)
ROOM_MS = 200
CLIMB_MS = 100
CONFIRM_DB = 10.0
REARM_MS = 200
CLOSE_MS = 1000
HOLD_MS = 10


def settings():
    return {'when': 'MF', 'mf_hz': list(MF_HZ), 'room_ms': ROOM_MS, 'climb_ms': CLIMB_MS, 'confirm_db': CONFIRM_DB,
            'rearm_ms': REARM_MS, 'close_ms': CLOSE_MS, 'hold_ms': HOLD_MS, 'where': 'HF 3-8 kHz (Angle)'}


class Attacks:
    """Fed the audio in order; returns the decisions each span makes, [('open' | 'close', frame48), ...]."""

    def __init__(self):
        self.sos = butter(4, MF_HZ, btype='bandpass', fs=SR, output='sos')
        self.z = np.zeros((2, self.sos.shape[0], 2))           # the filter's state, per capsule
        self.mf = deque(maxlen=ROOM_MS + CLIMB_MS)             # the levels of the last ms, nothing else
        self.carry = np.zeros((0, 2))                          # filtered samples short of a whole millisecond
        self.i = 0                                             # the next millisecond
        self.armed = True
        self.room = None                                       # the room the open utterance began in (dB)
        self.quiet = 0                                         # ms in a row MF has been back at that room
        self.above = 0                                         # ms in a row MF has been over it (a flicker, under HOLD_MS)
        self.speaking = False

    def feed(self, left, right):
        l, r = np.asarray(left, dtype=np.float64), np.asarray(right, dtype=np.float64)
        yl, self.z[0] = sosfilt(self.sos, l, zi=self.z[0])
        yr, self.z[1] = sosfilt(self.sos, r, zi=self.z[1])
        y = np.concatenate([self.carry, np.stack([yl, yr], axis=1)])
        k = len(y) // MS
        out = []
        for j in range(k):
            i = self.i
            self.i += 1
            e = 10 * np.log10((y[j * MS:(j + 1) * MS] ** 2).sum() + 1e-9)
            if self.room is not None:                          # an utterance has opened: is MF back at its room?
                if e <= self.room:
                    self.quiet, self.above = self.quiet + 1, 0
                else:                                          # a flicker neither counts nor resets; a sound does
                    self.above += 1
                    if self.above >= HOLD_MS:
                        self.quiet = 0
                if self.quiet >= REARM_MS:
                    self.armed = True
                if self.speaking and self.quiet >= CLOSE_MS:
                    out.append(('close', (i - CLOSE_MS + 1) * MS))
                    self.speaking = False
            if self.armed and len(self.mf) == ROOM_MS + CLIMB_MS:
                levels = list(self.mf)
                room = max(levels[:ROOM_MS])                   # the window that ends CLIMB_MS before now
                if e >= room + CONFIRM_DB:
                    start = i                                  # walk back down the climb to where MF left the room
                    for back, v in enumerate(reversed(levels[ROOM_MS:]), 1):
                        if v <= room:
                            break
                        start = i - back
                    out.append(('open', start * MS))
                    self.armed, self.room, self.quiet, self.speaking, self.above = False, room, 0, True, 0
            self.mf.append(e)
        self.carry = y[k * MS:]
        return out
