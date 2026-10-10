# ============================================================
# Nohn 虚拟世界兼容框架 - 世界海关 v2.0
# 功能：旧世界（主题公园）接入 Nohn 宪法领土的唯一“海关”
# ============================================================
#
# v2.0 变更（对比 v1.0）：
#   1. 物理校验改为「结构完备 + 硬约束」语义：复用 constitution_rules.
#      PhysicsBaseline.aligned() —— 值由世界自定，不强制等于地球常数；
#      与 law/Physics baseline standard V3.0 的「真实来自不变性」对齐。
#      （v1.0 逐项比较 NOHN_LAW_AXIOMS 属于把模板误当校验基准，已修正。）
#      2. 新增 R1–R5 真实性判据（reality_failures / admit.details.reality）
#      与 second-perspective 五类校验的逐一报告：
#      physics / reality / identity / economy / communication。
#   3. 词汇映射可配置：StandardVocabulary 支持按厂商注册，未识别指令
#      降维为 NOHN_GENERIC_LOGIC 并留痕（v1.0 是写死的三行字典）。
#   4. 灵魂确权扩展为「64 位 hex 结构校验 + 可选公钥指纹核验」。
#   5. 新增 admit() 一站式海关：五维校验 + fail-closed 准入签章。
#
# 兼容性：v1.0 的四个公开方法签名保持不变（translate_intent /
#   check_physics_constants / verify_soul_hash / check_economic_standard），
#   仅行为更严格（physics 不再强制地球值；知识语义不全、未抑制熵等
#   场景的 fail-closed 语义与 constitution_rules 保持一致）。
# ============================================================

import re
import time
from typing import Any, Dict, List, Optional, Tuple

from constitution import NOHN_LAW_AXIOMS, _safe_get
from constitution_rules import (
    PhysicsBaseline,
    IdentityProtocol,
    EconomicBaseline,
    UniversalVocabulary,
)

# 64 位 hex（SHA-256 指纹）的正则：soul_hash 结构校验的单一权威模式
_SOUL_HASH_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class StandardVocabulary:
    """
    可配置的世界通用语义映射表（law/Communication protocol standard）。

    v1.0 中写死的三行厂商映射，升级为可注册、可扩展、可留痕的映射表：
      - register(prefix, nohn_semantic)  按厂商/前缀注册映射
      - translate(raw, default=None)     查表；未识别 → default（默认降维）
      - unknown_events                    记录所有被降维的原始指令（留痕）
    """

    def __init__(self, initial: Optional[Dict[str, str]] = None) -> None:
        self._map: Dict[str, str] = dict(initial or {})
        self.unknown_events: List[str] = []

    def register(self, private: str, nohn_semantic: str) -> None:
        """注册一条私有指令 → Nohn 标准语义的映射。"""
        self._map[private] = nohn_semantic

    def register_vendor(self, vendor: str, mapping: Dict[str, str]) -> None:
        """按厂商批量注册：vendor 前缀下的全部私有指令。"""
        for k, v in mapping.items():
            self._map[f"{vendor}:{k}"] = v

    def translate(self, raw: Any, default: str = "NOHN_GENERIC_LOGIC") -> str:
        """查表翻译；未识别指令降维并留痕（不静默）。"""
        key = str(raw)
        if key in self._map:
            return self._map[key]
        self.unknown_events.append(key)
        return default

    @property
    def mapping(self) -> Dict[str, str]:
        return dict(self._map)


