# system/protocol.py - 互认协议（law 四标准机器可读化）
# ============================================================
# 职责：把 law/ 目录的四份人读规范，固化为机器可读的 JSON Schema，
#   并提供统一验证器。这是"多实现网络"互认的机器前提：
#   任何第三方企业实现，只需提供符合下列 Schema 的 world_config，
#   即可程序化通过并网审查（audit_engine / MandatoryInteroperability）。
#
# 单一权威来源：判定阈值仍引用 constitution_rules.NOHN_LAW_AXIOMS，
#   本模块只做"契约序列化 + 校验编排"，不重复硬编码物理常数。
# ============================================================

from typing import Any, Dict, List, Tuple

from constitution_rules import (
    NOHN_LAW_AXIOMS,
    PhysicsBaseline,
    IdentityProtocol,
    EconomicBaseline,
    UniversalVocabulary,
)

# ---- 四份机器可读契约（JSON Schema，供第三方实现自检与文档生成）----

PHYSICS_SCHEMA: Dict[str, Any] = {
    "title": "Physics Baseline Standard (law/Physics baseline standard)",
    "type": "object",
    "required": ["gravity", "time_dilation", "unit_scale", "no_dimensional_inflation"],
    "properties": {
        "gravity": {"type": "number", "const": NOHN_LAW_AXIOMS["gravity"]},
        "time_dilation": {"type": "number", "const": NOHN_LAW_AXIOMS["time_dilation"]},
        "unit_scale": {"type": "string", "const": NOHN_LAW_AXIOMS["unit_scale"]},
        "no_dimensional_inflation": {"type": "boolean", "const": True},
    },
}

IDENTITY_SCHEMA: Dict[str, Any] = {
    "title": "Identity Attestation Standard (law/Identity attestation standard)",
    "type": "object",
    "required": ["soul_hash_sha256", "non_revocable", "cross_world_portable", "asset_bound"],
    "properties": {
        "soul_hash_sha256": {"type": "boolean", "const": True},
        "non_revocable": {"type": "boolean", "const": True},
        "cross_world_portable": {"type": "boolean", "const": True},
        "asset_bound": {"type": "boolean", "const": True},
    },
}

COMMUNICATION_SCHEMA: Dict[str, Any] = {
    "title": "Communication Protocol Standard (law/Communication protocol standard)",
    "type": "object",
    "required": ["uses_nohn_semantics", "unknown_downgraded", "vocab_mapped"],
    "properties": {
        "uses_nohn_semantics": {"type": "boolean", "const": True},
        "unknown_downgraded": {"type": "boolean", "const": True},
        "vocab_mapped": {"type": "boolean", "const": True},
    },
}

ECONOMY_SCHEMA: Dict[str, Any] = {
    "title": "Global Economic Unified Standard (law/Global economic unified standard)",
    "type": "object",
    "required": [
        "real_peg_1to1", "proof_of_reserve", "redemption_right",
        "unilateral_fee", "asset_bound_to_soul", "oracle_sources",
    ],
    "properties": {
        "real_peg_1to1": {"type": "boolean", "const": True},
        "proof_of_reserve": {"type": "boolean", "const": True},
        "redemption_right": {"type": "boolean", "const": True},
        "unilateral_fee": {"type": "boolean", "const": False},
        "asset_bound_to_soul": {"type": "boolean", "const": True},
        "oracle_sources": {
            "type": "array",
            "minItems": NOHN_LAW_AXIOMS["oracle_min_sources"],
        },
    },
}

SCHEMAS: Dict[str, Dict[str, Any]] = {
    "physics": PHYSICS_SCHEMA,
    "identity": IDENTITY_SCHEMA,
    "communication": COMMUNICATION_SCHEMA,
    "economy": ECONOMY_SCHEMA,
}


class ProtocolValidator:
    """统一并网验证器：四维度逐一校验，返回 (是否通过, 失败维度列表)。"""

    def __init__(self):
        self.physics_baseline = PhysicsBaseline()
        self.identity_protocol = IdentityProtocol()
        self.economic_baseline = EconomicBaseline()
        self.standard_vocabulary = UniversalVocabulary()

    def validate(self, world_config: Dict) -> Tuple[bool, List[str]]:
        """校验一个世界配置是否满足 law 四标准。失败维度按层隔离。"""
        failures: List[str] = []
        if not self.standard_vocabulary.translatable(world_config.get("semantics", {})):
            failures.append("communication")
        if not self.physics_baseline.aligned(world_config.get("physics", {})):
            failures.append("physics")
        if not self.identity_protocol.compatible(world_config.get("identity", {})):
            failures.append("identity")
        if not self.economic_baseline.compliant(world_config.get("economy", {})):
            failures.append("economy")
        return (len(failures) == 0, failures)

    def validate_dict(self, world_config: Dict) -> Dict[str, bool]:
        """返回逐维度布尔结果，供审计/API 结构化消费。"""
        return {
            "communication": self.standard_vocabulary.translatable(
                world_config.get("semantics", {})),
            "physics": self.physics_baseline.aligned(world_config.get("physics", {})),
            "identity": self.identity_protocol.compatible(world_config.get("identity", {})),
            "economy": self.economic_baseline.compliant(world_config.get("economy", {})),
        }


__all__ = ["SCHEMAS", "ProtocolValidator", "PHYSICS_SCHEMA", "IDENTITY_SCHEMA",
           "COMMUNICATION_SCHEMA", "ECONOMY_SCHEMA"]
