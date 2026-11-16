# -*- coding: utf-8 -*-
"""容器入口：按环境变量启动一个 system.World 并用 system/api.py 的 serve() 对外服务。

只做部署装配，不改核心逻辑：
  - World 的构造方式与 README / tools/nohn_serve_boot.py 一致：
    World(world_id, data_dir=data_dir)
  - serve() 的调用方式与 system/api.py 的真实签名一致：
    serve(world, host=..., port=...,
          tls_certfile=..., tls_keyfile=..., require_tls=...)
    其中 tls_certfile / tls_keyfile 两者同时提供时启用 HTTPS；
    require_tls=True 时若未提供证书，serve() 会直接拒绝启动
    （RuntimeError，明文 HTTP 禁止用于生产部署）。

与 tools/nohn_serve_boot.py 的区别（刻意）：
  - 本入口不注册本机操作者灵魂、不导出 world_card.json；
    世界名片与跨世界注册请走 nohn_serve_boot.py 或 /roaming/* 接口。
  - 本入口支持用环境变量传证书，让 serve() 直接终结 TLS。

环境变量：
  WORLD_ID       世界名，默认 second-reality-world
  DATA_DIR       世界数据目录，默认 /data（容器内挂卷用）
  HOST           监听地址，默认 0.0.0.0（容器内必须如此，否则宿主机连不上）
  PORT           监听端口，默认 8000
  TLS_CERTFILE   TLS 证书路径，留空 = 不启用容器内 TLS
  TLS_KEYFILE    TLS 私钥路径，留空 = 不启用容器内 TLS
  REQUIRE_TLS    true/1/yes 时要求必须启用 TLS，否则拒绝启动
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from system.api import serve  # noqa: E402
from system.runtime import World  # noqa: E402


def _env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on") \
        if name in os.environ else default


def main() -> int:
    world_id = os.environ.get("WORLD_ID", "second-reality-world")
    data_dir = os.environ.get("DATA_DIR", "/data")
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    tls_certfile = os.environ.get("TLS_CERTFILE", "").strip() or None
    tls_keyfile = os.environ.get("TLS_KEYFILE", "").strip() or None
    require_tls = _env_bool("REQUIRE_TLS", False)

    os.makedirs(data_dir, exist_ok=True)
    world = World(world_id, data_dir=data_dir)
    print(
        "[entrypoint] world=%s data_dir=%s host=%s port=%d tls=%s require_tls=%s"
        % (world_id, data_dir, host, port, bool(tls_certfile and tls_keyfile), require_tls),
        flush=True,
    )
    serve(
        world,
        host=host,
        port=port,
        tls_certfile=tls_certfile,
        tls_keyfile=tls_keyfile,
        require_tls=require_tls,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
