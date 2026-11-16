# 云部署指南（Docker）

> 范围声明：本文件只讲“如何把现有代码装进容器跑起来”。它不改任何
> 核心代码、不声称生产就绪。文末的“已知生产缺口”是待办清单，
> 不是已完成项。

## 一、这套部署是什么

- 镜像（`Dockerfile`）：Python 3.12-slim，只装 `cryptography`
  （README 写明核心运行时仅需它，Ed25519 签名用）。GUI 演示用的
  `pygame` 不装进镜像，容器里跑的是无头世界服务。
- 入口（`docker/entrypoint.py`）：按环境变量建一个
  `World(world_id, data_dir=data_dir)`，再调 `system/api.py` 的
  `serve()` 对外提供 REST + WebSocket 服务，默认 8000 端口。
  `serve()` 的真实签名是：
  `serve(world, host="127.0.0.1", port=8000, tls_certfile=None, tls_keyfile=None, require_tls=False)`。
- 健康检查走 `system/api.py` 里真实存在的 `GET /health`（无需鉴权，
  返回 `{"status": "ok", "world_id": ...}`），见 `docker/healthcheck.py`。
- 编排（`docker-compose.yml`）：一个世界节点默认启动，第二个节点可选。

与 `tools/nohn_serve_boot.py` 的区别：那个脚本是在本机起一个
可被另一台电脑联通的世界，会注册本机操作者灵魂并导出
`world_card.json`（世界名片）；容器入口不做这两件事，世界名片与
跨世界注册请走 `nohn_serve_boot.py` 或 `/roaming/*` 接口。

## 二、快速上手

```bash
# 1. 构建并启动一个节点（world-a，宿主机 8000 端口）
docker compose up --build -d

# 2. 验活（/health 无需鉴权）
curl http://127.0.0.1:8000/health
# 预期：{"status": "ok", "world_id": "world-a"}

# 3. 看日志
docker compose logs -f world-a

# 4. 停掉（数据留在 ./data/world-a，下次启动还在）
docker compose down
```

第二个节点（world-b，宿主机 8001 端口，独立世界、独立数据卷）：

```bash
docker compose --profile second-node up --build -d
curl http://127.0.0.1:8001/health
```

只用 Docker 不用 Compose 也可以：

```bash
docker build -t second-reality .
docker run -d --name sr-world -p 8000:8000 \
  -v "$PWD/data/world-a:/data" \
  -e WORLD_ID=world-a \
  second-reality
```

## 三、环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `WORLD_ID` | `second-reality-world` | 世界名 |
| `DATA_DIR` | `/data` | 世界数据目录（容器内挂卷） |
| `HOST` | `0.0.0.0` | 容器内必须为 `0.0.0.0`，否则宿主机连不上 |
| `PORT` | `8000` | 监听端口 |
| `TLS_CERTFILE` | 空 | TLS 证书路径，如 `/certs/fullchain.pem` |
| `TLS_KEYFILE` | 空 | TLS 私钥路径，如 `/certs/privkey.pem` |
| `REQUIRE_TLS` | `false` | `true` 时要求必须启用 TLS，否则拒绝启动 |

## 四、TLS 怎么配（两种做法，二选一）

### 做法 A：让 serve() 直接终结 TLS

把证书放到 `./certs`（Compose 已将其只读挂载到容器内 `/certs`），
再改 `docker-compose.yml` 里对应服务的环境变量：

```yaml
TLS_CERTFILE: "/certs/fullchain.pem"
TLS_KEYFILE: "/certs/privkey.pem"
REQUIRE_TLS: "true"
```

行为以 `system/api.py` 的 `serve()` 为准，都是真实逻辑，不是文档承诺：

- `tls_certfile` 与 `tls_keyfile` 两者同时提供时启用 HTTPS
  （`ssl.SSLContext` + `load_cert_chain`）。
- `require_tls=True` 但未提供证书时，`serve()` 直接抛 `RuntimeError`
  拒绝启动：“明文 HTTP 禁止用于生产部署”。
