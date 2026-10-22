r"""siri_gate.py -- every tape through SIRI'S OWN GATE, on the desktop JVM (2026-10-08).

Jay, 2026-10-08: "From now on, we ALWAYS run play tapes through Siri's JVM and the tape should go through the exact
same pathway as it would through the phone. Otherwise we'd be skirting around other issues that might exist
upstream." The desktop used to carry Python COPIES of the handset's gate (live_stream.LiveGate,
firstonset_replay.DesktopGate), and the copies drifted: a reopen rule the phone never had, and a 0.5 s silence edge
where the phone runs 1.0 s. Both copies are gone. Siri/gatejvm runs the handset's own GateCore.kt and SegSpeech.kt,
and its own C++ decimator (decimator.h, built as a DLL), over a tape; this module runs that and reads it back.

    python -m geonar.siri_gate [--jobs 4] [--force] tape ...

writes captures/geonar/<tape>/siri_gate.json -- every pass the gate made, and every edge (open: the onset frame and
the pass that decided it; close: the end frame and the pass that decided it), in 48 kHz frames from the tape's start.

THE SETTINGS ARE ONE FILE, Siri/settings/gate.properties (Jay, 2026-10-08: "move the gate settings into somewhere in
Siri, where we don't include it with the build"). GateReplay reads it here; the handset reads the copy pushed beside its
models. There are no numbers in this module -- a second copy is how the desktop ran a 0.5 s silence edge while the
handset ran 1.0. The segmentation model is the handset's file byte for byte (sha256 220ad67c..., read off the phone).

THE GATE IS DIART'S FRONT END (Jay, 2026-10-08: "We try Diart's implementation"): a full 5 s window, one read per
0.5 s of audio, only the newest 0.5 s labelled and never relabelled, speech = any local speaker above 0.5 -- with the
phone's utterance rules on top. Identity (diart's embeddings + clustering) is not part of it. GateCore.kt says why.

WHAT STILL DIFFERS FROM THE HANDSET: the JVM (HotSpot, not ART), ONNX Runtime's desktop build of the same version
(1.27.0), and x86-64 floats instead of ARM64. Tapes are fed in 512-frame blocks, as the phone's tape replay feeds them.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / 'captures/geonar'
SIRI = ROOT.parent / 'Siri'
LIB = SIRI / 'gatejvm/build/install/gatejvm/lib'
DLL = SIRI / 'gatejvm/native/decimator_jni.dll'
MODEL = ROOT.parent / 'Whisper/models/diarize/segmentation-3.0.onnx'
JAVA = Path(r'C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot\bin\java.exe')
MAIN = 'com.jay.siri.gatejvm.GateReplayKt'
SETTINGS = SIRI / 'settings/gate.properties'
TOOL_VERSION = 4                           # GateReplay's output: 4 = the window from the ring (the tape), argmax
SR = 48000
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

# What the jar and the DLL are built from. A build older than its sources is not the code the handset runs.
KOTLIN_SOURCES = [SIRI / 'app/src/main/java/com/jay/siri/GateCore.kt',
                  SIRI / 'app/src/main/java/com/jay/siri/GateSettings.kt',
                  SIRI / 'app/src/main/java/com/jay/siri/SegSpeech.kt',
                  SIRI / 'gatejvm/src/main/kotlin/com/jay/siri/gatejvm/GateReplay.kt',
                  SIRI / 'gatejvm/src/main/kotlin/com/jay/siri/gatejvm/NativeDecimator.kt']
NATIVE_SOURCES = [SIRI / 'app/src/main/jni/mics/decimator.h', SIRI / 'gatejvm/native/decimator_jni.cpp']


def tape(name):
    return CAP / 'tapes' / (name + '.wav')


def out_path(name):
    return CAP / name / 'siri_gate.json'


def input_paths(name):
    """Everything siri_gate.json is a function of, for the fixture builders' fingerprints: the tape, the gate's build
    (jars, DLL), the model, the settings file, and this reader (last)."""
    return [tape(name), *sorted(LIB.glob('*.jar')), DLL, MODEL, SETTINGS, Path(__file__).resolve()]


PARAMS = {'tool_version': TOOL_VERSION}


def settings():
    """The gate's settings as the handset reads them: SETTINGS, key = value, # comments."""
    out = {}
    for line in SETTINGS.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, _, value = line.partition('=')
        value = value.strip()
        out[key.strip()] = float(value) if any(c in value for c in '.eE') else int(value)
    return out


def check_build():
    """Raise unless the jar and the DLL are newer than every source they are built from."""
    jar = LIB / 'gatejvm.jar'
    if not jar.is_file() or not DLL.is_file():
        raise RuntimeError('Siri gatejvm is not built: Siri\\gradlew :gatejvm:installDist, then gatejvm\\native\\build_dll.cmd')
    stale = [str(p) for p in KOTLIN_SOURCES if p.stat().st_mtime_ns > jar.stat().st_mtime_ns]
    stale += [str(p) for p in NATIVE_SOURCES if p.stat().st_mtime_ns > DLL.stat().st_mtime_ns]
    if stale:
        raise RuntimeError('Siri gatejvm is older than its sources (%s): rebuild with Siri\\gradlew :gatejvm:installDist '
                           'and gatejvm\\native\\build_dll.cmd' % ', '.join(stale))


