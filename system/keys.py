# system/keys.py - 密钥管理（服务端签名密钥 + 用户身份密钥链路）
# ============================================================
# 职责分两层：
#   A. 服务端签名密钥（原有）：为鉴权层提供 HMAC 签名密钥的生成/持久化/加载。
#      - 无状态签名 token 在服务重启后仍可验证（密钥不随进程消失）
#      - 签名不可伪造（密钥仅服务端持有）
#   B. 用户身份密钥链路（定稿方案·Passkey 单设备）：
#      - 真实身份凭证 = Ed25519 私钥，仅驻留持有者单台设备安全区（内存态，永不上传）
#      - soul_hash = SHA-256(公钥字节)，公钥可公开围观，哈希只是 ID 不是秘密
#      - 登录 = 挑战-响应：服务端下发一次性 nonce，设备签名，服务端仅验签
#      - 服务端不存储、不接触任何私钥材料；私钥丢失 = 身份冻结（永久）
#
# 依赖方向：system/keys.py 无内部依赖（仅标准库 + cryptography），可被
#   api.py / ledger.py / audit_engine.py 引用。不反向依赖任何模块。
# ============================================================

import base64
import hashlib
import os
import secrets
from typing import Dict, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

# HMAC-SHA256 签名密钥长度（32 字节 / 256 bit）
_KEY_BYTES = 32

# Ed25519 私钥 / 公钥原始字节长度
_ED25519_RAW_BYTES = 32


# ============================================================
# A. 服务端签名密钥（原有，勿动语义）
# ============================================================

def generate_key() -> bytes:
    """生成新的随机签名密钥。"""
    return secrets.token_bytes(_KEY_BYTES)


def load_or_create_key(key_path: str) -> bytes:
    """
    加载既有签名密钥；不存在则生成并持久化到 key_path。
    落盘后尝试收紧权限为 0600（POSIX；Windows 上为 no-op，无害）。
    """
    if key_path and os.path.exists(key_path):
        with open(key_path, "rb") as f:
            key = f.read()
        if key:
            return key
    key = generate_key()
    if key_path:
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        # 先写临时文件再原子替换，避免并发/中断留下半截密钥
        tmp_path = key_path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(key)
        os.replace(tmp_path, key_path)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass  # Windows 不支持 POSIX 权限位，忽略
    return key


# ============================================================
# B. 用户身份密钥链路（定稿方案：Passkey 单设备 + 公钥指纹）
# ============================================================

def generate_user_keypair() -> Dict[str, bytes]:
    """
    生成用户身份密钥对。返回 {"secret": 私钥32B, "pubkey": 公钥32B}。
    私钥必须仅驻留设备安全区（内存态），任何路径均不得落盘/上传。
    """
    private_key = Ed25519PrivateKey.generate()
    secret = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    pubkey = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return {"secret": secret, "pubkey": pubkey}


def public_from_private(secret_raw: bytes) -> bytes:
    """由私钥派生对应公钥（设备端用）。"""
    return Ed25519PrivateKey.from_private_bytes(secret_raw).public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


def derive_soul_hash_from_pubkey(pubkey_raw: bytes) -> str:
    """
    单一权威身份派生规则：soul_hash = SHA-256(公钥字节)。
    公钥公开、哈希只是 ID；盗窃哈希无法冒充，签名需要私钥。
    """
    return hashlib.sha256(pubkey_raw).hexdigest()


def sign_with_device(secret_raw: bytes, message: bytes) -> bytes:
    """设备端签名：私钥批准签名动作（用户经生物识别在场验证后触发）。"""
    return Ed25519PrivateKey.from_private_bytes(secret_raw).sign(message)


def verify_signature(pubkey_raw: bytes, message: bytes, signature: bytes) -> bool:
    """服务端验签：只接受公钥与签名，永远不接触私钥。"""
    try:
        Ed25519PublicKey.from_public_bytes(pubkey_raw).verify(signature, message)
        return True
    except (InvalidSignature, ValueError):
        return False


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64_decode(value: str) -> bytes:
    return base64.b64decode(value)


def build_genesis_proof(secret_raw: bytes, declaration: Dict) -> Optional[Dict]:
    """
    构建创世注册证明（服务端可验证，且不接触私钥）：
      {"pubkey": b64(公钥), "declaration": 创世声明, "sig": b64(签名)}
    签名对象 = 声明的规范 JSON（sort_keys + ensure_ascii=False）。
    服务端验：1) 签名有效（公钥验声明） 2) soul_hash == SHA-256(公钥)。
    """
    if not isinstance(declaration, dict) or not declaration:
        return None
    pubkey = public_from_private(secret_raw)
    canonical = __import__("json").dumps(
        declaration, sort_keys=True, ensure_ascii=False
    )
    sig = sign_with_device(secret_raw, canonical.encode("utf-8"))
    return {
        "pubkey": _b64(pubkey),
        "declaration": declaration,
        "sig": _b64(sig),
    }


def verify_genesis_proof(genesis_proof: Dict) -> bool:
    """服务端整体验注册证明：公钥派生指纹 + 签名有效。"""
    if not isinstance(genesis_proof, dict):
        return False
    try:
        pubkey = _b64_decode(genesis_proof.get("pubkey", ""))
        canonical = __import__("json").dumps(
            genesis_proof.get("declaration"), sort_keys=True, ensure_ascii=False
        )
        sig = _b64_decode(genesis_proof.get("sig", ""))
    except Exception:
        return False
    if len(pubkey) != _ED25519_RAW_BYTES or len(sig) != 64:
        return False
    return verify_signature(pubkey, canonical.encode("utf-8"), sig)


__all__ = [
    "generate_key",
    "load_or_create_key",
    "generate_user_keypair",
    "public_from_private",
    "derive_soul_hash_from_pubkey",
    "sign_with_device",
    "verify_signature",
    "build_genesis_proof",
    "verify_genesis_proof",
]