#!/usr/bin/env python3
"""Reality baseline smoke test - law/Physics baseline standard V3.0 (R1-R5).

Subject: a virtual world must be a real world.

Reality is a structural property: it describes how rules are set and enforced,
not what the rules say. This script verifies that the criterion set is
executable. It covers:

  [1] R1 genesis lock       locked on injection; locked on construction; later overwrite rejected
  [2] R2 global consistency an undeclared world is judged False (fail-closed)
  [3] R3 causal closure     an undeclared "no exogenous injection" channel is judged False
  [4] R4 published as executed  the commitment hash is recomputable by a third party; a mismatch is judged False
  [5] R5 reaction-table completeness  undeclared is judged False
  [6] Gate                  the reality dimension enters ProtocolValidator without subsuming physics
  [7] Referendum            fail-closed / threshold / passage
  [8] Fork                  the parent world is not modified; the child is itself bound by R1

Run: python tools/reality_smoke.py
"""
import sys
sys.path.insert(0, ".")

from constitution_rules import (
    ImmutableWorldRule,
    PhysicsBaseline,
    CONSENSUS_THRESHOLD,
)
from system.protocol import ProtocolValidator

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


def base_physics(**over):
    p = {
        "gravity": 3.7, "time_dilation": 2.0, "unit_scale": "lunar",
        "no_dimensional_inflation": True,
        "genesis_locked": True,
        "constants_globally_consistent": True,
        "no_exogenous_injection": True,
        "reaction_table_complete": True,
        "published_commitment": "sha256:abc",
        "ledger_commitment": "sha256:abc",
    }
    p.update(over)
    return p


print("=" * 68)
print("Reality baseline smoke test - law/Physics baseline standard V3.0 (R1-R5)")
print("=" * 68)

# -- [1] R1 genesis lock ------------------------------------------------
print("\n[1] R1 genesis lock")
w = ImmutableWorldRule(world_id="world-luna")
check("not locked before genesis", w._physics_locked is False)
check("genesis injection succeeds", w.set_physics_constants(
    {"gravity": 1.62, "time_dilation": 1.0, "unit_scale": "metric",
     "element_reactions": {}}) is True)
check("locked on injection", w._physics_locked is True)
check("later overwrite rejected", w.set_physics_constants(
    {"gravity": 9.80665, "time_dilation": 1.0, "unit_scale": "metric",
     "element_reactions": {}}) is False)
check("original constants preserved", w.physics_constants["gravity"] == 1.62,
      f"gravity={w.physics_constants['gravity']}")

w2 = ImmutableWorldRule(
    physics_constants={"gravity": 3.7, "time_dilation": 2.0,
                       "unit_scale": "lunar", "element_reactions": {}},
    world_id="world-mars")
check("genesis lock engaged by construction (old R1 bypass closed)", w2._physics_locked is True)
check("constants not overwritable after construction", w2.set_physics_constants(
    {"gravity": 9.8, "time_dilation": 1.0, "unit_scale": "metric",
     "element_reactions": {}}) is False)

# -- [2]-[5] criterion by criterion -------------------------------------
pb = PhysicsBaseline()

print("\n[2] R2 global consistency")
check("declared consistent -> pass", pb.reality_compliant(base_physics())["R2_global_consistency"])
check("undeclared -> rejected (fail-closed)",
      pb.reality_compliant(base_physics(constants_globally_consistent=False))
      ["R2_global_consistency"] is False)

print("\n[3] R3 causal closure")
check("no exogenous injection declared -> pass", pb.reality_compliant(base_physics())["R3_causal_closure"])
check("exogenous injection permitted -> rejected",
      pb.reality_compliant(base_physics(no_exogenous_injection=False))
      ["R3_causal_closure"] is False)

print("\n[4] R4 published as executed")
two_sided = pb.reality_compliant(base_physics())["R4_published_equals_executed"]
check("both sides equal -> pass", two_sided is True)
check("sides disagree -> rejected",
      pb.reality_compliant(base_physics(ledger_commitment="sha256:xyz"))
      ["R4_published_equals_executed"] is False)
check("only one side present -> rejected",
      pb.reality_compliant(base_physics(ledger_commitment=None))
      ["R4_published_equals_executed"] is False)
check("commitment hash recomputable by a third party",
      ImmutableWorldRule(physics_constants={
          "gravity": 3.7, "time_dilation": 2.0, "unit_scale": "lunar",
          "element_reactions": {}}).commitment()
      == ImmutableWorldRule(physics_constants={
          "unit_scale": "lunar", "gravity": 3.7, "time_dilation": 2.0,
          "element_reactions": {}}).commitment(),
      "key order does not affect the hash")

