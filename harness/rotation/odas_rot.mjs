// odas_rot.mjs: whole-tape ODAS for the walks added to DareDevil after 10-21 (the rotation walks, 2026-10-23), exactly as
// odas_batch.mjs ran the first 29 -- today's geonar_odas.exe, tape_fixture.py's settings, the WHOLE tape, no stops, no
// truth -- except that a folded tape (its fold.json) gets its chord as the baseline instead of 157 mm. Runs in scratch
// only; captures/ is read, never written. Each run is compacted to <dataset>/tapes/<tape>/odas.json.
import { readFileSync, writeFileSync, mkdirSync, existsSync, rmSync, statSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
const CAP = 'C:/Projects/GithubRoot/Dictate/captures/geonar';
const EXE = 'C:/Projects/GithubRoot/Siri/app/src/main/jni/odas/host/build/geonar_odas.exe';
const SCR = 'C:/Users/Jay/AppData/Local/Temp/claude/c--Projects-GithubRoot-Dictate/1053048d-c015-46b3-b4dc-eb2fa62e4e49/scratchpad/odas_runs';
const OUT = 'C:/Projects/GithubRoot/geonar-truth/tapes';
const TAPES = process.argv.slice(2);
const SET = { fs: 48000, hop: 512, channels: 2, baseline_mm: 157.0, pots: 8, tracks: 8, theta_inactive: 0.6, ssl_hp_hz: 0 };
// The pair's spacing: 157 mm flat; folded, the chord 157 sin(fold / 2), as the Conductor's baseline_m works it out.
function baselineOf(w) {
  const f = `${CAP}/${w}/fold.json`;
  if (!existsSync(f)) return 157.0;
  const deg = Number(JSON.parse(readFileSync(f, 'utf8')).fold_deg ?? 180);
  return Math.round(1570 * Math.sin((deg * Math.PI) / 360)) / 10;
}
// one tape's PCM as interleaved s16le stereo: .raw as is, .wav from its data chunk
function pcmOf(w) {
  const raw = `${CAP}/tapes/${w}.raw`, wav = `${CAP}/tapes/${w}.wav`;
  if (existsSync(raw)) return { buf: readFileSync(raw), src: `tapes/${w}.raw` };
  const b = readFileSync(wav);
  let p = 12, fmt = null, data = null;
  while (p + 8 <= b.length) {
    const id = b.toString('ascii', p, p + 4), n = b.readUInt32LE(p + 4);
    if (id === 'fmt ') fmt = { ch: b.readUInt16LE(p + 10), sr: b.readUInt32LE(p + 12), bits: b.readUInt16LE(p + 22) };
    if (id === 'data') { data = b.subarray(p + 8, p + 8 + n); break; }
    p += 8 + n + (n & 1);
  }
  if (!fmt || !data || fmt.ch !== 2 || fmt.sr !== 48000 || fmt.bits !== 16) throw new Error(`${w}.wav is not 48 kHz 2-ch 16-bit: ${JSON.stringify(fmt)}`);
  return { buf: data, src: `tapes/${w}.wav` };
}
// ODAS writes concatenated, pretty-printed JSON objects; a top-level object opens and closes at column 0
function* objects(file) {
  const s = readFileSync(file, 'utf8'), re = /^\{[\s\S]*?^\}/gm;
  let m; while ((m = re.exec(s))) yield JSON.parse(m[0]);
}
const r3 = (v) => Math.round(v * 1000) / 1000, r1 = (v) => Math.round(v * 10) / 10;
for (const w of TAPES) {
  const t0 = Date.now();
  try {
    const bl = baselineOf(w), dir = `${SCR}/${w}`;
    rmSync(dir, { recursive: true, force: true }); mkdirSync(dir, { recursive: true });
    const { buf, src } = pcmOf(w); writeFileSync(`${dir}/in.raw`, buf);
    const r = spawnSync(EXE, ['--raw', `${dir}/in.raw`, '--out', dir, '--fs', '48000', '--hop', '512', '--channels', '2', '--baseline', bl.toFixed(1),
      '--pots', '8', '--tracks', '8', '--theta-inactive', '0.60'], { env: { ...process.env, MSYS_NO_PATHCONV: '1', GEONAR_SSL_HP_HZ: '0' }, maxBuffer: 1 << 26, windowsHide: true });
    if (r.status !== 0 || !existsSync(`${dir}/tracks.jsonl`) || !existsSync(`${dir}/pots.jsonl`)) throw new Error(`exit ${r.status}: ${String(r.stderr || '').slice(0, 200)}`);
    rmSync(`${dir}/in.raw`, { force: true }); rmSync(`${dir}/separated.raw`, { force: true });
    const pots = new Map();
    for (const o of objects(`${dir}/pots.jsonl`)) pots.set(o.timeStamp, (o.src || []).filter((s) => s.E > 0).map((s) => [r1(s.az_deg), r3(s.E)]));
    const frames = [];
    for (const o of objects(`${dir}/tracks.jsonl`)) {
      const tr = (o.src || []).filter((s) => s.id !== 0).map((s) => [s.id, r1(s.az_deg), r3(s.activity)]);
      frames.push([o.timeStamp, tr, pots.get(o.timeStamp) || []]);
    }
    mkdirSync(`${OUT}/${w}`, { recursive: true });
    writeFileSync(`${OUT}/${w}/odas.json`, JSON.stringify({
      name: w, generated: new Date().toISOString(), input: `Dictate/captures/geonar/${src}`,
      binary: `Siri/app/src/main/jni/odas/host/build/geonar_odas.exe (built ${statSync(EXE).mtime.toISOString().slice(0, 10)})`,
      settings: { ...SET, baseline_mm: bl }, hop_s: 512 / 48000,
      frames_format: '[timeStamp (hop index, from 1), tracks [[id, az_deg, activity]] (id 0 = empty slot, dropped), pots [[az_deg, E]] (E 0 dropped)]',
      az_convention: 'az_deg as the binary reports it: asin of x on the two-capsule pair, + toward one capsule (see poses.json mirror)',
      frames }));
    console.log(`${w} ok: ${frames.length} frames, baseline ${bl} mm, ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  } catch (e) { console.log(`${w} FAILED: ${e.message}`); }
}
console.log('ODAS BATCH DONE');
