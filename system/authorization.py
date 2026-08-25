"""第 3 层：授权层（Authorization Engine）。

分级授权 + 风险引擎。几十亿现实资产，单靠登录成功就放行所有操作是致命的。
"""

import time


class AuthorizationEngine:
    """分级授权：小额即时 / 中额延迟+通知 / 大额多签 / 超大额人工复核。"""

    # 阈值（示例，生产按资产类别配置）
    TIER_SMALL = 1_000
    TIER_MEDIUM = 100_000
    TIER_LARGE = 1_000_000

    def __init__(self, storage=None):
        self._storage = storage

    def classify(self, amount: float) -> str:
        """按金额分级。"""
        if amount < self.TIER_SMALL:
            return "small"
        if amount < self.TIER_MEDIUM:
            return "medium"
        if amount < self.TIER_LARGE:
            return "large"
        return "critical"

    def authorize(self, soul_hash: str, action: str, amount: float) -> dict:
        """返回授权决策：
        {
            "allowed": bool,        # 是否即时放行
            "tier": str,            # small/medium/large/critical
            "required": str,        # 需要的额外授权动作
            "delay_seconds": int,   # 延迟期（0 表示即时）
        }
        """
        tier = self.classify(amount)
        if tier == "small":
            return {"allowed": True, "tier": tier, "required": "none", "delay_seconds": 0}
        if tier == "medium":
            return {
                "allowed": False,
                "tier": tier,
                "required": "delay_and_notify",
                "delay_seconds": 24 * 3600,
            }
        if tier == "large":
            return {
                "allowed": False,
                "tier": tier,
                "required": "guardian_multisig",
                "delay_seconds": 72 * 3600,
            }
        return {
            "allowed": False,
            "tier": tier,
            "required": "multisig_and_manual_review",
            "delay_seconds": 72 * 3600,
        }

    def risk_score(self, context: dict) -> float:
        """风险评分（0~1，越高越可疑）。context 可含 device/ip/geo/behavior。"""
        score = 0.0
        if context.get("new_device"):
            score += 0.3
        if context.get("unusual_ip"):
            score += 0.2
        if context.get("unusual_geo"):
            score += 0.2
        if context.get("unusual_hour"):
            score += 0.1
        if context.get("high_frequency"):
            score += 0.2
        return min(score, 1.0)

    def require_step_up(self, context: dict) -> bool:
        """风险超阈值时要求二次验证（生物识别/多因素）。"""
        return self.risk_score(context) >= 0.5
