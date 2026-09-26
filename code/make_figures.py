# -*- coding: utf-8 -*-
"""Figures 1-8 for the IJAMT manuscript, all drawn from pabhs_results.json and
plc_verify_results.json (Figure 1 and 3 are schematics). 300 dpi PNG + TIFF.

    python make_figures.py
"""
import json
import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle, Circle
from PIL import Image

import pabhs_model as M

R = json.load(open("pabhs_results.json"))
V = json.load(open("plc_verify_results.json"))
OUT = "figures"
os.makedirs(OUT, exist_ok=True)
DPI = 300
plt.rcParams.update({"font.size": 8.5, "axes.labelsize": 9, "axes.titlesize": 9.5,
                     "legend.fontsize": 7.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
                     "font.family": "DejaVu Sans", "axes.linewidth": 0.8})
BLUE, RED, GREEN, GREY, ORANGE, PURPLE = "#1b6ca8", "#c1553b", "#3f8f4a", "#7a7a7a", "#c98a1b", "#6a4c93"


def save(fig, name):
    """300 dpi PNG for embedding in the manuscript; 600 dpi TIFF for separate upload
    (Springer's minimum for combination artwork, i.e. charts with text)."""
    png = os.path.join(OUT, name + ".png")
    fig.savefig(png, dpi=DPI, bbox_inches="tight")
    tif = os.path.join(OUT, name + ".tif")
    fig.savefig(tif, dpi=600, bbox_inches="tight")
    plt.close(fig)
    Image.open(tif).convert("RGB").save(tif, dpi=(600, 600), compression="tiff_lzw")
    print(name)


def box(ax, x, y, w, h, text, col, fs=7.2, ls="-"):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.04",
                                lw=1.1, ls=ls, edgecolor=col, facecolor=col + "18"))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs)


def arrow(ax, a, b, col="#555555", ls="-", rad=0.0, lw=1.0, style="-|>"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=9, lw=lw, color=col,
                                 ls=ls, shrinkA=3, shrinkB=3, connectionstyle="arc3,rad=%.2f" % rad))


# ------------------------------------------------------------------ Figure 1
fig, ax = plt.subplots(figsize=(8.2, 5.2))
ax.set_xlim(0, 13.6); ax.set_ylim(0, 8.4); ax.axis("off")
# drum
ax.add_patch(Rectangle((1.2, 1.3), 1.8, 5.6, fc="#e9e9e9", ec=GREY, lw=1.2))
ax.text(2.1, 4.1, "coke drum\n(~28 m × 6 m)", ha="center", va="center", fontsize=7.4, rotation=90)
for y, lab in ((7.05, "top head\n32 bolts"), (1.15, "bottom head\n48 bolts")):
    ax.add_patch(Rectangle((1.0, y - 0.15), 2.2, 0.3, fc=BLUE + "33", ec=BLUE, lw=1.1))
    ax.text(0.9, y, lab, ha="right", va="center", fontsize=6.8)
ax.add_patch(Rectangle((3.0, 2.25), 0.6, 0.35, fc=BLUE + "33", ec=BLUE, lw=1.1))
ax.text(3.3, 2.0, "feed inlet\n12 bolts", ha="center", va="top", fontsize=6.6)
# subsystems
box(ax, 5.6, 7.05, 2.9, 0.75, "A  orbital bolt runner(s)\n(1, 2 or 4 torque heads)", BLUE)
box(ax, 5.6, 5.75, 2.9, 0.75, "B  bolt-management\ncarousel", BLUE)
box(ax, 5.6, 4.45, 2.9, 0.75, "C  counterbalanced\npneumatic head manipulator", BLUE)
box(ax, 5.6, 1.35, 2.9, 0.75, "A/B/C at bottom head\nand feed inlet (as above)", BLUE, ls="--")
box(ax, 9.4, 5.75, 3.0, 1.05, "D  sequence/interlock PLC\n(hazardous-area rated)\ntorque–angle record per bolt", PURPLE)
box(ax, 9.4, 3.9, 3.0, 0.7, "gas detection (2oo3)\n+ surface temperature", RED)
box(ax, 9.4, 7.35, 3.0, 0.6, "plant instrument air", GREY)
box(ax, 12.45, 5.75, 1.9, 1.05, "HMI (grade)\ncontrol room\nDCS: start/stop,\nstatus", GREY, fs=6.6)
for y in (7.05, 5.75, 4.45):
    arrow(ax, (7.05, y), (7.9, 5.75), col=PURPLE, rad=0.0)
