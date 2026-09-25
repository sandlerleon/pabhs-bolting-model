# Automated bolting and head handling for multi-flange pressure-vessel closures

Leon Sandler, Independent Researcher — sandler.leon@gmail.com
ORCID [0009-0007-4584-808X](https://orcid.org/0009-0007-4584-808X)

Models, verification and figures for *"Automated bolting and head handling for
multi-flange pressure-vessel closures: a simulation-based design evaluation with a
delayed-coking case study,"* submitted to **The International Journal of Advanced
Manufacturing Technology**.

> **Every performance figure here is a model prediction from stated assumptions.**
> No system has been built or tested. The step-time ranges, bolt-circle diameters and
> head masses are assumptions or swept parameters, labelled as such in the code.

## The question

An automated architecture for opening and closing a 92-bolt, three-flange coke drum —
orbital pneumatic torque runners, a bolt carousel, a counterbalanced head manipulator and
an interlocking sequence controller — was first proposed with targets of 1.5–2.5 h
bolting, ±2 % torque accuracy and no personnel in the hazard zone. This repository tests
each target.

## What the models say

| Question | Result |
|---|---|
| Bolting time, 1 torque head per flange | median **7.96 h**; best case 2.96 h — cannot meet 2.5 h |
| Bolting time, 4 synchronised heads per flange | median **2.31 h**; ≤ 2.5 h in 70 % of samples |
| Rate-limiting element with 4 heads | the **carousel** (26 % of bottom-flange time) |
| Time budget the 2.5 h target implies | 23 s per bolt-pass vs 75 s modelled |
| ±2 % torque accuracy | almost no effect on preload; nut-factor scatter dominates |
| Torque–angle re-torque | bolts outside ±10 % of target: 32 % → 5 % (CV_K 10 %) |
| Interlock logic as first specified | safe, but **1,232 of 2,105** states deadlock after an ESD mid-sequence |
| With a resume rule | 0 deadlocks, 0 safety violations; every interlock mutant detected |
| Pneumatic head lift | needs a counterbalance carrying ≥ 70 % of a 10 t head |

## Contents

```
code/
  pabhs_model.py        geometry, star-sequence rail travel, Monte Carlo cycle time,
                        sensitivity, admissibility, preload, manipulator, FMEA, exposure
  plc_verify.py         exhaustive state-space check of the interlock logic, liveness
                        (deadlock) check, and mutation tests
  make_figures.py       Figures 1–8 (300 dpi PNG + TIFF)
  harvest_refs.py       Crossref metadata + abstracts for every DOI reference
  build_manuscript.py   manuscript; every number read from the JSON outputs
  build_cover_letter.py cover letter
  audit_manuscript.py   checks the document against the model and against itself
figures/                Figures 1–8
manuscript/             manuscript and cover letter
```

## Reproducing

```bash
pip install -r requirements.txt
cd code
python pabhs_model.py      # -> pabhs_results.json (seed 20260925, 20,000 samples)
python plc_verify.py       # -> plc_verify_results.json
python make_figures.py     # -> figures/
python build_manuscript.py
python audit_manuscript.py
```

## License

Code MIT (`LICENSE`); manuscript text and figures CC BY 4.0.
