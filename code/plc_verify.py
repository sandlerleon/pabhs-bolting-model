# -*- coding: utf-8 -*-
"""Exhaustive verification of the PABHS sequence/interlock logic.

The white paper states five interlocks in prose. Here the controller is written as an
explicit transition function and every reachable state is explored under every
combination of the nine boolean inputs, checking seven safety invariants on every
transition. Then each interlock is removed in turn ('mutants') to show that the check
has the power to catch its absence: an invariant that no mutant can violate would be
testing nothing.

This is explicit-state model checking in the sense of the PLC-verification literature,
done by breadth-first enumeration rather than with a dedicated model checker; it
verifies the logic as specified, not any PLC implementation of it.

    python plc_verify.py
"""
import itertools
import json
from collections import deque

STATES = ["IDLE", "ATMOS_CHECK", "UNBOLT", "HEAD_OPEN", "OPEN", "GASKET", "HEAD_CLOSE",
          "BOLT", "LEAK_TEST", "AWAIT_SIGNOFF", "CLOSED", "HOLD", "ESD_SAFE"]
INPUTS = ["gas_ok", "esd", "torque_ok", "angle_ok", "head_aligned", "leak_ok",
          "start", "confirm", "reset"]
MOTION = {"UNBOLT", "BOLT"}                 # torque tool may act
HEAD_MOTION = {"HEAD_OPEN", "HEAD_CLOSE"}   # manipulator may move the head

ALL_INTERLOCKS = {"gas_before_unbolt", "no_head_move_engaged", "sequence_lock",
                  "leak_before_closed", "signoff_before_closed", "esd", "gas_hold"}


def atmos_route(engaged, verified, leak, resume, N, recovery):
    """Where ATMOS_CHECK sends the sequence. Without recovery (the logic as described
    in the source white paper) only a fully bolted or fully open drum has a route."""
    if not recovery:
        return "UNBOLT" if engaged == N else "GASKET"
    if engaged == 0:
        return "HEAD_OPEN" if resume == "HEAD_OPEN" else "GASKET"
    if engaged < N:
        return "UNBOLT"                      # interrupted opening: continue unbolting
    if verified < N:
        return "BOLT"                        # interrupted closing: resume at next bolt
    if not leak:
        return "LEAK_TEST"
    if resume == "AWAIT_SIGNOFF":
        return "AWAIT_SIGNOFF"
    return "UNBOLT"                          # a closed drum: open it


def step(st, i, N, il, recovery=True):
    """One PLC scan. st = (mode, engaged, verified, leak_passed, resume_mode).
    il = set of interlocks that are implemented (the full set in the real design)."""
    mode, engaged, verified, leak, resume = st
    if "esd" in il and i["esd"]:
        return ("ESD_SAFE", engaged, verified, leak, mode if mode != "ESD_SAFE" else resume)
    if mode == "ESD_SAFE":
        if i["reset"] and not i["esd"]:
            return ("IDLE", engaged, verified, leak, resume if recovery else "IDLE")
        return st
    if "gas_hold" in il and mode in MOTION and not i["gas_ok"]:
        return ("HOLD", engaged, verified, leak, mode)
    if mode == "HOLD":
        if i["gas_ok"] and i["confirm"]:
            return (resume, engaged, verified, leak, resume)
        return st
    if mode == "IDLE":
        if i["start"]:
            return ("ATMOS_CHECK", engaged, verified, leak, resume)
        return st
    if mode == "HEAD_OPEN" and engaged > 0 and "no_head_move_engaged" in il:
        return st
    if mode == "ATMOS_CHECK":
        nxt = atmos_route(engaged, verified, leak, resume, N, recovery)
        if nxt in MOTION and not (i["gas_ok"] or "gas_before_unbolt" not in il):
            return st                                       # tool motion needs clearance
        return (nxt, engaged, verified, leak, resume)
    if mode == "UNBOLT":
        # one bolt removed per scan when the tool reports completion
        if engaged > 0 and i["torque_ok"]:
            engaged -= 1
        if engaged == 0 or "no_head_move_engaged" not in il:
            if i["confirm"]:
                return ("HEAD_OPEN", engaged, 0, False, resume)
        return ("UNBOLT", engaged, verified, leak, resume)
    if mode == "HEAD_OPEN":
        return ("OPEN", engaged, verified, leak, resume)
    if mode == "OPEN":
        if i["start"]:
            return ("IDLE", engaged, verified, leak, resume)
        return st
    if mode == "GASKET":
        if i["confirm"] and (engaged == 0 or "no_head_move_engaged" not in il):
            return ("HEAD_CLOSE", engaged, verified, leak, resume)
        return st
    if mode == "HEAD_CLOSE":
        if i["head_aligned"]:
            return ("BOLT", N, 0, False, resume)            # bolts installed, none verified
        return st
    if mode == "BOLT":
        ok = i["torque_ok"] and i["angle_ok"]
        if verified < N and (ok or "sequence_lock" not in il):
            verified += 1
        if verified == N:
            return ("LEAK_TEST", engaged, verified, leak, resume)
        return ("BOLT", engaged, verified, leak, resume)
    if mode == "LEAK_TEST":
        if i["leak_ok"]:
            return ("AWAIT_SIGNOFF", engaged, verified, True, resume)
        if "leak_before_closed" not in il:
            return ("AWAIT_SIGNOFF", engaged, verified, False, resume)
        return st
    if mode == "AWAIT_SIGNOFF":
        if i["confirm"] or "signoff_before_closed" not in il:
            return ("CLOSED", engaged, verified, leak, resume)
        return st
    if mode == "CLOSED":
        if i["start"]:
            return ("ATMOS_CHECK", engaged, verified, leak, resume)
        return st
    raise ValueError(mode)


