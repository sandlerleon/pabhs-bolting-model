# -*- coding: utf-8 -*-
"""PABHS: simulation-based design evaluation of automated bolting and head handling for
a multi-flange pressure vessel (delayed-coking drum case study).

The white paper this derives from states performance targets (1.5-2.5 h for 92 bolts,
+/-2 % torque accuracy, zero personnel in the hazard zone) without the models behind
them. This script supplies those models and reports what they predict, including where
the targets do NOT follow.

  1. Geometry     bolt-circle diameter bracketed by a bolt-spacing rule (not given)
  2. Sequencing   ASME PCC-1-style legacy star pattern vs circular passes; carriage
                  travel computed from the actual sequence on a 360-degree rail
  3. Cycle time   Monte Carlo over per-step times (opening and closing separately),
                  one vs two runners per flange, serial vs parallel flanges
  4. Sensitivity  Spearman rank correlation of every sampled input with cycle time
  5. Admissibility  the per-bolt-pass time budget that the 2.5 h target implies
  6. Preload      torque accuracy vs nut-factor scatter; effect of torque-angle check
  7. Manipulator  pneumatic force budget vs head mass; counterbalance requirement
  8. FMEA         scored design FMEA, RPN ranking
  9. Exposure     automation coverage and hazard-zone person-hours

Every numerical input is an ASSUMPTION or a value stated in the source white paper,
labelled as such below. Nothing here is a measurement.

    python pabhs_model.py
"""
import json
import math

import numpy as np
from scipy.stats import spearmanr

SEED = 20260925
N_MC = 20000
rng = np.random.default_rng(SEED)

# ------------------------------------------------------------------ 1. case data
# From the source white paper (Table: bolted connections). Sizes are ranges.
FLANGES = {
    "top head":    {"n": 32, "d_mm": (48, 64), "head": True},
    "bottom head": {"n": 48, "d_mm": (48, 64), "head": True},
    "feed inlet":  {"n": 12, "d_mm": (36, 48), "head": False},
}
# ISO 261 coarse pitches (mm)
PITCH = {36: 4.0, 42: 4.5, 48: 5.0, 56: 5.5, 64: 6.0}
# ASSUMPTION: circumferential bolt spacing s = k*d, k in [2.5, 5]; the bolt-circle
# diameter is then D = n*s/pi. Wrench clearance sets the lower end, gasket-seating
# uniformity the upper; actual drawings were not available.
K_SPACING = (2.5, 5.0)


def bolt_circle(n, d_mm, k):
    return n * k * d_mm / 1000.0 / math.pi          # m


# ------------------------------------------------------------------ 2. sequencing
def legacy_star(n):
    """Legacy cross pattern for n divisible by 4: quartets at 90 degrees, quartets
    visited in bit-reversed order (the pattern family of ASME PCC-1 legacy sequences)."""
    assert n % 4 == 0
    q = n // 4
    bits = max(1, (q - 1).bit_length())
    def rev(i):
        return int(format(i, "0%db" % bits)[::-1], 2)
    order = sorted(range(q), key=lambda i: (rev(i) if rev(i) < q else q + i))
    seq = []
    for i in order:
        seq += [i, i + 2 * q, i + q, i + 3 * q]
    assert sorted(seq) == list(range(n))
    return seq


def circular(n):
    return list(range(n))


def travel_m(seq, n, D, runners=1):
    """Rail travel for one pass. With r equally spaced tool heads, bolts i, i+n/r, ...
    are worked together, so only one member of each group is visited."""
    m = n // runners
    seen, s2 = set(), []
    for b in seq:
        key = b % m
        if key not in seen:
            seen.add(key)
            s2.append(key)
    step = math.pi * D / n
    dist, moves = 0.0, 0
    for a, b in zip(s2, s2[1:]):
        k = abs(a - b) % n
        dist += min(k, n - k) * step            # shortest way round the rail
        moves += 1
    return dist, moves


