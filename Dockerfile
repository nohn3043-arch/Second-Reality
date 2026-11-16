# Second Reality Distributed System — 世界节点镜像
#
# 只做一件事：把仓库代码装进镜像，用 system/api.py 的 serve() 对外提供
# REST + WebSocket 服务（默认 8000 端口）。不改任何核心代码。
#
# 基础镜像：Python >= 3.8（README 要求），用 slim 变体。
# 依赖：核心运行时只需要 cryptography（Ed25519 签名，见 README）。
# GUI 演示用的 pygame 刻意不装进镜像 —— 容器里跑的是无头世界服务。
FROM python:3.12-slim

WORKDIR /app

# 只装运行时真正需要的依赖；不用 requirements.txt（仓库里没有这个文件，
# 不要凭空编一个依赖清单）。
RUN pip install --no-cache-dir cryptography

# 复制仓库代码（.dockerignore 会挡住 .git、__pycache__、本地数据目录等）。
COPY . /app

# 服务配置全部走环境变量，见 docker/entrypoint.py。
# TLS_CERTFILE / TLS_KEYFILE 留空 = 明文 HTTP，仅限可信内网；
# 生产部署必须二选一：挂证书走 serve() 的 TLS，或前置反向代理终结 TLS。
ENV WORLD_ID=second-reality-world \
    DATA_DIR=/data \
    HOST=0.0.0.0 \
    PORT=8000 \
    TLS_CERTFILE= \
    TLS_KEYFILE= \
    REQUIRE_TLS=false

EXPOSE 8000

# 世界数据（含世界私钥与操作者私钥）必须落盘持久化，见 docker-compose.yml。
VOLUME ["/data"]

# 健康检查走 system/api.py 里真实存在的 GET /health（无需鉴权，
# 返回 {"status": "ok", "world_id": ...}）。若容器内启用了 TLS，
# 探针自动改走 https（自签名证书不校验，只验服务是否活着）。
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "/app/docker/healthcheck.py"]

CMD ["python", "/app/docker/entrypoint.py"]
