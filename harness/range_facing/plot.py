#!/usr/bin/env python3
"""Brief 20's figure: the law per dEchorate setting, r_c against echo time, facing per band (LOCATA), the probe's r_c.
usage: plot.py <summary.json> <sim_summary.json> <out.png>
"""
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt    # noqa: E402

BLUE, ORANGE, GRAY, INK, MUTED = '#2a78d6', '#eb6834', '#8a8a85', '#1f1f1e', '#6b6b66'


def style(ax, title, xl, yl):
    ax.set_title(title, loc='left', fontsize=10, color=INK)
    ax.set_xlabel(xl, fontsize=9, color=MUTED); ax.set_ylabel(yl, fontsize=9, color=MUTED)
    ax.tick_params(labelsize=8, colors=MUTED)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color('#cfcfca')
    ax.grid(alpha=0.25, lw=0.6)


def ticks(ax, xs, ys):
    from matplotlib.ticker import FixedLocator, NullLocator
    for axis, v in ((ax.xaxis, xs), (ax.yaxis, ys)):
        axis.set_major_locator(FixedLocator(v)); axis.set_minor_locator(NullLocator())
        axis.set_ticklabels([f'{x:g}' for x in v])


def main():
    S = json.load(open(sys.argv[1])); M = json.load(open(sys.argv[2]))
    fig, axs = plt.subplots(2, 2, figsize=(10, 7.5))
    d = S['step1']['dechorate']; tv = S['step1_dechorate_rc_vs_t60']['ALL']
    rooms = sorted(d, key=lambda r: tv['t60_s'][r])
    t60 = [tv['t60_s'][r] for r in rooms]
    ax = axs[0, 0]
    ax.axhline(-20, color=GRAY, lw=1, ls='--'); ax.text(t60[0], -19.3, 'the law: -20', ha='left', fontsize=8, color=MUTED)
    ax.plot(t60, [d[r]['rir_drr']['ALL']['slope'] for r in rooms], 'o-', color=BLUE, lw=2, ms=6, label="RIRs' true DRR")
    ax.plot(t60, [d[r]['ALL']['slope'] for r in rooms], 's-', color=ORANGE, lw=2, ms=6, label='CDR, 155 mm pair (ALL band)')
    style(ax, 'a. dEchorate: dB per decade of distance, 11 settings', 'echo time T20 x 3 (s)', 'slope (dB / decade)')
    ax.set_ylim(-22, 0); ax.legend(fontsize=8, frameon=False, loc='lower right')
    ax = axs[0, 1]
    ax.loglog(t60, [tv['rir_rc_m'][r] for r in rooms], 'o-', color=BLUE, lw=2, ms=6, label=f"RIRs' DRR (log-log slope {tv['rir_rc_loglog_slope']})")
    ax.loglog(t60, [tv['cdr_rc_m'][r] for r in rooms], 's-', color=ORANGE, lw=2, ms=6, label=f"CDR (slope {tv['cdr_rc_loglog_slope']})")
    style(ax, 'b. dEchorate: r_c at slope -20 against echo time', 'echo time (s)', 'r_c (m)')
    ticks(ax, [0.15, 0.2, 0.3, 0.4, 0.6], [1, 1.5, 2, 3, 4, 6])
    ax.text(0.03, 0.04, 'Sabine, fixed volume: slope -0.5', transform=ax.transAxes, fontsize=8, color=MUTED)
    ax.legend(fontsize=8, frameon=False, loc='upper right')
    ax = axs[1, 0]
    bands = [('LF', 'LF (640 mm only)'), ('LF_raw', 'LF unfloored'), ('MF', 'MF'), ('HF', 'HF'), ('ALL', 'ALL')]
    for k, (pair, col, off) in enumerate((('160mm', BLUE, -0.18), ('640mm', ORANGE, 0.18))):
        fr = S['step3'][pair]['facing_regression']
        xs = [i + off for i, (b, _) in enumerate(bands) if b in fr]
        ys = [fr[b]['facing_away_db'] for b, _ in bands if b in fr]
        lo = [fr[b]['facing_away_db'] - fr[b]['facing_away_ci95'][0] for b, _ in bands if b in fr]
        hi = [fr[b]['facing_away_ci95'][1] - fr[b]['facing_away_db'] for b, _ in bands if b in fr]
        ax.bar(xs, ys, width=0.34, color=col, label=f'{pair[:-2]} mm pair', edgecolor='white', lw=2)
        ax.errorbar(xs, ys, yerr=[lo, hi], fmt='none', ecolor=INK, lw=1, capsize=3)
    ax.set_xticks(range(len(bands))); ax.set_xticklabels([n for _, n in bands], fontsize=8)
    style(ax, 'c. LOCATA: CDR change from facing the array to facing away', '', 'dB at fixed distance (95% CI)')
    ax.axhline(0, color='#cfcfca', lw=1); ax.legend(fontsize=8, frameon=False, loc='lower left')
    ax = axs[1, 1]
    rows = [r for r in M['rows'] if r['noise_db'] == 20.0]
    sizes = sorted({r['size'] for r in rows}, key=lambda s: [x['rc_true'] for x in rows if x['size'] == s][0])
    mk = dict(zip(sizes, 'os^D'))
    for s in sizes:
        g = [r for r in rows if r['size'] == s]
        ax.plot([r['rc_true'] for r in g], [r['rc_probe'] for r in g], mk[s], color=BLUE, ms=7, mfc='white', mew=1.6, label=s)
    lim = [0.25, 6]
    ax.loglog(lim, lim, color=GRAY, lw=1, ls='--'); ax.text(4.2, 4.6, 'y = x', fontsize=8, color=MUTED)
    ticks(ax, [0.3, 0.5, 1, 2, 3, 5], [0.3, 0.5, 1, 2, 3, 5])
    style(ax, "d. Simulated rooms: the announcement's r_c (noise 20 dB down)", "talkers' true r_c (m)", 'probe r_c (m)')
    ax.legend(fontsize=8, frameon=False, loc='upper left')
    fig.tight_layout()
    fig.savefig(sys.argv[3], dpi=130, facecolor='white')


if __name__ == '__main__':
    main()