# ------------------------------------------------------------------ 3. cycle model
# ASSUMED per-step time ranges (seconds), sampled uniformly. Order-of-magnitude values
# for pneumatic multiplier bolting; they are the inputs the sensitivity analysis ranks.
STEP = {
    "v_carriage":   (0.05, 0.20),   # m/s rail speed
    "t_move":       (1.0, 4.0),     # accel/settle overhead per indexing move
    "t_align":      (4.0, 15.0),    # laser/contact alignment to the nut
    "t_engage":     (3.0, 10.0),    # socket engagement
    "t_torque":     (10.0, 40.0),   # one torque pass on one bolt (to target)
    "t_breakout":   (10.0, 35.0),   # breakout on loosening
    "t_release":    (2.0, 6.0),     # reaction release and retract
    "t_verify":     (1.0, 3.0),     # PLC torque-angle window check
    "rpm_spin":     (20.0, 60.0),   # nut run-on / run-off speed (rev/min)
    "t_transfer":   (10.0, 35.0),   # bolt to/from carousel, per bolt
    "p_retry":      (0.005, 0.03),  # per bolt-pass: out-of-window, automatic retry
    "p_operator":   (0.0005, 0.005),# per bolt-pass: needs remote operator review
    "t_operator":   (300.0, 1200.0),# duration of one operator review
    "check_passes": (1, 3),         # circular check passes until no nut rotation
    "t_head":       (900.0, 1800.0),# head unlatch/lift/swing/lock (or reverse)
    "t_gasket":     (900.0, 2400.0),# gasket removal + face cleaning + placement, per flange
    "t_atmos":      (120.0, 600.0), # gas-clearance confirmation
    "t_leak":       (1200.0, 2700.0),# steam leak test
}
ENGAGE_LEN = 1.5                     # thread engagement length / d, for run-on turns
# Tightening passes (fraction of target torque) after run-on/snug:
TIGHTEN_STAR_PASSES = 3              # ~30 %, ~60 %, 100 % in star pattern
LOOSEN_STAR_PASSES = 1               # staged breakout in star pattern, then run-off


def sample():
    s = {}
    for k, (lo, hi) in STEP.items():
        if k == "check_passes":
            s[k] = rng.integers(lo, hi + 1, N_MC)
        else:
            s[k] = rng.uniform(lo, hi, N_MC)
    s["k_spacing"] = rng.uniform(*K_SPACING, N_MC)
    s["d_frac"] = rng.uniform(0, 1, N_MC)           # position within each flange's size range
    return s


def flange_times(f, s, runners=1, pattern="legacy", star_passes=TIGHTEN_STAR_PASSES):
    """Opening and closing bolting time (s) for one flange, vectorised over samples."""
    n = f["n"]
    d_lo, d_hi = f["d_mm"]
    d = d_lo + s["d_frac"] * (d_hi - d_lo)
    D = n * s["k_spacing"] * d / 1000.0 / math.pi
    p = np.interp(d, sorted(PITCH), [PITCH[k] for k in sorted(PITCH)])
    turns = ENGAGE_LEN * d / p
    t_spin = turns / s["rpm_spin"] * 60.0
    star = legacy_star(n) if pattern == "legacy" else circular(n)
    circ = circular(n)
    work = n // runners                                 # bolt stations visited per pass

    def pass_time(seq, t_tool):
        dist_unit, moves = travel_m(seq, n, 1.0, runners)   # distance scales with D
        per_station = s["t_align"] + s["t_engage"] + t_tool + s["t_release"] + s["t_verify"]
        # a station is done when all r heads are done: any head's retry/review delays it
        retry = (1 - (1 - s["p_retry"]) ** runners) * (s["t_engage"] + t_tool)
        oper = (1 - (1 - s["p_operator"]) ** runners) * s["t_operator"]
        travel = dist_unit * D / s["v_carriage"] + moves * s["t_move"]
        return work * (per_station + retry + oper) + travel

    # opening: staged breakout (star), then run-off + transfer to carousel (circular)
    t_open = LOOSEN_STAR_PASSES * pass_time(star, s["t_breakout"])
    t_open += pass_time(circ, t_spin) + n * s["t_transfer"]       # one carousel per flange
    # closing: transfer + run-on (circular), star torque passes, circular check passes
    t_close = pass_time(circ, t_spin) + n * s["t_transfer"]
    t_close += star_passes * pass_time(star, s["t_torque"])
    t_close += s["check_passes"] * pass_time(circ, s["t_torque"])
    return t_open, t_close, D, d


