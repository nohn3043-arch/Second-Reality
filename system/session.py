"""第 2 层：认证层（Session Manager）。

有状态会话：access token（短 TTL）+ refresh token（可轮换、可撤销）。
替代原无状态 HMAC token，支持即时吊销（丢设备一键踢下线）。
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid


class SessionManager:
    """有状态会话管理。签名密钥经 KMS 抽象托管（可插拔 HSM）。"""

    def __init__(self, storage, kms_provider, access_ttl: int = 900, refresh_ttl: int = 604800):
        self._storage = storage
        self._kms = kms_provider
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl

    def _signing_key(self) -> bytes:
        return self._kms.get_or_create_key("session_signing_key")

    def _sign(self, payload: bytes) -> bytes:
        return hmac.new(self._signing_key(), payload, hashlib.sha256).digest()

    def issue(self, soul_hash: str):
        """签发 access + refresh。返回 (access_token, refresh_token)。"""
        now = time.time()
        exp = now + self.access_ttl
        payload = json.dumps({"soul": soul_hash, "exp": exp}, sort_keys=True).encode("utf-8")
        access_token = (
            base64.urlsafe_b64encode(payload).decode("ascii")
            + "."
            + base64.urlsafe_b64encode(self._sign(payload)).decode("ascii")
        )
        refresh_token = secrets.token_urlsafe(32)
        session_id = uuid.uuid4().hex
        refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        self._storage.execute(
            "INSERT INTO sessions "
            "(session_id, soul_hash, refresh_hash, created_at, expires_at, revoked) "
            "VALUES (?, ?, ?, ?, ?, 0)",
            (session_id, soul_hash, refresh_hash, now, now + self.refresh_ttl),
        )
        return access_token, refresh_token

    def verify(self, access_token: str):
        """验 access token，返回 soul_hash 或 None。"""
        try:
            payload_b64, sig_b64 = access_token.split(".")
            payload = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
            sig = base64.urlsafe_b64decode(sig_b64.encode("ascii"))
        except Exception:
            return None
        if not hmac.compare_digest(self._sign(payload), sig):
            return None
        try:
            data = json.loads(payload.decode("utf-8"))
        except Exception:
            return None
        if data.get("exp", 0) < time.time():
            return None
        return data.get("soul")

    def refresh(self, refresh_token: str):
        """轮换 refresh token，返回新的 (access_token, refresh_token) 或 None。"""
        refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        rows = self._storage.query(
            "SELECT session_id, soul_hash, expires_at, revoked FROM sessions "
            "WHERE refresh_hash=?",
            (refresh_hash,),
        )
        if not rows:
            return None
        session_id, soul_hash, expires_at, revoked = rows[0]
        if revoked or expires_at < time.time():
            return None
        # 轮换：吊销旧 session，签发新 session（防重放）
        self._storage.execute(
            "UPDATE sessions SET revoked=1 WHERE session_id=?", (session_id,)
        )
        return self.issue(soul_hash)

    def revoke(self, soul_hash: str, session_id: str = None) -> bool:
        """吊销会话。session_id 为 None 时吊销该 soul 全部会话。"""
        if session_id:
            self._storage.execute(
                "UPDATE sessions SET revoked=1 WHERE soul_hash=? AND session_id=?",
                (soul_hash, session_id),
            )
        else:
            self._storage.execute(
                "UPDATE sessions SET revoked=1 WHERE soul_hash=?", (soul_hash,)
            )
        return True