arrow(ax, (9.4, 4.25), (9.4, 5.22), col=RED)
arrow(ax, (7.9, 7.35), (7.05, 7.1), col=GREY)
arrow(ax, (10.9, 5.75), (11.5, 5.75), col=GREY, style="<|-|>")
arrow(ax, (4.15, 7.05), (3.2, 7.05), col=BLUE)
arrow(ax, (4.15, 1.35), (3.2, 1.2), col=BLUE)
arrow(ax, (4.15, 4.45), (3.05, 6.6), col=BLUE, rad=0.2)
ax.text(6.8, 0.35, "Personnel: none inside the hazard zone during routine operation (design intent); "
        "supervisor at grade HMI or control room.", ha="center", fontsize=6.8, color="#444444")
save(fig, "figure1_architecture")

# ------------------------------------------------------------------ Figure 2
fig = plt.figure(figsize=(8.6, 3.9))
ax = fig.add_subplot(1, 2, 1, projection="polar")
n = 48
seq = M.legacy_star(n)
th = [2 * math.pi * i / n for i in range(n)]
ax.plot(th + [th[0]], [1] * (n + 1), color=GREY, lw=0.6)
order = {b: k + 1 for k, b in enumerate(seq)}
for i in range(n):
    col = ORANGE if (i % (n // 4)) == 0 else BLUE
    ax.plot(th[i], 1, "o", ms=4.3, color=col)
    ax.text(th[i], 1.17, str(order[i]), ha="center", va="center", fontsize=5.4)
for a, b in zip(seq[:8], seq[1:9]):
    ax.annotate("", xy=(th[b], 0.93), xytext=(th[a], 0.93),
                arrowprops=dict(arrowstyle="->", lw=0.7, color=RED, connectionstyle="arc3,rad=0.25"))
ax.set_ylim(0, 1.3); ax.set_yticks([]); ax.set_xticks([])
ax.set_title("A   48-bolt legacy star sequence\n(first eight moves in red; orange = one 4-head group)",
             fontsize=8.2, pad=10)
ax2 = fig.add_subplot(1, 2, 2)
names = ["top head", "bottom head", "feed inlet"]
S = R["sequences"]
xs = np.arange(3)
w = 0.2
vals = [[S[k]["travel_circ_perD"] for k in names], [S[k]["travel_star_perD"] for k in names],
        [S[k]["travel_star_2runners_perD"] for k in names],
        [R["sequences_travel_4heads_perD"][k] for k in names]]
labs = ["circular pass", "star pass, 1 head", "star pass, 2 heads", "star pass, 4 heads"]
cols = [GREEN, RED, ORANGE, BLUE]
for j, (v, l, c) in enumerate(zip(vals, labs, cols)):
    ax2.bar(xs + (j - 1.5) * w, v, w, label=l, color=c)
ax2.set_xticks(xs); ax2.set_xticklabels(["top (32)", "bottom (48)", "feed (12)"])
ax2.set_ylabel("rail travel per pass / bolt-circle diameter")
ax2.set_title("B   Travel per tightening pass", loc="left", fontweight="bold")
ax2.legend(frameon=False)
ax2.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
save(fig, "figure2_sequence")

# ------------------------------------------------------------------ Figure 3
fig, ax = plt.subplots(figsize=(7.6, 4.6))
ax.set_xlim(0, 12); ax.set_ylim(0, 7.4); ax.axis("off")
P = {"IDLE": (1.0, 6.3), "ATMOS_CHECK": (3.4, 6.3), "UNBOLT": (6.0, 6.3), "HEAD_OPEN": (8.5, 6.3),
     "OPEN": (10.9, 6.3), "GASKET": (10.9, 4.2), "HEAD_CLOSE": (8.5, 4.2), "BOLT": (6.0, 4.2),
     "LEAK_TEST": (3.4, 4.2), "AWAIT_SIGNOFF": (1.0, 4.2), "CLOSED": (1.0, 2.3),
     "HOLD": (6.0, 2.1), "ESD_SAFE": (9.7, 1.4)}
colr = {"HOLD": ORANGE, "ESD_SAFE": RED, "CLOSED": GREEN, "OPEN": GREEN}
for k, (x, y) in P.items():
    box(ax, x, y, 2.0 if len(k) > 9 else 1.6, 0.62, k.replace("_", " "), colr.get(k, PURPLE), fs=6.8)
E = [("IDLE", "ATMOS_CHECK", "start"), ("ATMOS_CHECK", "UNBOLT", "gas OK"),
     ("UNBOLT", "HEAD_OPEN", "0 engaged\n+ confirm"), ("HEAD_OPEN", "OPEN", ""),
     ("OPEN", "GASKET", "decoked;\nstart"), ("GASKET", "HEAD_CLOSE", "0 engaged\n+ confirm"),
     ("HEAD_CLOSE", "BOLT", "aligned"), ("BOLT", "LEAK_TEST", "all n pass\ntorque AND angle"),
     ("LEAK_TEST", "AWAIT_SIGNOFF", "leak OK"), ("AWAIT_SIGNOFF", "CLOSED", "sign-off")]
def half(k):
    return (2.0 if len(k) > 9 else 1.6) / 2


for a, b, lab in E:
    (x1, y1), (x2, y2) = P[a], P[b]
    if y1 == y2:
        sgn = 1 if x2 > x1 else -1
        arrow(ax, (x1 + sgn * half(a), y1), (x2 - sgn * half(b), y2), col="#444444")
    else:
        sgn = 1 if y2 > y1 else -1
        arrow(ax, (x1, y1 + sgn * 0.31), (x2, y2 - sgn * 0.31), col="#444444")
    if lab:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.33, lab, ha="center", fontsize=5.9, color="#333333")
arrow(ax, (P["UNBOLT"][0] + 0.5, P["UNBOLT"][1] - 0.31), (P["HOLD"][0] + 0.5, P["HOLD"][1] + 0.31), col=ORANGE, ls="--", rad=-0.25)
arrow(ax, (P["BOLT"][0], P["BOLT"][1] - 0.31), (P["HOLD"][0], P["HOLD"][1] + 0.31), col=ORANGE, ls="--")
ax.text(4.9, 2.75, "gas clearance lost", fontsize=6.0, color=ORANGE)
ax.text(9.7, 0.55, "ESD from any state; reset returns to IDLE, and\nATMOS CHECK resumes the "
        "interrupted phase (added)", ha="center", fontsize=6.0, color=RED)
fd = V["full_design"]["12"]; asp = V["as_specified"]["12"]
ax.text(0.1, 0.95, "Exhaustive check, 12-bolt flange: %d states, %d transitions, 0 safety "
        "violations.\nAs specified in the source (no resume rule): %d of %d states deadlocked; "
        "with resume: 0." % (fd["states"], fd["transitions"], asp["deadlocked_states"], asp["states"]),
        fontsize=6.4, color="#333333")
save(fig, "figure3_state_machine")

# ------------------------------------------------------------------ Figure 4
data = np.load("_mc_bolting_total.npy") / 3600.0
cfg = list(R["cycle"])
fig, ax = plt.subplots(figsize=(7.8, 3.8))
ax.axhspan(1.5, 2.5, color=GREEN, alpha=0.12, lw=0)
ax.text(len(cfg) + 0.45, 2.0, "source target\n1.5–2.5 h", fontsize=7, color=GREEN, va="center")
ax.axhspan(4.0, 6.0, color=GREY, alpha=0.12, lw=0)
ax.text(len(cfg) + 0.45, 5.0, "reported manual\n4–6 h", fontsize=7, color="#555555", va="center")
parts = ax.violinplot(list(data), positions=range(1, len(cfg) + 1), widths=0.8,
                      showmedians=True, showextrema=False)
for b in parts["bodies"]:
    b.set_facecolor(BLUE); b.set_alpha(0.45)
parts["cmedians"].set_color(RED)
ax.set_xticks(range(1, len(cfg) + 1))
SHORT = {"1 head, parallel flanges": "1 head\nparallel", "1 head, serial flanges": "1 head\nserial",
         "1 head, circular passes only": "1 head\ncircular only",
         "2 heads, parallel flanges": "2 heads\nparallel", "4 heads, parallel flanges": "4 heads\nparallel",
         "4 heads, 2 star passes": "4 heads\n2 star passes"}
ax.set_xticklabels([SHORT.get(c, c) for c in cfg], fontsize=7)
ax.set_ylabel("bolting time, opening + closing (h)")
ax.set_xlim(0.4, len(cfg) + 1.6)
ax.set_title("Monte Carlo bolting time (%d samples, all 92 bolts)" % R["n_mc"], loc="left",
             fontweight="bold")
for i, c in enumerate(cfg):
    p = R["cycle"][c]["p_bolting_le_2.5h"]
    ax.text(i + 1, data[i].max() * 1.02 if data[i].max() < 17 else 17, "P(≤2.5 h)\n= %.2f" % p,
            ha="center", fontsize=6.4)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "figure4_cycle_time")