def cycle(s, runners=1, parallel=True, pattern="legacy", star_passes=TIGHTEN_STAR_PASSES):
    res = {}
    opens, closes = [], []
    for name, f in FLANGES.items():
        to, tc, D, d = flange_times(f, s, runners, pattern, star_passes)
        res[name] = {"open": to, "close": tc, "D": D, "d": d}
        opens.append(to)
        closes.append(tc)
    opens, closes = np.array(opens), np.array(closes)
    bolt_open = opens.max(0) if parallel else opens.sum(0)
    bolt_close = closes.max(0) if parallel else closes.sum(0)
    n_heads = sum(1 for f in FLANGES.values() if f["head"])
    n_fl = len(FLANGES)
    # head handling and gasket work: heads in parallel if flanges run in parallel
    heads = s["t_head"] * (1 if parallel else n_heads)
    gaskets = s["t_gasket"] * (1 if parallel else n_fl)
    full_open = s["t_atmos"] + bolt_open + heads
    full_close = gaskets + heads + bolt_close + s["t_leak"]
    res["bolting_open"], res["bolting_close"] = bolt_open, bolt_close
    res["bolting_total"] = bolt_open + bolt_close
    res["full_open"], res["full_close"] = full_open, full_close
    res["full_total"] = full_open + full_close
    return res


def pct(x, h=3600.0):
    x = np.asarray(x) / h
    return {"p05": round(float(np.percentile(x, 5)), 2),
            "median": round(float(np.median(x)), 2),
            "p95": round(float(np.percentile(x, 95)), 2)}


# ------------------------------------------------------------------ 6. preload
BOLT_SY = 724.0        # MPa, SA-193 B7 up to 64 mm (ASSUMED material)
TARGET_FRAC = 0.5      # ASSUMED target bolt stress as fraction of yield


def stress_area(d, p):
    return math.pi / 4.0 * (d - 0.9382 * p) ** 2       # mm^2, ISO 898-1


def preload_study():
    out = {"torque_kNm": {}}
    for d in (36, 42, 48, 56, 64):
        As = stress_area(d, PITCH[d])
        F = TARGET_FRAC * BOLT_SY * As                    # N
        out["torque_kNm"][str(d)] = {
            "As_mm2": round(As, 0), "F_kN": round(F / 1e3, 0),
            "T_K0.16": round(0.16 * F * d / 1e6, 2), "T_K0.20": round(0.20 * F * d / 1e6, 2)}
    n = 200000
    r = np.random.default_rng(SEED + 1)
    grid = []
    for cv_k in (0.05, 0.10, 0.15, 0.20):
        for tool in (0.02, 0.05, 0.10):
            e_tool = r.uniform(-tool, tool, n)
            K = 0.18 * (1 + r.normal(0, cv_k, n))
            F_rel = (1 + e_tool) * 0.18 / K                # achieved / intended preload
            grid.append({"cv_K": cv_k, "tool_pm": tool,
                         "preload_cv": round(float(np.std(F_rel) / np.mean(F_rel)), 4),
                         "frac_outside_10pct": round(float(np.mean(np.abs(F_rel - 1) > 0.10)), 4)})
    out["torque_control_grid"] = grid
    # torque-angle correction: angle after snug gives an independent preload estimate
    # with error cv_theta (joint/gasket stiffness uncertainty); bolts whose estimate is
    # outside +/-window are re-torqued to the angle-corrected target.
    ta = []
    for cv_k in (0.10, 0.15):
        for cv_theta in (0.03, 0.05, 0.08):
            e_tool = r.uniform(-0.02, 0.02, n)
            K = 0.18 * (1 + r.normal(0, cv_k, n))
            F = (1 + e_tool) * 0.18 / K
            F_hat = F * (1 + r.normal(0, cv_theta, n))
            flag = np.abs(F_hat - 1) > 0.10
            F_final = np.where(flag, F / F_hat, F)
            ta.append({"cv_K": cv_k, "cv_theta": cv_theta,
                       "flagged_frac": round(float(flag.mean()), 3),
                       "preload_cv_before": round(float(F.std() / F.mean()), 4),
                       "preload_cv_after": round(float(F_final.std() / F_final.mean()), 4),
                       "outside10_before": round(float(np.mean(np.abs(F - 1) > 0.10)), 4),
                       "outside10_after": round(float(np.mean(np.abs(F_final - 1) > 0.10)), 4)})
    out["torque_angle"] = ta
    return out


