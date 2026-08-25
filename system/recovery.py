"""第 4 层：恢复层（Recovery Manager）。

社交恢复 + 时间锁。化解 non_revocable 与「丢钥匙=资产永久冻结」的矛盾：
灵魂不可撤销，但凭证可安全更换。
"""

import base64
import time
import uuid


class RecoveryManager:
    """社交恢复：N 守护者 M 同意 + 时间锁（延迟期可取消）。"""

    def __init__(
        self,
        storage,
        credential_vault,
        guardian_threshold: int = 3,
        timelock_seconds: int = 7 * 24 * 3600,
    ):
        self._storage = storage
        self._credentials = credential_vault
        self.guardian_threshold = guardian_threshold
        self.timelock_seconds = timelock_seconds

    def add_guardian(self, soul_hash: str, guardian_soul: str) -> bool:
        """添加守护者。"""
        self._storage.execute(
            "INSERT OR IGNORE INTO guardians (soul_hash, guardian_soul, created_at) "
            "VALUES (?, ?, ?)",
            (soul_hash, guardian_soul, time.time()),
        )
        return True

    def get_guardians(self, soul_hash: str):
        rows = self._storage.query(
            "SELECT guardian_soul FROM guardians WHERE soul_hash=?", (soul_hash,)
        )
        return [r[0] for r in rows]

    def initiate_recovery(self, soul_hash: str, new_public_key_b64: str) -> str:
        """发起恢复：创建请求，进入时间锁。返回 request_id。"""
        request_id = uuid.uuid4().hex
        now = time.time()
        self._storage.execute(
            "INSERT INTO recovery_requests "
            "(request_id, soul_hash, new_public_key, created_at, timelock_until, status) "
            "VALUES (?, ?, ?, ?, ?, 'pending')",
            (request_id, soul_hash, new_public_key_b64, now, now + self.timelock_seconds),
        )
        return request_id

    def approve_recovery(self, request_id: str, guardian_soul: str) -> bool:
        """守护者投票。非守护者无权投票。"""
        rows = self._storage.query(
            "SELECT soul_hash, status FROM recovery_requests WHERE request_id=?",
            (request_id,),
        )
        if not rows or rows[0][1] != "pending":
            return False
        soul_hash = rows[0][0]
        if guardian_soul not in self.get_guardians(soul_hash):
            return False
        self._storage.execute(
            "INSERT OR IGNORE INTO recovery_votes (request_id, guardian_soul, ts) "
            "VALUES (?, ?, ?)",
            (request_id, guardian_soul, time.time()),
        )
        return True

    def vote_count(self, request_id: str) -> int:
        rows = self._storage.query(
            "SELECT COUNT(*) FROM recovery_votes WHERE request_id=?", (request_id,)
        )
        return rows[0][0] if rows else 0

    def cancel_recovery(self, request_id: str) -> bool:
        """原设备在时间锁内取消。"""
        self._storage.execute(
            "UPDATE recovery_requests SET status='cancelled' "
            "WHERE request_id=? AND status='pending'",
            (request_id,),
        )
        return True

    def finalize_recovery(self, request_id: str):
        """时间锁到期 + 票数达标 → 换新凭证。返回新 credential_id 或 None。"""
        rows = self._storage.query(
            "SELECT soul_hash, new_public_key, timelock_until, status "
            "FROM recovery_requests WHERE request_id=?",
            (request_id,),
        )
        if not rows:
            return None
        soul_hash, new_public_key_b64, timelock_until, status = rows[0]
        if status != "pending":
            return None
        if time.time() < timelock_until:
            return None  # 时间锁未到期
        if self.vote_count(request_id) < self.guardian_threshold:
            return None  # 票数不足
        pubkey = base64.b64decode(new_public_key_b64)
        credential_id = self._credentials.bind_credential(soul_hash, pubkey, "recovered")
        self._storage.execute(
            "UPDATE recovery_requests SET status='finalized' WHERE request_id=?",
            (request_id,),
        )
        return credential_id