# ------------------------------------------------------------------ Figure 5
fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.6), sharex=True)
LBL = {"v_carriage": "carriage speed", "t_torque": "torque time / pass", "check_passes": "check passes",
       "k_spacing": "bolt spacing (BCD)", "t_align": "alignment time", "t_engage": "engagement time",
       "t_transfer": "carousel transfer", "p_operator": "P(operator review)", "t_operator": "review duration",
       "t_release": "release time", "t_verify": "verify time", "t_move": "move overhead",
       "rpm_spin": "run-on/off speed", "t_breakout": "breakout time", "p_retry": "P(retry)",
       "d_frac": "bolt size"}
for ax, key, title in ((axs[0], "sensitivity_bolting_total", "A   One head per flange"),
                       (axs[1], "sensitivity_bolting_total_4heads", "B   Four heads per flange")):
    items = list(R[key].items())[:9][::-1]
    ax.barh([LBL.get(k, k) for k, _ in items], [v for _, v in items],
            color=[RED if v > 0 else BLUE for _, v in items])
    ax.axvline(0, color="#333333", lw=0.8)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_xlabel("Spearman rank correlation with bolting time")
    ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
save(fig, "figure5_sensitivity")

# ------------------------------------------------------------------ Figure 6
fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.5))
G = R["preload"]["torque_control_grid"]
for tool, col in ((0.02, BLUE), (0.05, ORANGE), (0.10, RED)):
    rows = [g for g in G if g["tool_pm"] == tool]
    axs[0].plot([100 * g["cv_K"] for g in rows], [100 * g["preload_cv"] for g in rows], "o-",
                color=col, label="tool accuracy ±%d %%" % round(100 * tool), ms=3.5)