# ------------------------------------------------------------------ 7. manipulator
P_AIR = 0.6e6          # Pa, ASSUMED plant instrument-air supply (6 bar gauge)
ETA = 0.9              # cylinder force efficiency, ASSUMED
SF = 1.5               # lifting safety factor, ASSUMED
BORE_MAX = 0.320       # m, largest ISO 15552 standard bore


def manipulator():
    rows = []
    A_max = math.pi / 4 * BORE_MAX ** 2
    for M in (1, 2, 5, 10, 15, 20):
        W = M * 1000 * 9.81
        row = {"head_t": M}
        for c in (0.0, 0.5, 0.8, 0.9, 0.95):
            F = SF * (1 - c) * W
            bore = math.sqrt(4 * F / (math.pi * P_AIR * ETA))
            row["bore_mm_c%.2f" % c] = round(bore * 1000, 0)
        row["min_counterbalance"] = round(max(0.0, 1 - A_max * P_AIR * ETA / (SF * W)), 3)
        row["moment_kNm_at_2m"] = round(W * 2.0 / 1000, 1)
        rows.append(row)
    return rows


# ------------------------------------------------------------------ 8. FMEA
# Design FMEA, scored by the author on 1-10 scales (S severity, O occurrence with the
# stated control, D detection: 10 = undetectable). Expert judgement, not field data.
FMEA = [
    ("Gas detector fails to register residual hydrocarbons", "Sensor drift, fouling", "Bolting starts in flammable atmosphere", 10, 3, 5, "Redundant detectors (2oo3 voting), bump test before each cycle"),
    ("Head released with a bolt still engaged", "Engagement sensor false negative", "Head/flange damage, dropped load", 10, 2, 3, "Carousel count must equal n AND per-station sensor; interlock"),
    ("Manipulator loses air pressure under load", "Supply failure, hose rupture", "Uncontrolled head motion", 10, 3, 2, "Counterbalance carries static load; spring-applied mechanical lock"),
    ("Out-of-window preload not detected", "Nut-factor outlier, galled thread", "Gasket leak at restart", 8, 5, 4, "Torque-angle window per bolt; angle-corrected re-torque"),
    ("Socket fails to engage nut", "Misalignment, coke fouling of nut", "Bolt skipped, sequence stall", 5, 6, 2, "Laser/contact alignment; engagement proof before torque"),
    ("Carousel jam or mis-indexed slot", "Coke debris, bent stud", "Wrong bolt returned or stall", 6, 4, 3, "Slot presence sensing; bolt ID; stop on mismatch"),
    ("Carriage drive failure mid-sequence", "Motor/gear failure, debris on rail", "Sequence interrupted mid-pass", 6, 3, 2, "Resume-from-bolt state retention; manual procedure retained"),
    ("PLC or network fault during tightening", "Hardware/software fault", "Partially tightened joint", 7, 2, 2, "Safe-state on fault; state retention; ESD independent of PLC"),
    ("Galled or seized nut on breakout", "Thermal cycling, corrosion", "Breakout torque exceeded, stall", 5, 5, 2, "Torque limit with alarm; operator review; spare stud set"),
    ("Gasket misplaced by semi-automatic arm", "Cassette misload, face debris", "Leak at steam test", 7, 4, 3, "Camera confirmation; steam test gate before CLOSED"),
    ("Thermal damage to tool or sensors", "Residual hot spots on flange", "Tool failure, sensor drift", 6, 4, 4, "High-temperature rating; surface temperature interlock"),
    ("Leak test passes with a marginal joint", "Test pressure/time insufficient", "Leak in service", 8, 2, 5, "Defined hold time and decay criterion; torque-angle record review"),
]


def fmea():
    rows = []
    for mode, cause, effect, S, O, D, ctrl in FMEA:
        rows.append({"mode": mode, "cause": cause, "effect": effect, "S": S, "O": O, "D": D,
                     "RPN": S * O * D, "control": ctrl})
    rows.sort(key=lambda r: -r["RPN"])
    return rows


