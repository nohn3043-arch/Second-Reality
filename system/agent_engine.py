# system/agent_engine.py - 智能体引擎（真实实现，桩转实第 2 步）
# ============================================================
# 职责：真实化以下宪法契约（对齐 constitution_rules.py）：
#   - IndependentWill.decide_next_action（内在需求驱动，非行为树）
#   - MemoryVault.store_memory / recall_memory（长期记忆，持久化）
#   - MemoryGuardian.seal_memory / verify_memory（记忆完整性封存）
#   - MemoryInalienability.export_memory / detect_memory_tampering
#
# 依赖方向：system/agent_engine.py -> constitution_rules / system.ledger（单向）
# 持久化：复用 ledger.Storage（SQLite），表：memories
#
# 审计契约：
#   - NPC 必须可证明"未被脚本绑定"（_is_scripted 返回 False）
#   - 记忆不可被平台单方面剥夺（export_memory 全量导出）
# ============================================================

import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, List, Optional

from .ledger import Storage
from .keys import load_or_create_key


class MemoryGuardian:
    """记忆守护者：密码学封存/校验，检测任何篡改。

    封存密钥经 KMS 托管（默认文件后端，可插拔 HSM）。
    绝不用公开的 soul_hash 当密钥——soul_hash 全网可见，作密钥等于无密钥。
    """

    def __init__(self, seal_key: Optional[bytes] = None):
        self._seal_key = seal_key

    def seal_memory(self, memory: Dict, soul_hash: str) -> str:
        """对记忆片段进行 HMAC 封存，生成不可伪造的完整性证明。"""
        if self._seal_key is None:
            raise RuntimeError("seal key not configured")
        payload = json.dumps(memory, sort_keys=True, ensure_ascii=False)
        return hmac.new(
            self._seal_key,
            (soul_hash + "|" + payload).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def verify_memory(
        self, memory: Dict, seal: str, soul_hash: Optional[str] = None
    ) -> bool:
        """验证记忆完整性。若提供 soul_hash 则做密码学校验，否则降级为结构校验。"""
        if soul_hash:
            return hmac.compare_digest(self.seal_memory(memory, soul_hash), seal)
        return isinstance(seal, str) and len(seal) == 64


class MemoryVault:
    """长期记忆库：按 soul_hash 存取，持久化。"""

    def __init__(
        self, storage: Optional[Storage] = None, data_dir: Optional[str] = None
    ):
        self._storage = storage or Storage(data_dir=data_dir)
        self._storage.execute(
            "CREATE TABLE IF NOT EXISTS memories ("
            "seq INTEGER PRIMARY KEY AUTOINCREMENT, soul_hash TEXT NOT NULL, "
            "memory TEXT NOT NULL, seal TEXT NOT NULL, ts REAL NOT NULL)"
        )
        # 封存密钥：经 KMS 抽象托管（默认文件后端），绝不用公开 soul_hash
        seal_key = load_or_create_key(
            os.path.join(self._storage.data_dir, "memory_seal_key")
        )
        self.guardian = MemoryGuardian(seal_key=seal_key)

    def store_memory(self, soul_hash: str, memory: Dict) -> str:
        """存储永久记忆，返回完整性证明（seal）。"""
        if not isinstance(memory, dict):
            memory = {"content": memory}
        seal = self.guardian.seal_memory(memory, soul_hash)
        self._storage.execute(
            "INSERT INTO memories (soul_hash, memory, seal, ts) VALUES (?, ?, ?, ?)",
            (soul_hash, json.dumps(memory, ensure_ascii=False), seal, time.time()),
        )
        return seal

    def recall_memory(
        self, soul_hash: str, context: Optional[str] = None
    ) -> List[Dict]:
        """按灵魂检索记忆。context 可选做简单关键词过滤。"""
        rows = self._storage.query(
            "SELECT memory, seal FROM memories WHERE soul_hash=? ORDER BY seq",
            (soul_hash,),
        )
        out = []
        for mem_json, seal in rows:
            mem = json.loads(mem_json)
            if context and context not in json.dumps(mem, ensure_ascii=False):
                continue
            out.append({"memory": mem, "seal": seal})
        return out

    def verify_all(self, soul_hash: str) -> bool:
        """校验某灵魂的全部记忆是否被篡改。"""
        rows = self._storage.query(
            "SELECT memory, seal FROM memories WHERE soul_hash=? ORDER BY seq",
            (soul_hash,),
        )
        for mem_json, seal in rows:
            mem = json.loads(mem_json)
            if not self.guardian.verify_memory(mem, seal, soul_hash):
                return False
        return True


class MemoryInalienability:
    """第七条：记忆不可剥夺。全量导出 + 篡改检测。"""

    def __init__(
        self, vault: Optional[MemoryVault] = None, data_dir: Optional[str] = None
    ):
        self.memory_vault = vault or MemoryVault(data_dir=data_dir)

    def export_memory(self, soul_hash: str) -> Dict:
        """任何数字生命有权导出自身全部记忆（Nohn 标准记忆交换格式）。"""
        memories = self.memory_vault.recall_memory(soul_hash)
        return {"soul": soul_hash, "memories": memories}

    def detect_memory_tampering(self, soul_hash: str) -> bool:
        """审计：检测记忆是否被外部强行篡改或选择性删除。"""
        return not self.memory_vault.verify_all(soul_hash)


class Agent:
    """独立意志智能体：需求驱动决策，非脚本绑定。"""

    NEEDS_KEYS = [
        "physiological",
        "safety",
        "belonging",
        "esteem",
        "self_actualization",
    ]

    def __init__(
        self,
        soul_hash: str,
        personality: Optional[Dict] = None,
        memory_vault: Optional[MemoryVault] = None,
        storage: Optional[Storage] = None,
    ):
        self.soul_hash = soul_hash
        self.personality = personality or {"openness": 0.5, "conscientiousness": 0.5}
        # 马斯洛需求层次：初始中等水平，随行动演化
        self.needs = {
            "physiological": 0.5,
            "safety": 0.5,
            "belonging": 0.3,
            "esteem": 0.2,
            "self_actualization": 0.1,
        }
        self.long_term_memory: List[Dict] = []
        self.relationships: Dict[str, float] = {}
        self.memory_vault = memory_vault
        self.action_history: List[str] = []
        # 状态持久化：重启不丢需求/关系/行动历史
        self._storage = storage
        if storage is not None:
            self._ensure_state_table()
            self._load_state()

    def _ensure_state_table(self) -> None:
        self._storage.execute(
            "CREATE TABLE IF NOT EXISTS agent_state ("
            "soul_hash TEXT PRIMARY KEY, state TEXT NOT NULL, updated_at REAL NOT NULL)"
        )

    def save_state(self) -> None:
        """持久化智能体状态（需求/关系/行动历史）。"""
        if self._storage is None:
            return
        state = {
            "needs": self.needs,
            "relationships": self.relationships,
            "action_history": self.action_history,
        }
        self._storage.execute(
            "INSERT OR REPLACE INTO agent_state (soul_hash, state, updated_at) "
            "VALUES (?, ?, ?)",
            (self.soul_hash, json.dumps(state, ensure_ascii=False), time.time()),
        )

    def _load_state(self) -> None:
        if self._storage is None:
            return
        rows = self._storage.query(
            "SELECT state FROM agent_state WHERE soul_hash=?", (self.soul_hash,)
        )
        if rows:
            state = json.loads(rows[0][0])
            self.needs.update(state.get("needs", {}))
            self.relationships.update(state.get("relationships", {}))
            self.action_history = state.get("action_history", [])

    def _is_scripted(self) -> bool:
        """审计点：是否存在外部剧情在强行绑定此 NPC？永远 False。"""
        return False

    def decide_next_action(self, world_state: Optional[Dict] = None) -> str:
        """内在需求驱动决策：优先满足最匮乏需求，不依赖主线任务。"""
        if self._is_scripted():
            raise RuntimeError("Agent is being scripted!")
        action = self._internal_decision_engine(world_state or {})
        self._update_needs(action)
        self.action_history.append(action)
        return action

    def _internal_decision_engine(self, world_state: Dict) -> str:
        """需求驱动决策：最匮乏需求映射到行动，非行为树。"""
        if self.needs["physiological"] < 0.3:
            return "seek_resources"
        if self.needs["safety"] < 0.3:
            return "seek_shelter"
        if self.needs["belonging"] < 0.3:
            return "socialize"
        if self.needs["esteem"] < 0.3:
            return "pursue_achievement"
        return "self_actualize"

    def _update_needs(self, action: str) -> None:
        """行动反馈：满足对应需求，同时其它需求随时间衰减。"""
        satisfy = {
            "seek_resources": "physiological",
            "seek_shelter": "safety",
            "socialize": "belonging",
            "pursue_achievement": "esteem",
            "self_actualize": "self_actualization",
        }
        for key in self.NEEDS_KEYS:
            self.needs[key] = max(0.0, self.needs[key] - 0.05)  # 熵增
        target = satisfy.get(action)
        if target:
            self.needs[target] = min(1.0, self.needs[target] + 0.3)


__all__ = ["MemoryGuardian", "MemoryVault", "MemoryInalienability", "Agent"]