print("\n[5] R5 reaction-table completeness")
check("declared complete -> pass", pb.reality_compliant(base_physics())["R5_reaction_table_complete"])
check("undeclared -> rejected (fail-open prohibited)",
      pb.reality_compliant(base_physics(reaction_table_complete=False))
      ["R5_reaction_table_complete"] is False)

print("\n[5b] all criteria combined")
check("all satisfied -> is_real=True", pb.is_real(base_physics()) is True)
check("any unmet -> is_real=False",
      pb.is_real(base_physics(no_exogenous_injection=False)) is False)
check("bare configuration -> all five fail",
      len(pb.reality_failures({"gravity": 3.7})) == 5,
      str(pb.reality_failures({"gravity": 3.7})))

# -- [6] admission gate -------------------------------------------------
print("\n[6] Gate: the reality dimension enters ProtocolValidator")
pv = ProtocolValidator()
full = {
    "semantics": {"uses_nohn_semantics": True, "unknown_downgraded": True,
                  "vocab_mapped": True},
    "physics": base_physics(),
    "identity": {"soul_hash_sha256": True, "non_revocable": True,
                 "cross_world_portable": True, "asset_bound": True},
    "economy": {"real_peg_1to1": True, "proof_of_reserve": True,
                "redemption_right": True, "unilateral_fee": False,
                "asset_bound_to_soul": True, "oracle_sources": ["a", "b", "c"]},
}
ok, fails = pv.validate(full)
check("complete configuration -> pass", ok is True and fails == [], f"failures={fails}")

dims = pv.validate_dict(full)
check("all five dimensions present", set(dims) == {"communication", "physics", "reality",
                                "identity", "economy"}, str(sorted(dims)))

partial = dict(full)
partial["physics"] = {"gravity": 3.7, "time_dilation": 2.0,
                      "unit_scale": "lunar", "no_dimensional_inflation": True}
ok2, fails2 = pv.validate(partial)
check("constants only -> physics passes, reality rejects", fails2 == ["reality"], str(fails2))
check("a non-Earth gravity is no longer rejected by physics",
      pv.validate_dict(partial)["physics"] is True,
      "reality comes from invariance, not from matching Earth")
check("per-criterion localisation available",
      all(v is False for v in pv.validate_reality_detail(partial).values()))

# -- [7] referendum -----------------------------------------------------
print("\n[7] Global referendum")
check("no ballot record -> rejected (fail-closed)",
      w.propose_amendment({"gravity": 3.7}, "citizen-1") is False)
check("rejection reason recorded",
      w.rule_modification_log[-1]["reason"] == "no vote record (fail-closed)")
check("approval 0.60 < 2/3 -> rejected",
      w.propose_amendment({"gravity": 3.7}, "citizen-1",
                          {"eligible": 100, "approve": 60, "reject": 40}) is False)
check("threshold recorded",
      w.rule_modification_log[-1]["threshold"] == CONSENSUS_THRESHOLD)
check("referendum passes -> True",
      w.propose_amendment({"gravity": 3.7}, "citizen-1",
                          {"eligible": 100, "approve": 90, "reject": 10}) is True)
check("raw counts recorded (recomputable against another baseline)",
      w.rule_modification_log[-1]["ballot"]["approve"] == 90)

# -- [8] fork -----------------------------------------------------------
print("\n[8] Fork: the only amendment path")
rec = w.fork_registry[-1]
check("fork registered", rec["status"] == "forked", rec["fork_id"])
check("parent world unmodified", rec["parent_untouched"] is True)
check("parent constants remain 1.62", w.physics_constants["gravity"] == 1.62,
      f"gravity={w.physics_constants['gravity']}")
check("child world receives the new constants", rec["child_constants"]["gravity"] == 3.7)
check("migration is voluntary (no automatic relocation)", rec["requires_migration"] is True)
check("parent and child commitment hashes differ",
      rec["parent_commitment"] != rec["child_commitment"])
check("parent commitment hash matches current state",
      rec["parent_commitment"] == w.commitment())
check("second fork increments the identifier",
      w._fork_world({"gravity": 9.8})["fork_id"] == "world-luna-fork-002")
check("fork registry is append-only", len(w.fork_registry) == 2)

print("\n" + "=" * 68)
if _failed == 0:
    print(f"ALL PASS - {_passed} checks")
else:
    print(f"FAILED - {_failed} of {_passed + _failed} checks failed")
print("=" * 68)
sys.exit(1 if _failed else 0)