class NohnCompatibilityBridge:
    """
    海关模块：负责将旧世界的私有逻辑映射至 Nohn 骨架。

    v2.0 在 v1.0 的四个方法之外新增：
      - physics_details / identity_details / economy_details /
        communication_details / reality_details —— 逐条判据报告
      - admit(world_config) —— 五维校验 + fail-closed 准入签章

    校验口径与 system/protocol.py 的 ProtocolValidator 及
    audit_engine.py 的 SecondPerspectiveAuditor 同源（复用同一组宪法基类），
    保证「海关判定 = 审计判定」，不会出现海关放行、审计拦截的裂缝。
    """

    def __init__(self, vocabulary: Optional[StandardVocabulary] = None) -> None:
        # 向后兼容：默认实例预置 v1.0 的示例映射（VENDOR_A/B/C），
        # 未识别指令仍降维为 NOHN_GENERIC_LOGIC 并留痕；新厂商经
        # register_vendor() / StandardVocabulary.register() 追加。
        if vocabulary is None:
            vocabulary = StandardVocabulary(
                initial={
                    "VENDOR_A_PRIVATE_MOVE": "NOHN_STANDARD_MOVE",
                    "VENDOR_B_PRIVATE_ATTACK": "NOHN_STANDARD_ACTION",
                    "VENDOR_C_PRIVATE_EMOTE": "NOHN_STANDARD_COMMUNICATE",
                }
            )
        self.vocabulary = vocabulary
        self.physics_baseline = PhysicsBaseline()
        self.identity_protocol = IdentityProtocol()
        self.economic_baseline = EconomicBaseline()
        self.universal_vocabulary = UniversalVocabulary()

    # ------------------------------------------------------------
    # ① 语义清洗（向后兼容 v1.0：translate_intent 签名不变）
    # ------------------------------------------------------------
    def translate_intent(self, raw_intent: Any) -> str:
        """
        【世界唯一通用语 - 语义清洗】
        功能：将厂商私有的、带有诱导性或格式不一的指令，洗白为 Nohn 标准语义。
        逻辑：剥夺厂商对指令的暗箱解释权，确保跨世界通信的纯粹性。
        未识别指令降维为 NOHN_GENERIC_LOGIC，并写入 vocabulary.unknown_events。
        """
        return self.vocabulary.translate(raw_intent)

    # ------------------------------------------------------------
    # ② 物理底线校验（v2.0：结构完备 + 硬约束，而非强制地球值）
    # ------------------------------------------------------------
    def check_physics_constants(self, incoming_physics: Dict) -> bool:
        """
        【全球物理底线校验 - 维度对齐】
        功能：校验重力、时间流速、空间尺度是否自洽声明。
        逻辑：复用 PhysicsBaseline.aligned() ——
          - 必须显式声明 gravity、time_dilation、unit_scale（值由世界自定）
          - no_dimensional_inflation 为硬约束，必须为 True（禁止数值膨胀式引流）
        注意（v2.0 修正）：不再逐项比较 NOHN_LAW_AXIOMS 模板值——
          那会把「创世自定模板」误当「地球值校验基准」，与真实性基准相悖。
        """
        return self.physics_baseline.aligned(incoming_physics)

    def physics_details(self, incoming_physics: Dict) -> Dict[str, bool]:
        """物理维度逐条判据（对齐 law/Physics baseline standard）。"""
        return {
            "gravity_declared": "gravity" in incoming_physics,
            "time_dilation_declared": "time_dilation" in incoming_physics,
            "unit_scale_declared": "unit_scale" in incoming_physics,
            "no_dimensional_inflation": bool(
                incoming_physics.get("no_dimensional_inflation", False)),
        }

    def reality_failures(self, incoming_physics: Dict) -> List[str]:
        """R1–R5 未通过的判据名；空列表 = 通过全部真实性判据。"""
        return self.physics_baseline.reality_failures(incoming_physics)

    # ------------------------------------------------------------
    # ③ 灵魂确权（向后兼容 v1.0：verify_soul_hash 签名 + 新增公钥指纹）
    # ------------------------------------------------------------
    def verify_soul_hash(
        self, soul_hash: str, public_key: Optional[str] = None
    ) -> bool:
        """
        【全球唯一身份标识规范 - 灵魂确权】
        功能：绕过厂商账号体系，验证“数字生命”的真实唯一性。
        逻辑：
          - 结构校验：soul_hash 必须是 64 位 hex（SHA-256 指纹规范）；
          - 可选公钥指纹核验：传入 public_key 时，校验公钥 16 进制指纹
            与 soul_hash 的前缀一致（law/Identity attestation standard 允许
            自定义指纹长度；此处默认按完整 64 位匹配）。
        未通过 → 视为无记忆的“幽灵”数据，拒绝入境。
        """
        if not soul_hash or not _SOUL_HASH_HEX_RE.match(soul_hash):
            return False
        if public_key is not None:
            pub_hex = public_key if isinstance(public_key, str) else public_key.hex()
            if not _SOUL_HASH_HEX_RE.match(pub_hex):
                return False
            # 完整指纹对齐：公钥指纹即灵魂哈希（SHA-256 输入为公钥而非私钥）
            return pub_hex.lower() == soul_hash.lower()
        return True

    # ------------------------------------------------------------
    # ④ 经济标准校验（与 SecondPerspectiveAuditor._audit_economic_law 同源）
    # ------------------------------------------------------------
    def check_economic_standard(self, economy: Dict) -> bool:
        """
        【全球经济统一标准 V2.1 - 海关校验】
        功能：新世界接入前，核验其经济系统是否真正 1:1 锚定现实。
        逻辑：与 audit_engine.SecondPerspectiveAuditor._audit_economic_law
          及 constitution_rules.EconomicBaseline.compliant() 同源——
          锚定 1:1、PoR、赎回权、无单边费、资产绑灵魂、预言机 ≥ 3。
        """
        return self.economic_baseline.compliant(economy)

    def economy_details(self, economy: Dict) -> Dict[str, Any]:
        """经济维度逐条报告（含预言机来源数）。"""
        oracle_sources = _safe_get(economy, "oracle_sources", [])
        return {
            "real_peg_1to1": _safe_get(economy, "real_peg_1to1", None) is True,
            "proof_of_reserve": _safe_get(economy, "proof_of_reserve", None) is True,
            "redemption_right": _safe_get(economy, "redemption_right", None) is True,
            "unilateral_fee_forbidden": _safe_get(economy, "unilateral_fee", None) is False,
            "asset_bound_to_soul": _safe_get(economy, "asset_bound_to_soul", None) is True,
            "oracle_sources": len(oracle_sources),
            "oracle_min_sources": int(NOHN_LAW_AXIOMS["oracle_min_sources"]),
        }

    # ------------------------------------------------------------
    # ⑤ 五维校验报告（v2.0 新增）
    # ------------------------------------------------------------
    def check_identity(self, identity: Dict) -> bool:
        """身份维度：灵魂唯一、不可撤销、跨世界可迁移、资产绑定。"""
        return self.identity_protocol.compatible(identity)

    def check_communication(self, semantics: Dict) -> bool:
        """通信维度：使用 Nohn 标准语义、未知降维、词汇已映射。"""
        return self.universal_vocabulary.translatable(semantics)

    def verify(self, world_config: Dict) -> Tuple[bool, Dict[str, bool]]:
        """
        五维逐项校验（与 ProtocolValidator.validate_dict 同口径）：
        communication / physics / reality / identity / economy。
        返回 (是否全通过, 逐维布尔)。
        """
        physics = world_config.get("physics", {})
        results: Dict[str, bool] = {
            "communication": self.check_communication(
                world_config.get("semantics", {})),
            "physics": self.physics_baseline.aligned(physics),
            "reality": self.physics_baseline.is_real(physics),
            "identity": self.identity_protocol.compatible(
                world_config.get("identity", {})),
            "economy": self.economic_baseline.compliant(
                world_config.get("economy", {})),
        }
        return (all(results.values()), results)

    # ------------------------------------------------------------
    # ⑥ 一站式海关：准入签章（v2.0 新增，fail-closed）
    # ------------------------------------------------------------
    def admit(self, world_config: Dict) -> Dict[str, Any]:
        """
        完整入境审查：五维校验 + R1–R5 细节 + 准入签章。

        fail-closed 原则：任一维度未通过 → verdict = REJECTED，
        附 fail 清单（failures）与逐条细节（details），供厂商针对性整改。
        全通过 → verdict = ADMITTED，签发带时间戳的海关签章。
        """
        passed, dimensions = self.verify(world_config)
        failures = [k for k, ok in dimensions.items() if not ok]
        verdict = "ADMITTED" if passed else "REJECTED"
        return {
            "bridge_version": "2.0",
            "verdict": verdict,
            "admitted": passed,
            "failures": failures,
            "dimensions": dimensions,
            "details": {
                "communication": {
                    "uses_nohn_semantics": bool(_safe_get(
                        world_config.get("semantics", {}),
                        "uses_nohn_semantics", False)),
                },
                "physics": self.physics_details(
                    world_config.get("physics", {})),
                "reality": self.physics_baseline.reality_compliant(
                    world_config.get("physics", {})),
                "identity": {
                    "soul_hash_sha256": bool(_safe_get(
                        world_config.get("identity", {}),
                        "soul_hash_sha256", False)),
                },
                "economy": self.economy_details(
                    world_config.get("economy", {})),
            },
            "stamp": {
                "issued_at": time.time(),
                "algorithm": "compatibility_bridge.v2/fail-closed",
            },
        }


# 使用示例：
# bridge = NohnCompatibilityBridge()
# bridge.vocabulary.register("WZD_MMO_MOVE", "NOHN_STANDARD_MOVE")
# ok, dims = bridge.verify(world_config)
# report = bridge.admit(world_config)      # 一站式入境审查
# if bridge.check_physics_constants(legacy_world.params):
#     standard_soul = bridge.verify_soul_hash(user.hash, public_key=user.pub)
#     standard_action = bridge.translate_intent(user.input)