axs[0].plot([5, 20], [5, 20], ":", color=GREY, lw=0.9)
axs[0].text(14, 12.2, "preload CV = nut-factor CV", fontsize=6.6, color=GREY, rotation=30)
axs[0].set_xlabel("nut-factor coefficient of variation (%)")
axs[0].set_ylabel("achieved preload CV (%)")
axs[0].set_title("A   Torque accuracy barely moves preload", loc="left", fontweight="bold")
axs[0].legend(frameon=False)
TA = R["preload"]["torque_angle"]
lab = ["K CV %d%%, θ-est. %d%%" % (round(100 * t["cv_K"]), round(100 * t["cv_theta"])) for t in TA]
x = np.arange(len(TA))
axs[1].bar(x - 0.2, [100 * t["outside10_before"] for t in TA], 0.4, color=RED, label="torque control only")
axs[1].bar(x + 0.2, [100 * t["outside10_after"] for t in TA], 0.4, color=GREEN,
           label="with torque–angle re-torque")
axs[1].set_xticks(x); axs[1].set_xticklabels(lab, rotation=35, ha="right", fontsize=6.4)
axs[1].set_ylabel("bolts outside ±10 % of target preload (%)")
axs[1].set_title("B   Angle channel is what narrows it", loc="left", fontweight="bold")
axs[1].legend(frameon=False, fontsize=6.8)
for a in axs:
    a.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
save(fig, "figure8_preload")

# ------------------------------------------------------------------ Figure 7
fig, ax = plt.subplots(figsize=(6.2, 3.6))
Mx = np.linspace(0.5, 20, 200)
for c, col in ((0.0, RED), (0.5, ORANGE), (0.8, BLUE), (0.9, GREEN), (0.95, PURPLE)):
    F = M.SF * (1 - c) * Mx * 1000 * 9.81
    bore = np.sqrt(4 * F / (math.pi * M.P_AIR * M.ETA)) * 1000
    ax.plot(Mx, bore, color=col, lw=1.6, label="counterbalance %d %%" % round(100 * c))
ax.axhline(320, color="#333333", ls="--", lw=1)
ax.text(19.8, 330, "largest ISO 15552 bore (320 mm)", ha="right", fontsize=7)
ax.set_xlabel("head mass (t)  —  not given in the source; swept")
ax.set_ylabel("single-cylinder bore at 6 bar, SF 1.5 (mm)")
ax.set_title("Pneumatic lift is feasible only with counterbalance", loc="left", fontweight="bold")
ax.legend(frameon=False, fontsize=7)
ax.set_ylim(0, 900)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "figure9_manipulator")

