"""Brief G's figures, from numbers.json: the pooling curve and the per-utterance call through the continuous turns."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'     # dataviz reference palette, slots 1-3 (validated)
INK, MUTED, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'


def _axes(a):
    a.set_facecolor(SURF)
    for s in ('top', 'right'):
        a.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        a.spines[s].set_color(MUTED)
    a.tick_params(colors=MUTED, labelsize=9)
    a.grid(axis='y', color=GRID, lw=0.8)
    a.set_axisbelow(True)


def draw(N, out):
    P = N['pooling']['curve']
    xs = sorted(float(k) for k in P)
    get = lambda k: P[str(k) if str(k) in P else (str(int(k)) if str(int(k)) in P else k)]
    fig, a = plt.subplots(figsize=(8, 4.6), facecolor=SURF)
    _axes(a)
    for lvl in (70, 75):
        a.axhline(lvl, color=MUTED, lw=1, ls=(0, (4, 3)))
        a.text(7.35, lvl, f'{lvl}%', color=MUTED, fontsize=9, va='center')
    y1 = [get(x)['bal'] for x in xs]; y2 = [get(x)['bal_all_stops_with_this_much'] for x in xs]
    a.plot(xs, y1, color=BLUE, lw=2, marker='o', ms=7, mec=SURF, mew=2)
    a.plot(xs, y2, color=ORANGE, lw=2, marker='o', ms=7, mec=SURF, mew=2)
    a.text(xs[-1] - 0.1, y1[-1] + 1.6, N['pooling']['population'].split(' (')[0].replace('stops with at least 7 s of speech',
           'stops with 7 s+ of speech'), color=INK, fontsize=9, ha='right')
    a.text(xs[-1] - 0.1, y2[-1] - 3.2, 'every stop with that much speech', color=INK, fontsize=9, ha='right')
    al = N['alone']
    bins = [k for k in ('0-1 s', '1-2 s', '2-4 s') if al[k]['stop_threshold']]
    bx = [al[k]['dur_mean'] for k in bins]; by = [al[k]['stop_threshold']['bal'] for k in bins]
    a.plot(bx, by, ls='none', marker='D', ms=8, color=AQUA, mec=SURF, mew=2)
    for k, x, y in zip(bins, bx, by):
        a.text(x + 0.12, y - 2.4, f"one utterance, {k} (n {al[k]['n']})", color=INK, fontsize=9)
    a.set_xlim(0, 7.8); a.set_ylim(50, 90)
    a.set_xlabel('seconds of speech pooled', color=INK, fontsize=10)
    a.set_ylabel('balanced accuracy, facing vs turned (%)', color=INK, fontsize=10)
    a.set_title('The facing call against seconds of speech (fixed threshold, left out by walk)', color=INK, fontsize=11,
                loc='left')
    fig.tight_layout(); fig.savefig(out / 'pooling_curve.png', dpi=120, facecolor=SURF); plt.close(fig)

    T = N['turns']
    fig, ax = plt.subplots(len(T), 1, figsize=(10, 2.7 * len(T)), facecolor=SURF)
    for a, (walk, t) in zip(ax, T.items()):
        _axes(a)
        (c0, c1), (r0, r1) = t['circle'], t['ref']
        a.axvspan(r0, r1, color='#f0efec', lw=0)
        a.axvspan(c0, c1, color='#dcdad3', lw=0)
        a.text(c0 + 0.2, 0.97, 'turning a full circle', transform=a.get_xaxis_transform(), color=MUTED, fontsize=8, va='top')
        a.text(r0 + 0.2, 0.97, 'facing the phone', transform=a.get_xaxis_transform(), color=MUTED, fontsize=8, va='top')
        a.axhline(t['threshold'], color=MUTED, lw=1, ls=(0, (4, 3)))
        for u in t['utterances']:
            col = BLUE if u['call'] == 'facing' else ORANGE
            a.plot([u['t0'], u['t1']], [u['c'], u['c']], color=col, lw=3, solid_capstyle='round')
        lo = min(r0, c0) - 4; hi = c1 + 6
        vis = [u['c'] for u in t['utterances'] if lo <= u['t0'] <= hi]
        a.set_xlim(lo, hi); a.set_ylim(min(vis + [-6]) - 1, max(vis + [3]) + 2)
        a.set_title(f"{walk}: {t['dir']}", color=INK, fontsize=10, loc='left')
        a.set_ylabel('contrast (dB)', color=INK, fontsize=9)
    ax[0].plot([], [], color=BLUE, lw=3, label='called facing'); ax[0].plot([], [], color=ORANGE, lw=3, label='called turned')
    ax[0].plot([], [], color=MUTED, lw=1, ls=(0, (4, 3)), label=f"threshold {T[next(iter(T))]['threshold']:+.2f} dB")
    ax[0].legend(loc='lower left', fontsize=8, frameon=False, ncol=3)
    ax[-1].set_xlabel('tape time (s); one bar per utterance, at its own contrast', color=INK, fontsize=9)
    fig.tight_layout(); fig.savefig(out / 'continuous_turns.png', dpi=120, facecolor=SURF); plt.close(fig)
