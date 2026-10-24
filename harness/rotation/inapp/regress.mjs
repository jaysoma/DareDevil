// Brief H's regression driver (2026-10-24): a Conductor stream (JSONL, regress.py) read by a CdrRange the way Voice's
// MathPass.mjs reads it -- frames held until the utterance is confirmed, cut at the gate's onset, then handed to
// estimate() with onset_idx, cdrf and the bearing stamped -- and, per utterance, what CdrRange drew.
//
//     node harness/rotation/inapp/regress.mjs <CdrRange.js> <stream.jsonl> [<stream.jsonl> ...]
//
// Prints one JSON line per stream: { stream, utts: [{ utt, onset_s, S, corr, facing, contrast, n_free, n_face, draws }] }
// S is the range statistic read at 0.5 s (dB; corr is the 2 s correction, 0 unless turned), draws every value of u the
// dot took while the utterance's frames were read. Each utterance is stamped with its own bearing (37 deg from the last), so
// the pool (POOL_DEG 0, off) never joins: its gate is |deg - pool deg| <= POOL_DEG, which two EQUAL bearings still
// pass. MathPass stamps the bearing's own read; its gate on showing a range (RANGE_HOLD_DEG) is MathPass's, not CdrRange's.
import fs from 'node:fs';

export function loadScheme(path) {
  return new Function(fs.readFileSync(path, 'utf8') + '\nreturn RangeScheme;')();
}

export function read(Scheme, items) {
  const inst = new Scheme(), utts = [];
  let cur = null, rec = null;
  const drain = () => {
    for (const f of cur.pending.splice(0)) {
      const before = inst.u;                                    // a draw is a change of the scheme's own u on this frame
      inst.estimate({ t: f.t, track: { onset_idx: cur.utt, cdrf: f.cdrf, onset_deg: ((cur.utt * 37) % 360) - 180 } });
      if (Number.isFinite(inst.u) && inst.u !== before) rec.draws.push([f.t, inst.u]);
      const c = inst.cur;
      rec.S = c ? Scheme._free(c.free) : null;
      rec.corr = c && c.corr !== undefined ? c.corr : null;
      rec.facing = inst.facing({ track: { onset_idx: cur.utt } });
      rec.contrast = typeof inst.facingContrast === 'function' ? inst.facingContrast({}) : null;
      rec.n_free = c ? c.free.n : 0; rec.n_face = c && c.face ? c.face.n : 0;
    }
  };
  for (const it of items) {
    if (it.to === 'render') {
      if (it.event === 'open') {
        cur = { utt: it.utt, confirmed: !it.provisional, pending: [] };
        rec = { utt: it.utt, onset_s: it.onset_s, S: null, corr: null, facing: null, contrast: null, n_free: 0, n_face: 0, draws: [] };
        utts.push(rec);
      } else if (it.event === 'onset' && cur && it.utt === cur.utt) {
        cur.confirmed = true; rec.onset_s = it.onset_s;
        cur.pending = cur.pending.filter((f) => f.t >= it.onset_s);
        drain();
      } else if (it.event === 'close') cur = null;
    } else if (it.to === 'range' && cur && it.utt === cur.utt) {
      cur.pending.push(...it.frames);
      if (cur.confirmed) drain();
    }
  }
  return utts;
}

if (process.argv[1] && process.argv[1].endsWith('regress.mjs')) {
  const [schemePath, ...streams] = process.argv.slice(2);
  for (const s of streams) {
    const Scheme = loadScheme(schemePath);                      // a fresh class per tape: the opener lives on the class
    const items = fs.readFileSync(s, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
    console.log(JSON.stringify({ stream: s, utts: read(Scheme, items) }));
  }
}
