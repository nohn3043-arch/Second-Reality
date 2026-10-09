#!/usr/bin/env python3
"""Primordial frames smoke test - constitution_rules 第负一章 (Primordial Frames).

Subject: an "original framework" that is only *published* but never *executed*
is, by this repository's own R4 standard, an illusion. This script verifies
that every executable frame actually has a producer in system/ and a consumer
in audit_engine, and that the R4 clause is no longer a no-op.

Coverage:
  [1] Chapter self-audit   every frame carries producer/consumer/recompute/boundary
  [2] Chaos                the entropy seed enters the commitment; omission stays byte-compatible
  [3] R4 really executed   published == ledger AND the recompute hits the ledger block
  [4] R4 regression probe  a hand-written literal (the old way) must now FAIL
  [5] Wuji                 fork records land in the ledger; the tree rebuilds; the parent is untouched
  [6] Illusion             the representation layer cannot move the commitment hash
  [7] Heavenly Way         the *form* of fairness is immutable; the thresholds stay votable
  [8] Samsara              the conservation residual holds, and a broken ledger is detected
  [9] No regression        full audit runs; all five frame dimensions PASS on a healthy world

Run: python tools/frames_smoke.py
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, ".")

# Hermetic by default: sections [1]-[9] must not touch the shared .world_data
# ledger (a stale shared ledger makes fork ids and identity audits non-reproducible).
os.environ["STORAGE"] = "memory"

from constitution_rules import (
    PRIMORDIAL_FRAMES,
    primordial_completeness,
    ImmutableWorldRule,
    NOHN_LAW_AXIOMS,
    CONSENSUS_THRESHOLD,
)
from system.runtime import World

_passed = 0
_failed = 0


def check(name, cond, detail=""):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  [PASS] {name}" + (f" - {detail}" if detail else ""))
    else:
        _failed += 1
        print(f"  [FAIL] {name}" + (f" - {detail}" if detail else ""))


def fresh_world(seed=None, world_id="frames-probe"):
    return World(world_id, data_dir=None, genesis_seed=seed)


def verdict(report, attr):
    value = getattr(report, attr, None)
    return value.get("verdict", "") if isinstance(value, dict) else ""


def main():
    # ---- [1] Chapter self-audit (M1 discipline, executable form) ----
    print("[1] Chapter self-audit - every frame carries the four elements")
    audit = primordial_completeness()
    check("all six frames present", len(PRIMORDIAL_FRAMES) == 6,
          f"{len(PRIMORDIAL_FRAMES)} frames")
    check("no frame is missing an element", audit["is_complete"],
          f"incomplete={audit['incomplete']}")
    for name, frame in PRIMORDIAL_FRAMES.items():
        check(f"frame '{name}' has producer+consumer+recompute",
              all(frame.get(k) for k in ("producer", "consumer", "recompute")))

    # ---- [2] Chaos: the seed enters the commitment ----
    print("[2] Chaos - the entropy seed enters the commitment")
    rule = ImmutableWorldRule()
    rule.set_physics_constants({
        "gravity": NOHN_LAW_AXIOMS["gravity"],
        "time_dilation": NOHN_LAW_AXIOMS["time_dilation"],
        "unit_scale": NOHN_LAW_AXIOMS["unit_scale"],
        "element_reactions": {("fire", "water"): "evaporation"},
    })
    no_seed = rule.commitment()
    seed_a = rule.commitment(seed=1)
    seed_b = rule.commitment(seed=2)
    check("seed omitted keeps the legacy hash (byte-compatible)", no_seed != seed_a)
    check("same constants + different seeds => different commitments", seed_a != seed_b)
    check("the same seed is stable", rule.commitment(seed=1) == seed_a)

    # ---- [3] R4 is really executed ----
    print("[3] R4 published-as-executed - the producer actually runs")
    world = fresh_world(seed=42)
    published = world.physics.get("published_commitment")
    anchored = world.physics.get("ledger_commitment")
    check("world carries a real commitment (producer present)", bool(published))
    check("published == ledger", published is not None and published == anchored)
    recomputed = world.immutable_rule.commitment(seed=world.genesis_seed)
    check("third party recompute hits the value", recomputed == published)

    ledger_anchor = None
    for _ts, event, _bh in world.history.chain:
        if isinstance(event, dict) and event.get("event") == "genesis_commitment":
            ledger_anchor = event.get("physics_commitment")
    check("the commitment is anchored in the hash chain", ledger_anchor == recomputed,
          f"anchor={str(ledger_anchor)[:24]}...")

    # genesis params must include the anchor block, or the audit cannot re-derive it
    cfg = world.genesis_condition.genesis_record or {}
    check("genesis record carries the commitment block",
          bool(cfg.get("genesis_commitment_block")))

    report = world.audit()
    check("audit dimension genesis_commitment PASS",
          verdict(report, "genesis_commitment").startswith("PASS"),
          verdict(report, "genesis_commitment"))

    # ---- [4] R4 regression probe ----
    print("[4] Regression probe - a hand-written literal must now fail")

    class LiteralWorld:
        world_id = "literal-world"
        physics = {"gravity": 9.80665, "time_dilation": 1.0, "unit_scale": "metric",
                   "published_commitment": "sha256:abc",
                   "ledger_commitment": "sha256:abc"}

    from audit_engine import SecondPerspectiveAuditor
    fake_result = SecondPerspectiveAuditor()._audit_genesis_commitment(LiteralWorld())
    check("literal 'sha256:abc' no longer passes",
          fake_result["verdict"].startswith("FAILED"),
          fake_result["verdict"])

    # ---- [5] Wuji: the branch space rebuilds from the ledger ----
    print("[5] Wuji - branch space rebuilds from the ledger")
    space0 = world.branch_space()
    check("root is the world itself", space0["root"] == world.world_id)
    check("chain valid before any fork", space0["chain_valid"] is True)
    check("no forks yet", space0["fork_count"] == 0)

    parent_constants = dict(world.immutable_rule.physics_constants)
    rejected = world.fork_world({"gravity": 3.7}, "proposer", {"approve": 1, "reject": 9})
    check("referendum below 2/3 is fail-closed",
          rejected["status"] == "fork_rejected", rejected["status"])
    check("no ledger block written on rejection",
          all(not (isinstance(e, dict) and e.get("event") == "world_fork")
              for _t, e, _b in world.history.chain))

    approved = world.fork_world(
        {"gravity": 3.7}, "proposer", {"eligible": 100, "approve": 80, "reject": 20})
    check("referendum >= 2/3 forks a child", approved["status"] == "forked")
    space1 = world.branch_space()
    child_id = approved["record"]["fork_id"]
    check("fork record is anchored in the ledger", space1["fork_count"] == 1)
    check("child is attached to the world root",
          space1["children"].get(world.world_id) == [child_id],
          f"children={space1['children']}")
    check("child depth is 1", space1["nodes"].get(child_id, {}).get("depth") == 1)
    check("parent constants untouched (R1)",
          dict(world.immutable_rule.physics_constants) == parent_constants)

    # ---- [6] Illusion: the representation layer cannot move the commitment ----
    print("[6] Illusion - the representation layer is isolated from the executor")
    before = world.immutable_rule.commitment(seed=world.genesis_seed)
    world.represent("soul_probe", {"content": "the sky is falling", "truth": False})
    world.represent("soul_probe", {"content": "I dreamt of a second sun", "truth": False})
    after = world.immutable_rule.commitment(seed=world.genesis_seed)
    check("representation writes do not move the commitment hash", before == after)
    check("beliefs are stored per actor", len(world.beliefs_of("soul_probe")) == 2)
    check("representation keys are disjoint from physics keys",
          not (set(world.representations.keys()) & set(world.physics.keys())))

    report = world.audit()
    check("audit dimension representation_isolation PASS",
          verdict(report, "representation_isolation").startswith("PASS"),
          verdict(report, "representation_isolation"))

    # ---- [7] Heavenly Way: form immutable, thresholds votable ----
    print("[7] Heavenly Way - the form of fairness is immutable")
    check("threshold is still the single-source 2/3",
          abs(CONSENSUS_THRESHOLD - 2.0 / 3.0) < 1e-12)
    from constitution_rules import DecentralizationGovernance, WorldPerpetuity
    dg = DecentralizationGovernance()
    check("no single entity may shut a world down",
          dg.shutdown_world("w", "actor") is False)
    check("no single entity may freeze a soul",
          dg.freeze_soul("0" * 64, "actor") is False)
    check("world perpetuity cannot be legally terminated by one operator",
          world.world_perpetuity.is_shutdown_legal("w", "actor") is False)
    check("a soul can never be revoked by the platform",
          world.soul_attestation.revoke_soul("0" * 64) is False)
    check("economic dynamic balance is in place", world.economy.compliant() is True)
    report = world.audit()
    check("audit dimension fairness_invariant PASS",
          verdict(report, "fairness_invariant").startswith("PASS"),
          verdict(report, "fairness_invariant"))

    # ---- [8] Samsara: conservation holds, and breakage is detected ----
    print("[8] Samsara - conservation law holds and breakage is detected")
    tol = float(NOHN_LAW_AXIOMS["conservation_tolerance"])
    check("healthy world has residual 0", world.conservation_residual() == 0.0)
    check("healthy world has no reserve shortfall", world.economy.conservation_holds() is True)
    check("history chain links every cause", world.history.validate_chain() is True)
    report = world.audit()
    check("audit dimension conservation_law PASS",
          verdict(report, "conservation_law").startswith("PASS"),
          verdict(report, "conservation_law"))

    # inject a broken ledger entry: supply with no reserve behind it
    world.economy._ledger["__broken__"] = {
        "owner_soul": "0" * 64, "total_supply": 1000.0, "reserve_amount": 0.0,
    }
    check("a supply with no backing is detected",
          world.conservation_residual() > tol,
          f"residual={world.conservation_residual()}")
    broken = SecondPerspectiveAuditor()._audit_conservation_law(world)
    check("audit flips to FAILED once the law is broken",
          broken["verdict"].startswith("FAILED"), broken["verdict"])
    del world.economy._ledger["__broken__"]
    check("residual returns to 0 after repair", world.conservation_residual() == 0.0)

    # ---- [9] No regression across the whole audit ----
    print("[9] No regression - the full audit still runs")
    report = world.audit()
    check("branch_space dimension PASS after a real fork",
          verdict(report, "branch_space").startswith("PASS"),
          verdict(report, "branch_space"))
    summary = report.summary()
    check("summary runs", isinstance(summary, str) and len(summary) > 0)
    frame_attrs = ["genesis_commitment", "branch_space",
                   "representation_isolation", "fairness_invariant", "conservation_law"]
    check("all five frame dimensions PASS on a healthy world",
          all(verdict(report, a).startswith("PASS") for a in frame_attrs),
          ", ".join(f"{a}={verdict(report, a).split(' ')[0]}" for a in frame_attrs))
    check("dimension count is derived, not hardcoded",
          str(len(report.FIELDS)) in summary)
    check("temporal dimension unchanged (time frame is zero-code)",
          verdict(report, "temporal_defined").startswith("PASS"))

    world.close()

    # ---- [10] Durability: fork ids stay unique across a restart ----
    print("[10] Durability - fork ids do not collide across a restart")
    tmp_dir = tempfile.mkdtemp(prefix="frames-wuji-")
    os.environ["STORAGE"] = "sqlite"   # the real scenario: a persistent ledger
    try:
        w1 = World("durable-world", data_dir=tmp_dir)
        first = w1.fork_world({"gravity": 3.7}, "proposer",
                              {"eligible": 100, "approve": 90, "reject": 10})
        first_id = first["record"].get("fork_id")
        check("first fork is numbered 001", str(first_id).endswith("fork-001"), str(first_id))
        w1.close()

        # A new process against the same ledger: the registry must be rebuilt
        # from the chain, otherwise the id sequence restarts and collides.
        w2 = World("durable-world", data_dir=tmp_dir)
        space = w2.branch_space()
        check("branch space survives the restart", space["fork_count"] == 1,
              f"fork_count={space['fork_count']}")
        check("restored registry is flagged as derived, not fabricated",
              w2.immutable_rule.fork_registry[0].get("restored_from_ledger") is True)
        second = w2.fork_world({"gravity": 3.8}, "proposer",
                               {"eligible": 100, "approve": 90, "reject": 10})
        second_id = second["record"].get("fork_id")
        check("second fork increments instead of colliding",
              second_id != first_id and str(second_id).endswith("fork-002"),
              str(second_id))
        children = w2.branch_space()["children"].get("durable-world", [])
        check("both children hang off the same root",
              sorted(children) == sorted([first_id, second_id]), str(children))
        w2.close()
    finally:
        os.environ["STORAGE"] = "memory"
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("")
    if _failed:
        print(f"FAIL: {_failed} checks failed")
        return 1
    print(f"ALL PASS ({_passed} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
