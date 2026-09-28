#!/usr/bin/env python3
"""Reality baseline smoke test — law/Physics baseline standard V3.0 (R1–R5).

主题：虚拟世界必须是一个真实的世界。

真实性是结构性属性——描述规则如何被设定与被执行，不描述规则的具体内容。
本脚本验证该判据集的可执行性，覆盖：

  [1] R1 创世锁定    注入即锁；构造注入亦锁；事后覆写被拒
  [2] R2 全域一致    未声明的世界判 False（fail-closed）
  [3] R3 因果闭合    未声明「无外部注入通道」判 False
  [4] R4 公示即执行  承诺哈希可被第三方重算；不一致即判 False
  [5] R5 反应表完备  未声明判 False
  [6] 门禁           reality 维度进入 ProtocolValidator，且不吞并 physics
  [7] 公投           fail-closed / 阈值 / 通过
  [8] 分叉           父世界不被改写；子世界同样受 R1 约束

运行：python tools/reality_smoke.py
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
        print(f"  [PASS] {name}" + (f" — {detail}" if detail else ""))
    else:
        _failed += 1
        print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))


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
print("真实性基准冒烟测试 · law/Physics baseline standard V3.0 (R1–R5)")
print("=" * 68)

# ── [1] R1 创世锁定 ─────────────────────────────────────────────
print("\n[1] R1 创世锁定")
w = ImmutableWorldRule(world_id="world-luna")
check("创世前未锁定", w._physics_locked is False)
check("创世注入成功", w.set_physics_constants(
    {"gravity": 1.62, "time_dilation": 1.0, "unit_scale": "metric",
     "element_reactions": {}}) is True)
check("注入即锁定", w._physics_locked is True)
check("事后覆写被拒", w.set_physics_constants(
    {"gravity": 9.80665, "time_dilation": 1.0, "unit_scale": "metric",
     "element_reactions": {}}) is False)
check("原常数保持", w.physics_constants["gravity"] == 1.62,
      f"gravity={w.physics_constants['gravity']}")

w2 = ImmutableWorldRule(
    physics_constants={"gravity": 3.7, "time_dilation": 2.0,
                       "unit_scale": "lunar", "element_reactions": {}},
    world_id="world-mars")
check("构造注入即锁（修补旧 R1 通道）", w2._physics_locked is True)
check("构造注入后亦不可覆写", w2.set_physics_constants(
    {"gravity": 9.8, "time_dilation": 1.0, "unit_scale": "metric",
     "element_reactions": {}}) is False)

# ── [2]~[5] 逐条判据 ────────────────────────────────────────────
pb = PhysicsBaseline()

print("\n[2] R2 全域一致")
check("声明一致 → 通过", pb.reality_compliant(base_physics())["R2_global_consistency"])
check("未声明 → 拒绝（fail-closed）",
      pb.reality_compliant(base_physics(constants_globally_consistent=False))
      ["R2_global_consistency"] is False)

print("\n[3] R3 因果闭合")
check("声明无外部注入 → 通过", pb.reality_compliant(base_physics())["R3_causal_closure"])
check("允许外部注入 → 拒绝",
      pb.reality_compliant(base_physics(no_exogenous_injection=False))
      ["R3_causal_closure"] is False)

print("\n[4] R4 公示即执行")
two_sided = pb.reality_compliant(base_physics())["R4_published_equals_executed"]
check("两侧一致 → 通过", two_sided is True)
check("两侧不一致 → 拒绝",
      pb.reality_compliant(base_physics(ledger_commitment="sha256:xyz"))
      ["R4_published_equals_executed"] is False)
check("仅一侧存在 → 拒绝",
      pb.reality_compliant(base_physics(ledger_commitment=None))
      ["R4_published_equals_executed"] is False)
check("承诺哈希可第三方重算",
      ImmutableWorldRule(physics_constants={
          "gravity": 3.7, "time_dilation": 2.0, "unit_scale": "lunar",
          "element_reactions": {}}).commitment()
      == ImmutableWorldRule(physics_constants={
          "unit_scale": "lunar", "gravity": 3.7, "time_dilation": 2.0,
          "element_reactions": {}}).commitment(),
      "键序不影响哈希")

print("\n[5] R5 反应表完备")
check("声明完备 → 通过", pb.reality_compliant(base_physics())["R5_reaction_table_complete"])
check("未声明 → 拒绝（fail-open 禁止）",
      pb.reality_compliant(base_physics(reaction_table_complete=False))
      ["R5_reaction_table_complete"] is False)

print("\n[5b] 全判据组合")
check("全部满足 → is_real=True", pb.is_real(base_physics()) is True)
check("任一不满足 → is_real=False",
      pb.is_real(base_physics(no_exogenous_injection=False)) is False)
check("裸配置 → 五条全失败",
      len(pb.reality_failures({"gravity": 3.7})) == 5,
      str(pb.reality_failures({"gravity": 3.7})))

# ── [6] 门禁 ────────────────────────────────────────────────────
print("\n[6] 门禁：reality 维度进入 ProtocolValidator")
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
check("完整配置 → 通过", ok is True and fails == [], f"failures={fails}")

dims = pv.validate_dict(full)
check("五维度齐备", set(dims) == {"communication", "physics", "reality",
                                "identity", "economy"}, str(sorted(dims)))

partial = dict(full)
partial["physics"] = {"gravity": 3.7, "time_dilation": 2.0,
                      "unit_scale": "lunar", "no_dimensional_inflation": True}
ok2, fails2 = pv.validate(partial)
check("仅声明常数 → physics 过、reality 拒", fails2 == ["reality"], str(fails2))
check("非地球重力不再被 physics 判死",
      pv.validate_dict(partial)["physics"] is True, "真实来自不变性，不来自与地球同值")
check("R1–R5 逐条定位可用",
      all(v is False for v in pv.validate_reality_detail(partial).values()))

# ── [7] 公投 ────────────────────────────────────────────────────
print("\n[7] 全球公投")
check("无投票记录 → 驳回（fail-closed）",
      w.propose_amendment({"gravity": 3.7}, "citizen-1") is False)
check("驳回原因已留档",
      w.rule_modification_log[-1]["reason"] == "no vote record (fail-closed)")
check("赞成率 0.60 < 2/3 → 驳回",
      w.propose_amendment({"gravity": 3.7}, "citizen-1",
                          {"eligible": 100, "approve": 60, "reject": 40}) is False)
check("阈值记录在案",
      w.rule_modification_log[-1]["threshold"] == CONSENSUS_THRESHOLD)
check("公投通过 → True",
      w.propose_amendment({"gravity": 3.7}, "citizen-1",
                          {"eligible": 100, "approve": 90, "reject": 10}) is True)
check("原始计数留档（可换基准重算）",
      w.rule_modification_log[-1]["ballot"]["approve"] == 90)

# ── [8] 分叉 ────────────────────────────────────────────────────
print("\n[8] 分叉：变更唯一路径")
rec = w.fork_registry[-1]
check("分叉已登记", rec["status"] == "forked", rec["fork_id"])
check("父世界未被改写", rec["parent_untouched"] is True)
check("父世界常数保持 1.62", w.physics_constants["gravity"] == 1.62,
      f"gravity={w.physics_constants['gravity']}")
check("子世界收到新常数", rec["child_constants"]["gravity"] == 3.7)
check("迁移为自愿（不自动搬迁）", rec["requires_migration"] is True)
check("父/子承诺哈希不同",
      rec["parent_commitment"] != rec["child_commitment"])
check("父世界承诺哈希与当前一致",
      rec["parent_commitment"] == w.commitment())
check("二次分叉编号递增",
      w._fork_world({"gravity": 9.8})["fork_id"] == "world-luna-fork-002")
check("分叉簿只增不删", len(w.fork_registry) == 2)

print("\n" + "=" * 68)
if _failed == 0:
    print(f"ALL PASS — {_passed} checks")
else:
    print(f"FAILED — {_failed} of {_passed + _failed} checks failed")
print("=" * 68)
sys.exit(1 if _failed else 0)
