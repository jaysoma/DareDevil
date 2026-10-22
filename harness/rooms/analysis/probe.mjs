// Every 3 ms window of Angle2.readUtterance, gate or no gate, for trying counting rules offline (policies.py): a copy of
// the scheme with U_GATE_DB at -999 (every window read) and no clean rising edge ever found (so the scan runs to its
// end), each window's [ms from the true onset, dB over the floor, rise, share, deg].
// usage: node probe.mjs cuts.jsonl <schemes dir> > windows.jsonl
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [cutsPath, dir] = process.argv.slice(2);
let src = fs.readFileSync(path.resolve(dir, 'Angle2.mjs'), 'utf8');
for (const [a, b] of [[/U_GATE_DB = 10,/, 'U_GATE_DB = -999,'], [/U_RISE_DB = [\d.]+,/, 'U_RISE_DB = 999,']]) {
  if (!a.test(src)) throw new Error(`Angle2.mjs: no ${a}`);
  src = src.replace(a, b);
}
const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'probe-')), 'Angle2.mjs');
fs.writeFileSync(tmp, src);
const A2 = await import(pathToFileURL(tmp).href);
const i16 = (b64) => { const b = Buffer.from(b64, 'base64'); return new Int16Array(b.buffer, b.byteOffset, b.length / 2); };
for (const line of fs.readFileSync(cutsPath, 'utf8').split('\n')) {
  if (!line.trim()) continue;
  const c = JSON.parse(line), tr = [], t0 = c.true_onset ?? c.onset_sample;
  A2.readUtterance(i16(c.L), i16(c.R), c.onset_sample, c.baseline_m, tr);
  process.stdout.write(JSON.stringify({ t: c.truth_lateral, d: c.baseline_m, file: c.file,
    w: tr.map((x) => [Math.round((x.at - t0) / 48), +x.db.toFixed(1), +x.rise.toFixed(1), +x.share.toFixed(3), +x.deg.toFixed(1)]) }) + '\n');
}