# ------------------------------------------------------------------ 9. exposure
def exposure(med):
    """Automation coverage A = sum(w_i a_i)/sum(w_i), weights = modelled task duration,
    and hazard-zone person-hours. Manual baseline figures are the source's estimates."""
    tasks = [  # name, duration (h, model median or assumption), automation level a
        ("Atmosphere check", med["t_atmos"], 1.0),
        ("Bolt loosening and removal", med["bolting_open"], 1.0),
        ("Head removal and replacement", 2 * med["t_head"], 0.5),   # operator initiates
        ("Gasket removal, cleaning, installation", med["t_gasket"], 0.5),
        ("Bolt installation and tightening", med["bolting_close"], 1.0),
        ("Leak test", med["t_leak"], 1.0),
    ]
    w = np.array([t[1] for t in tasks])
    a = np.array([t[2] for t in tasks])
    A = float((w * a).sum() / w.sum())
    return {"tasks": [{"task": t[0], "hours": round(t[1], 2), "a": t[2]} for t in tasks],
            "coverage": round(A, 3),
            "manual_person_hours": [4 * 4, 6 * 6],          # 4-6 workers x 4-6 h (source)
            "pabhs_person_hours_in_zone": [0.0, round(med["t_gasket"], 2)]}


def main():
    s = sample()
    res = {"seed": SEED, "n_mc": N_MC, "step_ranges_s": STEP, "k_spacing": K_SPACING,
           "flanges": {k: {"n": v["n"], "d_mm": v["d_mm"]} for k, v in FLANGES.items()}}

    # sequences and travel (per unit bolt-circle diameter)
    res["sequences"] = {}
    for name, f in FLANGES.items():
        n = f["n"]
        st, ci = legacy_star(n), circular(n)
        res["sequences"][name] = {
            "star": st[:16],
            "travel_star_perD": round(travel_m(st, n, 1.0)[0], 2),
            "travel_circ_perD": round(travel_m(ci, n, 1.0)[0], 2),
            "travel_star_2runners_perD": round(travel_m(st, n, 1.0, 2)[0], 2),
            "D_range_m": [round(bolt_circle(n, f["d_mm"][0], K_SPACING[0]), 2),
                          round(bolt_circle(n, f["d_mm"][1], K_SPACING[1]), 2)]}

    configs = {"1 head, parallel flanges": dict(runners=1, parallel=True),
               "1 head, serial flanges": dict(runners=1, parallel=False),
               "1 head, circular passes only": dict(runners=1, parallel=True, pattern="circular"),
               "2 heads, parallel flanges": dict(runners=2, parallel=True),
               "4 heads, parallel flanges": dict(runners=4, parallel=True),
               "4 heads, 2 star passes": dict(runners=4, parallel=True, star_passes=2)}
    res["cycle"] = {}
    for name, kw in configs.items():
        c = cycle(s, **kw)
        res["cycle"][name] = {k: pct(c[k]) for k in ("bolting_open", "bolting_close",
                                                     "bolting_total", "full_open",
                                                     "full_close", "full_total")}
        res["cycle"][name]["per_flange_bolting_h"] = {
            f: pct(c[f]["open"] + c[f]["close"]) for f in FLANGES}
        res["cycle"][name]["p_bolting_le_2.5h"] = round(float(np.mean(c["bolting_total"] <= 9000)), 3)
        res["cycle"][name]["p_bolting_le_1.5h"] = round(float(np.mean(c["bolting_total"] <= 5400)), 3)
        if name == "1 head, parallel flanges":
            base = c
        if name == "4 heads, parallel flanges":
            quad = c
    np.save("_mc_bolting_total.npy", np.vstack([cycle(s, **kw)["bolting_total"] for kw in configs.values()]))

    lo = {k: np.full(1, (v[0] if k not in ("v_carriage", "rpm_spin") else v[1]), dtype=float)
          for k, v in STEP.items()}
    lo["k_spacing"] = np.full(1, K_SPACING[0]); lo["d_frac"] = np.zeros(1)
    lo["check_passes"] = np.full(1, 1)
    res["best_case_bolting_h"] = {name: round(float(cycle(lo, **kw)["bolting_total"][0]) / 3600, 2)
                                  for name, kw in configs.items()}

    # sensitivity: Spearman rank correlation with total bolting time (base config)
    sens = {}
    for k in list(STEP) + ["k_spacing", "d_frac"]:
        if k in ("t_head", "t_gasket", "t_atmos", "t_leak"):
            continue
        rho = spearmanr(s[k], base["bolting_total"]).correlation
        sens[k] = round(float(rho), 3)
    res["sensitivity_bolting_total"] = dict(sorted(sens.items(), key=lambda kv: -abs(kv[1])))
    sens4 = {}
    for k in list(STEP) + ["k_spacing", "d_frac"]:
        if k in ("t_head", "t_gasket", "t_atmos", "t_leak"):
            continue
        sens4[k] = round(float(spearmanr(s[k], quad["bolting_total"]).correlation), 3)
    res["sensitivity_bolting_total_4heads"] = dict(sorted(sens4.items(), key=lambda kv: -abs(kv[1])))
    res["carousel_share_4heads"] = round(float(np.median(
        (2 * FLANGES["bottom head"]["n"] * s["t_transfer"]) /
        (quad["bottom head"]["open"] + quad["bottom head"]["close"]))), 3)

    # admissibility: what per-bolt-pass time does the 2.5 h bolting target allow?
    bp = {name: 0 for name in FLANGES}
    for name, f in FLANGES.items():
        n = f["n"]
        # bolt-passes: open (1 star + 1 run-off) + close (1 run-on + 3 star + check ~2)
        bp[name] = n * (LOOSEN_STAR_PASSES + 1 + 1 + TIGHTEN_STAR_PASSES + 2)
    worst = max(bp.values())
    res["admissibility"] = {
        "bolt_passes_per_flange": bp,
        "bolt_passes_total": sum(bp.values()),
        "budget_s_per_bolt_pass_parallel_2.5h": round(9000.0 / worst, 1),
        "budget_s_per_bolt_pass_serial_2.5h": round(9000.0 / sum(bp.values()), 1),
        "budget_s_per_bolt_pass_parallel_1.5h": round(5400.0 / worst, 1),
        "modelled_median_s_per_bolt_pass_bottom": round(
            float(np.median(base["bottom head"]["open"] + base["bottom head"]["close"])) / bp["bottom head"], 1)}
    med = {k: float(np.median(v)) / 3600.0 for k, v in (
        ("t_atmos", s["t_atmos"]), ("t_head", s["t_head"]), ("t_gasket", s["t_gasket"]),
        ("t_leak", s["t_leak"]), ("bolting_open", base["bolting_open"]),
        ("bolting_close", base["bolting_close"]))}
    res["preload"] = preload_study()
    res["manipulator"] = manipulator()
    res["fmea"] = fmea()
    res["exposure"] = exposure(med)
    res["sequences_travel_4heads_perD"] = {n_: round(travel_m(legacy_star(f["n"]), f["n"], 1.0, 4)[0], 2)
                                           for n_, f in FLANGES.items()}
    json.dump(res, open("pabhs_results.json", "w"), indent=1, default=float)

    c = res["cycle"]
    print("bolting total (h), median [p05-p95]:")
    for name in c:
        b = c[name]["bolting_total"]
        print("  %-32s %.2f [%.2f-%.2f]  P(<=2.5h)=%.2f  P(<=1.5h)=%.2f"
              % (name, b["median"], b["p05"], b["p95"], c[name]["p_bolting_le_2.5h"],
                 c[name]["p_bolting_le_1.5h"]))
    print("full open+close (h), base:", c["1 head, parallel flanges"]["full_total"])
    print("per flange (base):", c["1 head, parallel flanges"]["per_flange_bolting_h"])
    print("best case:", res["best_case_bolting_h"])
    print("sensitivity:", list(res["sensitivity_bolting_total"].items())[:6])
    print("admissibility:", res["admissibility"])
    print("sensitivity 4 heads:", list(res["sensitivity_bolting_total_4heads"].items())[:6])
    print("carousel share of bottom-flange time, 4 heads:", res["carousel_share_4heads"])
    print("torque kNm:", res["preload"]["torque_kNm"])
    print("torque-angle:", res["preload"]["torque_angle"])
    print("manipulator:", res["manipulator"])
    print("FMEA top:", [(r["mode"][:40], r["RPN"]) for r in res["fmea"][:4]])
    print("exposure:", res["exposure"])
    print("sequences:", {k: (v["travel_star_perD"], v["travel_circ_perD"], v["travel_star_2runners_perD"], v["D_range_m"]) for k, v in res["sequences"].items()})


if __name__ == "__main__":
    main()
