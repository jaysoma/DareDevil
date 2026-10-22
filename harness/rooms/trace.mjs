// Every counted window of Angle2.readUtterance on chosen cuts: when it read (ms from the true onset), how far over the
// floor, how far over the window U_RISE_MS before (null for a version without it), which direction, which family; then the onset and reflection it published.
// usage: node trace.mjs cuts.jsonl <schemes dir> [truth_deg] [max cuts]     (JSON lines out, one per cut)
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [cutsPath, dir, want, max] = process.argv.slice(2);
const A2 = await import(pathToFileURL(path.resolve(dir, 'Angle2.mjs')).href);
const i16 = (b64) => { const b = Buffer.from(b64, 'base64'); return new Int16Array(b.buffer, b.byteOffset, b.length / 2); };
let n = 0;
for (const line of fs.readFileSync(cutsPath, 'utf8').split('\n')) {
  if (!line.trim()) continue;
  const c = JSON.parse(line);
  if (want !== undefined && want !== '' && c.truth_lateral !== Number(want)) continue;
  if (max && n++ >= Number(max)) break;
  const trace = [], r = A2.readUtterance(i16(c.L), i16(c.R), c.onset_sample, c.baseline_m, trace);
  const t0 = c.true_onset ?? c.onset_sample, ms = (s) => Math.round((s - t0) / 4.8) / 10;
  process.stdout.write(JSON.stringify({ file: c.file, truth: c.truth_lateral, onset: r && r.onset.deg, edge: r ? r.onset.edge ?? null : null, onset_at3_ms: r && ms(r.onset.at3),
    refl: r && r.refl && r.refl.deg, reads: trace.map((w) => [ms(w.at), Math.round(w.db), w.rise === undefined ? null : Math.round(w.rise * 10) / 10, Math.round(w.deg * 10) / 10, w.fam]) }) + '\n');
}
