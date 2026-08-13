# system/keys.py - 密钥管理（生产级安全，桩转真第 1 阶段）
# ============================================================
# 职责：为鉴权层提供 HMAC 签名密钥的生成 / 持久化 / 加载。
#   密钥首次运行时生成并落盘（权限 0600），此后复用，保证：
#   - 无状态签名 token 在服务重启后仍可验证（密钥不随进程消失）
#   - 签名不可伪造（密钥仅服务端持有）
#
# 依赖方向：system/keys.py 无内部依赖（仅标准库），可被 api.py 引用。
# ============================================================

import os
import secrets
from typing import Optional

# HMAC-SHA256 签名密钥长度（32 字节 / 256 bit）
_KEY_BYTES = 32


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


__all__ = ["generate_key", "load_or_create_key"]