def fresh(name):
    """siri_gate.json exists, is newer than everything it was made from, and was made with today's settings."""
    path = out_path(name)
    if not path.is_file():
        return False
    made = path.stat().st_mtime_ns
    if any(p.stat().st_mtime_ns > made for p in input_paths(name)[:-1]):
        return False
    rec = json.loads(path.read_text(encoding='utf-8'))
    return rec.get('version') == TOOL_VERSION and rec.get('settings') == settings()


def command(names):
    """One windowless JVM running the handset's gate over `names`, in order (GateReplay takes several tapes)."""
    for n in names:
        if not tape(n).is_file():
            raise FileNotFoundError(tape(n))
    return [str(JAVA), '-cp', str(LIB / '*'), MAIN, '--model', str(MODEL), '--dll', str(DLL), '--settings', str(SETTINGS),
            '--out-root', str(CAP), *[str(tape(n)) for n in names]]


def replay(name):
    """Run the handset's gate over one tape. Returns the record."""
    p = subprocess.run(command([name]), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
                       errors='replace', creationflags=NO_WINDOW)
    if p.returncode != 0:
        raise RuntimeError('GateReplay failed on %s (exit %s): %s' % (name, p.returncode,
                                                                     ' | '.join(p.stderr.strip().splitlines()[-4:])))
    return load(name, run=False)


def ensure(name):
    """siri_gate.json for a tape, made now if it is missing or stale."""
    check_build()
    if not fresh(name):
        replay(name)
    return load(name, run=False)


def load(name, run=True):
    """The tape's gate record, checked against the tape. With run=True it is made first if missing or stale."""
    if run:
        return ensure(name)
    rec = json.loads(out_path(name).read_text(encoding='utf-8'))
    with wave.open(str(tape(name))) as wav:
        frames = wav.getnframes()
    if rec.get('frames') != frames or rec.get('sr') != SR:
        raise ValueError('%s does not match its tape (%s frames at %s, tape has %s)' % (out_path(name), rec.get('frames'),
                                                                                       rec.get('sr'), frames))
    return rec


def gates_of(rec):
    """The record's gates in order: onset, decided, end, closed (48 kHz frames; end/closed None while open at the end)."""
    out = []
    for e in rec['edges']:
        if e['type'] == 'open':
            out.append({'onset': e['frame'], 'decided': e['at'], 'end': None, 'closed': None})
        else:
            out[-1].update(end=e['frame'], closed=e['at'])
    return out


def anomalies(rec):
    """What the handset's gate did that no utterance should: a gate whose onset falls before the previous gate's
    speech end (OVERLAP -- the same speech handed out twice), and a gate that ends before it starts (BACKWARD)."""
    gates = gates_of(rec)
    overlap = [k for k in range(1, len(gates)) if gates[k - 1]['end'] is not None and gates[k]['onset'] < gates[k - 1]['end']]
    backward = [k for k, g in enumerate(gates) if g['end'] is not None and g['end'] <= g['onset']]
    return {'gates': len(gates), 'overlap': overlap, 'backward': backward}


# SiriGate, the adapter that replayed a record to the two fixture builders (live_stream, firstonset_replay), went with
# them on 2026-10-09: the Conductor (geonar/conductor.py) walks the record's passes and edges itself, one pass at a time.


def main(argv=None):
    ap = argparse.ArgumentParser(description='Tapes through the handset gate on the desktop JVM')
    ap.add_argument('--jobs', type=int, default=4, help='JVMs at once, each running its share of the tapes in order')
    ap.add_argument('--force', action='store_true', help='replay even when siri_gate.json is fresh')
    ap.add_argument('names', nargs='+')
    a = ap.parse_args(argv)
    check_build()
    todo = [n for n in a.names if a.force or not fresh(n)]
    shares = [todo[i::a.jobs] for i in range(a.jobs) if todo[i::a.jobs]]
    print('##total %d' % len(shares), flush=True)
    # Started together, then waited on one by one: no threads, nothing polls. Each JVM's stderr goes to a temporary file
    # (a pipe nobody is reading yet could fill and stall it) and says why if it fails.
    logs = [tempfile.TemporaryFile() for _ in shares]
    procs = [subprocess.Popen(command(share), stdout=subprocess.DEVNULL, stderr=log, creationflags=NO_WINDOW)
             for share, log in zip(shares, logs)]
    failed = []
    for k, (share, proc, log) in enumerate(zip(shares, procs, logs), 1):
        proc.wait()
        log.seek(0)
        err = log.read().decode('utf-8', 'replace')
        log.close()
        if proc.returncode != 0:
            failed += share
            print('FAILED %s (exit %s): %s' % (', '.join(share), proc.returncode, ' | '.join(err.strip().splitlines()[-4:])),
                  flush=True)
        print('##progress %d/%d %d tapes' % (k, len(shares), len(share)), flush=True)
    totals = {'gates': 0, 'overlap': 0, 'backward': 0}
    for n in todo:
        if n in failed:
            continue
        an = anomalies(load(n, run=False))
        for key in totals:
            totals[key] += an[key] if key == 'gates' else len(an[key])
    print('%d replayed, %d failed, %d fresh; new runs: %d gates, %d overlap, %d backward' % (
        len(todo) - len(failed), len(failed), len(a.names) - len(todo), totals['gates'], totals['overlap'],
        totals['backward']), flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