# ------------------------------------------------------------------ Figure 8
F = R["fmea"]
fig, ax = plt.subplots(figsize=(7.6, 4.2))
lab = [f["mode"] for f in F][::-1]
rpn = [f["RPN"] for f in F][::-1]
sev = [f["S"] for f in F][::-1]
cols = [RED if s >= 9 else (ORANGE if s >= 7 else BLUE) for s in sev]
ax.barh(range(len(F)), rpn, color=cols)
ax.set_yticks(range(len(F))); ax.set_yticklabels(lab, fontsize=6.6)
for i, (r_, s_) in enumerate(zip(rpn, sev)):
    ax.text(r_ + 2, i, "RPN %d  (S=%d)" % (r_, s_), va="center", fontsize=6.2)
ax.set_xlabel("risk priority number, S × O × D")
ax.set_title("Design FMEA (author-scored; red: S ≥ 9, orange: S 7–8)", loc="left", fontweight="bold")
ax.set_xlim(0, max(rpn) * 1.35)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "figure10_fmea")

# ------------------------------------------------------------------ Figure 6
O = np.load("_mc_opt.npy") / 3600.0          # [bolting|complete, config, sample]
names6 = ["1 head\n(baseline)", "A  4 heads\n1 carousel", "B  + 4 transfer\nchannels",
          "C  + 2 star\npasses", "D  + optimised\nsequence", "E  + pipelined\nservicing"]
fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.8), sharey=True)
for ax, k, title in ((axs[0], 0, "A   Bolting time, 92 bolts"),
                     (axs[1], 1, "B   Complete operation (open + close)")):
    ax.axhspan(0, 2.5, color=GREEN, alpha=0.10, lw=0)
    ax.axhline(2.5, color=GREEN, lw=1.0, ls="--")
    parts = ax.violinplot(list(O[k]), positions=range(1, 7), widths=0.8, showmedians=True,
                          showextrema=False)
    for b in parts["bodies"]:
        b.set_facecolor(BLUE if k == 0 else PURPLE); b.set_alpha(0.45)
    parts["cmedians"].set_color(RED)
    for i in range(6):
        med = np.median(O[k][i])
        ax.text(i + 1, min(O[k][i].max() + 0.25, 12.6), "%.2f h\nP≤2.5 h: %.2f" % (med, np.mean(O[k][i] <= 2.5)),
                ha="center", fontsize=5.9)
    ax.set_xticks(range(1, 7)); ax.set_xticklabels(names6, fontsize=6.3)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
axs[0].set_ylabel("time (h)")
axs[0].set_ylim(0, 13.5)
axs[1].text(6.45, 2.62, "2.5 h", color=GREEN, fontsize=7, ha="right")
fig.tight_layout()
save(fig, "figure6_optimisation")

# ------------------------------------------------------------------ Figure 7
FMAP = R["feasibility_map"]
fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.4))
heads, chans = [1, 2, 4], [1, 2, 4]
for ax, sp, title in ((axs[0], 3, "A   Legacy procedure (3 star passes)"),
                      (axs[1], 2, "B   Two star passes (needs qualification)")):
    Z = np.array([[FMAP["%d,%d,%d" % (sp, h, c)]["p_le_2.5h"] for c in chans] for h in heads])
    im = ax.imshow(Z, cmap="RdYlGn", vmin=0, vmax=1, origin="lower", aspect="auto")
    for i, h in enumerate(heads):
        for j, c in enumerate(chans):
            v = FMAP["%d,%d,%d" % (sp, h, c)]
            ax.text(j, i, "%.2f\n%.2f h" % (v["p_le_2.5h"], v["median"]), ha="center", va="center",
                    fontsize=7.2, color="black")
            if v["p_le_2.5h"] >= 0.9:
                ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec="black", lw=1.6))
    ax.set_xticks(range(3)); ax.set_xticklabels(chans)
    ax.set_yticks(range(3)); ax.set_yticklabels(heads)
    ax.set_xlabel("bolt-transfer channels per flange")
    ax.set_ylabel("torque heads per flange")
    ax.set_title(title, loc="left", fontweight="bold", fontsize=8.6)
cb = fig.colorbar(im, ax=axs, fraction=0.03, pad=0.02)
cb.set_label("P(bolting ≤ 2.5 h)")
fig.text(0.01, -0.03, "Outlined cells: P ≥ 0.90.", fontsize=7, color="#444444")
save(fig, "figure7_feasibility")