def invariants(st, i, nx, N):
    """Return the list of invariant names violated by transition st --i--> nx."""
    bad = []
    mode, eng, ver, leak, _ = st
    nmode, neng, nver, nleak, _ = nx
    if nmode in MOTION and mode == "ATMOS_CHECK" and not i["gas_ok"]:
        bad.append("I1 unbolting starts only with gas clearance")
    if nmode in HEAD_MOTION and neng > 0:
        bad.append("I2 head moves only with no bolt engaged")
    if nmode == "BOLT" or mode == "BOLT":
        if nver > ver and not (i["torque_ok"] and i["angle_ok"]):
            bad.append("I3 sequence advances only on torque AND angle pass")
        if nver - ver > 1:
            bad.append("I3 sequence advances only on torque AND angle pass")
    if nmode == "CLOSED" and mode != "CLOSED":
        if not nleak:
            bad.append("I4 CLOSED only after leak test pass")
        if nver != N:
            bad.append("I4 CLOSED only after leak test pass")
        if not i["confirm"]:
            bad.append("I5 CLOSED only with operator sign-off")
    if i["esd"] and nmode != "ESD_SAFE":
        bad.append("I6 ESD forces the safe state from any state")
    if mode in MOTION and not i["gas_ok"] and not i["esd"] and nmode in MOTION:
        bad.append("I7 loss of gas clearance holds all tool motion")
    return bad


def explore(N, il, recovery=True):
    start = ("CLOSED", N, N, True, "IDLE")
    seen = {start: None}
    q = deque([start])
    violations = {}
    n_trans = 0
    succ = {}
    combos = [dict(zip(INPUTS, v)) for v in itertools.product([False, True], repeat=len(INPUTS))]
    while q:
        st = q.popleft()
        succ[st] = set()
        for i in combos:
            nx = step(st, i, N, il, recovery)
            succ[st].add(nx)
            n_trans += 1
            for b in invariants(st, i, nx, N):
                if b not in violations:
                    # reconstruct the path to this state for the counterexample length
                    depth, cur = 0, st
                    while seen[cur] is not None:
                        cur = seen[cur]
                        depth += 1
                    violations[b] = depth + 1
            if nx not in seen:
                seen[nx] = st
                q.append(nx)
    reach = {m: any(s[0] == m for s in seen) for m in STATES}
    # liveness: from which reachable states can a completed state (OPEN or CLOSED) still
    # be reached under SOME input sequence? States that cannot are deadlocks.
    can = {s for s in seen if s[0] in ("OPEN", "CLOSED")}
    changed = True
    while changed:
        changed = False
        for s in seen:
            if s not in can and succ[s] & can:
                can.add(s)
                changed = True
    dead = [s for s in seen if s not in can]
    return {"states": len(seen), "transitions": n_trans, "violations": violations,
            "modes_reachable": sum(reach.values()), "closed_reachable": reach["CLOSED"],
            "open_reachable": reach["OPEN"], "deadlocked_states": len(dead),
            "deadlock_examples": [list(d) for d in sorted(dead)[:5]]}


def main():
    out = {"inputs": INPUTS, "modes": STATES, "full_design": {}, "as_specified": {},
           "mutants": {}}
    for N in (4, 8, 12):
        a = explore(N, ALL_INTERLOCKS, recovery=False)
        out["as_specified"][str(N)] = a
        r = explore(N, ALL_INTERLOCKS)
        out["full_design"][str(N)] = r
        print("N=%-3d as specified: states=%-5d deadlocked=%-4d violations=%s"
              % (N, a["states"], a["deadlocked_states"], a["violations"] or "none"))
        print("      with recovery: states=%-5d deadlocked=%-4d transitions=%-8d violations=%s modes=%d/%d"
              % (r["states"], r["deadlocked_states"], r["transitions"],
                 r["violations"] or "none", r["modes_reachable"], len(STATES)))
    for drop in sorted(ALL_INTERLOCKS):
        r = explore(4, ALL_INTERLOCKS - {drop})
        out["mutants"][drop] = sorted(r["violations"].items())
        print("mutant without %-24s -> %s" % (drop, r["violations"] or "NOT DETECTED"))
    out["all_mutants_detected"] = all(out["mutants"].values())
    json.dump(out, open("plc_verify_results.json", "w"), indent=1)
    print("all mutants detected:", out["all_mutants_detected"])


if __name__ == "__main__":
    main()
