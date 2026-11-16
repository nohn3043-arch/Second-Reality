# -*- coding: utf-8 -*-
"""Docker HEALTHCHECK 探针：调 system/api.py 里真实存在的 GET /health。

/health 无需鉴权，正常返回 {"status": "ok", "world_id": ...}。
容器内启用了 TLS（TLS_CERTFILE 已设置）时改走 https；自签名证书
不做校验，只验证服务是否活着。明文模式下走 http。
"""

import os
import ssl
import urllib.request


def main() -> int:
    port = os.environ.get("PORT", "8000")
    use_tls = bool(os.environ.get("TLS_CERTFILE", "").strip())
    scheme = "https" if use_tls else "http"
    url = "http://127.0.0.1:%s/health" % port if not use_tls \
        else "https://127.0.0.1:%s/health" % port
    ctx = ssl._create_unverified_context() if use_tls else None
    try:
        with urllib.request.urlopen(url, timeout=5, context=ctx) as resp:
            return 0 if resp.status == 200 else 1
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