- 不提供证书且 `require_tls` 为假时，服务以明文 HTTP 启动，
  `serve()` 会在日志里警告：`access_token` / 签名挑战将以明文传输。

### 做法 B：前置反向代理终结 TLS

容器保持明文（`REQUIRE_TLS=false`），前面放 nginx / Caddy 终结 TLS。
这也是 `serve()` 文档字符串里写明的推荐做法之一。
注意：反向代理后客户端 IP 取自 `X-Forwarded-For`，
见文末“已知生产缺口”第 4 条 —— 只有受信代理才能这样接。

### 千万别做的事

`tools/nohn_serve_boot.py` 的文档头写明了：它是“明文 HTTP，
只在可信局域网内跑，不要映射到公网”。不要把那个脚本的启动方式
原样搬到公网，也不要把无 TLS 的容器端口直接暴露到公网。

## 五、数据与密钥

- `./data/<节点>` 是世界数据目录，含世界私钥与操作者私钥，
  等同于本机身份本体：持久化到宿主机、权限收紧、永不提交进仓库、
  永不外发。`.dockerignore` 已把 `data`、`.world_data`、
  `world_card.json` 挡在镜像构建上下文之外。
- 备份就是备份整个数据目录；删卷等于删世界，操作前先停服务。

## 六、已知生产缺口（待办，不是已完成）

以下缺口在当前代码里真实存在，本次提交只加部署文件和文档，
没有修其中任何一项。融资后、对外提供生产服务之前必须逐项处理：

1. **特权端点无角色模型** —— 任何“已认证灵魂”都能调用
   `/keys/rotate`、`/keys/revoke` 等特权端点。
   （`tools/nohn_serve_boot.py` 文档头也写明了这一点。）
2. **集群传输无 TLS、无节点认证** —— 节点之间互联的传输层
   目前没有 TLS 与节点身份认证。
3. **KMS 默认文件后端** —— 密钥管理默认落文件，未接生产级 KMS。
4. **信任 `X-Forwarded-For`** —— `system/api.py` 的 `_client_ip()`
   优先取反向代理传来的 `X-Forwarded-For`；若代理不可信，
   客户端 IP 会被伪造，进而影响限流与审计归因。
   反向代理部署时必须只信任自己控制的代理。

## 七、本次提交改了什么、没改什么

本次提交直接提交到 main 分支，未开 PR。改了：

- `README-zh.md`：旧品牌名 `SPL-VIRTUAL-WORLD-BASE`（含横幅与概览图
  的 alt 文本、正文、生态节、页脚）统一为
  `SECOND REALITY DISTRIBUTED SYSTEM`。Gitee 镜像链接
  `https://gitee.com/nohn-ecosystem/SPL-virtual-world-core.git`
  是 URL 本身，改了会断链，故刻意未动。
- 新增：`Dockerfile`、`docker-compose.yml`、`.dockerignore`、
  `docker/entrypoint.py`、`docker/healthcheck.py`、
  `docs/cloud-deployment.md`（本文件）。

没改：

- 任何 `.py` 核心逻辑（`system/`、`audit_engine.py`、
  `constitution_rules.py` 等一个字没动）；英文 `README.md` 没动。
- 仓库描述（GitHub 页面上显示的 “SPL虚拟世界核心引擎……开源……”）
  不在本次提交里 —— 可用的 GitHub 工具里没有改仓库描述的接口，
  需要仓库所有者在网页上手动改：Settings → About → Description，
  建议改为与 `README-zh.md`“许可与授权”节一致的表述，即
  “并非开源，双轨许可：个人非商业研究免费；政府 / 企业使用需付费商业许可”。
- 旧品牌名在其他文件里的残留（`system/__init__.py` 的注释、
  `GLOSSARY.md`、`package-lock.json` 的 `name` 字段）不在本次
  范围内，如需统一请另行提交。
