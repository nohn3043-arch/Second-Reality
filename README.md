<div align="center">
  <img src="assets/banner.png" alt="SPL-Virtual-World-Base banner" width="100%" />
</div>

<p align="center">
  <img src="https://img.shields.io/badge/metaverse-D4AF37?style=flat-square" alt="metaverse" />
  <img src="https://img.shields.io/badge/infrastructure-D4AF37?style=flat-square" alt="infrastructure" />
  <img src="https://img.shields.io/badge/constitution-D4AF37?style=flat-square" alt="constitution" />
  <img src="https://img.shields.io/badge/second--perspective-D4AF37?style=flat-square" alt="second-perspective" />
</p>

<p align="center">
  <em>Virtual World & Metaverse Infrastructure Base</em>
</p>

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px; font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #2b2b2b; line-height: 1.8;">

## ✦ About

<p style="font-size: 16px; line-height: 1.9; color: #2F2F2F; margin: 0 0 24px;">
  <strong>SPL-VIRTUAL-WORLD-BASE</strong> is a runnable infrastructure base for virtual worlds and the metaverse, organized as a "Constitution — Law — Bridge" stack with a real implementation layer (<code>system/</code>) underneath. It delivers:
</p>

<ul>
  <li><strong>An end-to-end account &amp; world runtime</strong> — persistent hash-chained ledger, ≥2/3 referendum consensus, need-driven agents, headless tick loop, REST + WebSocket API, and a multi-layer account system (credentials → sessions → tiered authorization → social recovery) wired together for real.</li>
  <li><strong>The Second Perspective Cognitive Auditor</strong> as the neutral referee — a 19-dimension compliance review (including a functionally executed authentication-security dimension) that can be run on demand against any world instance.</li>
  <li><strong>Geo-distributed readiness</strong> — hybrid logical clocks, spatial sharding with handover, AOI delta sync, partition guard with Merkle diff-merge, and hierarchical (intra-DC fast ring + inter-DC epoch) consensus, all speaking over real TCP and verified by a 3-node local cluster smoke test.</li>
  <li><strong>AR / edge access</strong> — an Edge SDK for device-credential login, AOI viewport sync, and cross-DC relocation, plus roaming, account-abstraction and key-rotation modules.</li>
</ul>

<div align="center">
  <img src="assets/overview.png" alt="SPL-Virtual-World-Base overview" width="100%" />
</div>

</div>

<p align="center">— ✦ —</p>

## ✦ Quick Start

```bash
# Primary source: GitHub (repository: Second-Reality)
git clone https://github.com/nohn3043-arch/Second-Reality.git

# Mirror: Gitee
# git clone https://gitee.com/nohn-ecosystem/SPL-virtual-world-core.git

cd Second-Reality

# Python ≥3.8; core runtime requires only cryptography (Ed25519 signing)
# pip install cryptography   # GUI demo additionally requires pygame
# No GPU dependency, no database service dependency — runs on any hardware

# 1. Society simulation demo (standalone, in-memory; pygame GUI, 60×60 grid, 30 agents)
python virtual_world.py

# 2. Infrastructure verification (no GUI required)
python smoke_test.py            # account/session/recovery security paths — ~1s
python tools/cluster_smoke.py   # 3-node local geo-distributed cluster — ~14s
python tools/edge_smoke.py      # AR edge access path — <1s
```

### Programmatic Launch (Reference World)

```python
from system.runtime import World
from system.keys import generate_user_keypair, build_genesis_proof
from system.ledger import derive_soul_hash

world = World("my-world", data_dir="./my_data")
device = generate_user_keypair()   # Private key stays on device, never uploaded
genesis_proof = build_genesis_proof(device["secret"], {"genesis_id": "my-first-soul"})
soul_hash = derive_soul_hash(genesis_proof)
world.spawn_agent(soul_hash=soul_hash, genesis_proof=genesis_proof)
world.tick()
print(world.audit_summary())       # 19-dimension Second Perspective audit
```

### API Service

```python
from system.api import serve
serve(world, host="0.0.0.0", port=8000)
```

<p align="center">— ✦ —</p>

## ✦ Architecture

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px; font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #2b2b2b; line-height: 1.8;">

The stack keeps rules (read-only), the auditor (neutral referee), the implementation, and the demo strictly separated:

- <strong>Constitution Rules</strong> (`constitution_rules.py`): original axioms and ten governance laws, locked as the root trust anchor. `NOHN_LAW_AXIOMS` is the single authoritative source for shared constants (gravity, time dilation, unit scale, soul-hash length, oracle minimum sources).
- <strong>Audit Engine</strong> (`audit_engine.py`): Second Perspective Cognitive Auditor — `ResponsibilityAccount` + pluggable `AuditPlugin` + `CognitiveAuditEngine` (counterfactual `reconstruct()`) + `SecondPerspectiveAuditor`. Runs a 19-dimension compliance review; the authentication-security dimension functionally executes the account stack in an isolated in-memory world rather than probing attributes.
- <strong>Law</strong> (`law/`): four human-readable standards — Communication Protocol · Unified Global Economy (currency, pegging, reserve proof, redemption) · Identity Attestation (soul-hash-bound, with the V2.2 credential-recovery clause) · Physics Baseline. Their machine-readable JSON-Schema counterparts live in `system/protocol.py` and drive onboarding validation.
- <strong>System</strong> (`system/`, 23 modules): the real implementation layer — ledger, consensus, agent engine, headless runtime, REST/WS API, protocol schema, account-system layers, geo-distributed subsystems, and edge access. See the module table below.
- <strong>Bridge</strong> (`compatibility_bridge.py`): the customs checkpoint for legacy worlds entering Nohn territory — `translate_intent()` semantic cleansing, `check_physics_constants()` verification, `verify_soul_hash()` identity verification.

### System Modules (23)

Core runtime:

| Module | Role | Notes |
|---|---|---|
| `runtime.py` | World genesis assembly + tick loop + causal chain + snapshots | STORAGE backend selection |
| `ledger.py` | Persistent ledger: soul / history hash chain / economy / snapshot + ShardRouter | SQLite (default), memory, PostgreSQL |
| `consensus.py` | Proposal referendum (≥2/3 supermajority), governance, genesis bootstrap exemption | Real TCP transport |
| `agent_engine.py` | Need-driven agent decisions + HMAC memory sealing + gas metering | Memory inalienability guarantee |
| `api.py` | REST + WebSocket service, challenge-response auth, rate limiting | Pure standard library |
| `protocol.py` | Four law standards as machine-readable JSON Schema + onboarding validator | — |
| `keys.py` | Ed25519 keys, Shamir secret sharing, KMS abstraction (file / cloud) | — |

Account system:

| Module | Layer | Role |
|---|---|---|
| `credentials.py` | Credential (L1) | One soul, multi-device credentials (server stores public keys only) |
| `session.py` | Authentication (L2) | Stateful access/refresh tokens, revocable; store pluggable (SQLite / Memory / Redis) |
| `authorization.py` | Authorization (L3) | Tiered authorization (instant / delayed / multisig / manual) + risk scoring |
| `recovery.py` | Recovery (L4) | Social recovery (3/5 guardian vote) + 7-day cancellable time lock |
| `identity_root.py` | Identity root (L0) | Master keypair + Shamir(3,5) sharing; server-side helper for thin clients (`POST /identity/root/generate`, zero key material persisted) |
| `account_abstraction.py` | Session keys (ERC-4337-style) | Session keys with spend-limit / expiry / action-scope constraints; daily operations signed by session keys via challenge-response — the master key stays offline (`/aa/*`) |
| `key_rotation.py` | Key lifecycle | Server signing keys rotated on a schedule; tokens embed a key ID — retired keys keep verifying old tokens, revoked keys kill them instantly (`/keys/*`, wired into session signing) |

Geo-distributed (wired into the runtime as the horizon-2 subsystem):

| Module | Role |
|---|---|
| `hlc.py` | Hybrid logical clock — consistent cross-node event ordering |
| `spatial_sharding.py` | Geographic shards + `ShardRouter` + migration handover protocol |
| `aoi_sync.py` | Area-of-interest delta synchronization (`AoiTracker` / `DeltaSync` / `SyncScheduler`) |
| `partition_guard.py` | Partition detection, local-autonomy degradation, Merkle diff-tree merge |
| `hierarchical_consensus.py` | Intra-DC fast ring + inter-DC epoch slow ring (eventual consistency) |
| `cluster.py` | Cluster wiring, heartbeat loop, inbound whitelist, transport dispatcher |

Edge & roaming:

| Module | Role |
|---|---|
| `edge_sdk.py` | AR-glasses access: device credential enrollment, challenge login, AOI viewport sync, nearest-DC routing, cross-DC relocation |
| `soul_roaming.py` | Cross-world identity roaming: certificates signed by the source world, verified (signature + expiry + soul-hash derivation + optional user challenge-response) by the target world, with local soul mapping (`/roaming/*`; memory transfer channel still forthcoming) |

**Multi-Backend Deployment (same codebase, four backends)**

Select the storage backend via the `STORAGE` environment variable before running; default `sqlite`:

| STORAGE | Ledger | Session | Use Case |
|---|---|---|---|
| `sqlite` (default) | On-disk SQLite (`.world_data/`) | Same database as ledger | Single machine / demo |
| `memory` | In-process `:memory:` (no disk) | In-memory dict | Testing / stateless demo |
| `redis` | Local SQLite | Redis (requires `pip install redis`; falls back to SQLite if absent) | Multi-instance shared sessions |
| `postgres` | PostgreSQL via psycopg2 (DSN from `DATABASE_URL` or `pg_dsn`) | SQLite | Large-scale ledger — requires the driver, does not silently fall back |

```bash
STORAGE=redis REDIS_URL=redis://cache:6379/0 python -m system.api            # scale-out
STORAGE=postgres DATABASE_URL=postgresql://user:pass@db:5432/world python -m system.api
```

Supporting deployment-level abstractions: `ShardRouter` (routing by `soul_hash`, default single shard), `SessionStore` (externalized session state), `CloudKmsProvider` (cloud KMS envelope encryption; falls back to the file backend when no cloud client is injected). Multi-datacenter deployment means laying out shard units — not code changes.

**Hardware Requirements & Deployment Topology**

Workload is pure CPU logical simulation (need state machine + SHA-256 hash chain + Ed25519 signing): no matrix operations, no local LLM inference, no GPU dependency. Runs on anything from a Raspberry Pi to a multi-datacenter cluster.

| Tier | Scenario | Reference Hardware | Storage Backend |
|---|---|---|---|
| Minimum | Demo / smoke tests / audit trail | 1 CPU core · 256MB–1GB RAM | `memory` / `sqlite` |
| Standard | Hundred-level agents + full 19-dimension audit | 2–4 cores · 2–4GB · SSD | `sqlite` |
| Scale | Thousand-level agents / production multi-instance | 4–8 cores · 8–16GB · SSD · Redis/PG | `redis` / `postgres` |

- Single agent decision is constant time; world tick is O(N) (N = agent count). The cost of scale is ledger I/O and disk growth, not compute.
- The only path that introduces external compute is LLM augmentation (via external API); the local core stays low-configuration.

</div>

<p align="center">— ✦ —</p>

## ✦ Demo & Verification

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px;">

**Society Simulation Demo** (`virtual_world.py`) — a standalone, in-memory society simulation that demonstrates the agent and economic dynamics of the stack. It runs independently of `system/` (no infrastructure required):

- 60×60 grid world, 30 initial agents, 80 resource nodes, 8 buildings
- Need-driven agents (five-level need model) with perceive → think → act loops and STM→LTM memory consolidation
- Economy with periodic UBI (every 10 ticks), wealth tax (every 30), inflation (every 50), and a wealth hard-cap rule
- `run_gui()` renders the live world with pygame (pause / speed control / agent inspection); `run_headless(n)` runs n ticks and prints statistics plus a compliance score

**Verification scripts** (all currently pass):

| Script | Scope | Runtime |
|---|---|---|
| `smoke_test.py` | Genesis proof → soul hash, challenge-response signing, session issuance, per-device revocation, auth-security audit, shard router, recovery pollution checks | ~1s |
| `tools/cluster_smoke.py` | 3-node local cluster: heartbeat, epoch broadcast, AOI replication, HLC convergence, migration handover, partition degradation & recovery | ~14s |
| `tools/edge_smoke.py` | Edge device: credential enrollment, challenge login, AOI viewport deltas, nearest-DC routing, cross-DC relocation, revocation | <1s |
| `tools/wiring_smoke.py` | Account abstraction (session-key issue → challenge → execute → constraints → revoke), key rotation (retired verifies / revoked kills tokens), identity root (Shamir 3-of-5 recovery), soul roaming (issue → tamper rejection → verify → map) | ~2s |

**Expert Review Reports** (`expert_report.py`) — exports the auditor's machine-readable verdicts plus ledger hash anchors as a locally reproducible Markdown report (see `reports/`). The report itself is a display layer; every anchor (hash / verdict) points back to re-runnable primitives, so reviewers never need to trust the report.

</div>

<p align="center">— ✦ —</p>

## ✦ Enterprise Integration

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px;">

This base is a <strong>protocol guardian + reference implementation</strong>, not a single-operator platform. Three integration paths:

### A. Protocol Participant (Self-hosted, Data Stays Local)

Run a self-developed implementation compliant with the four standards. Validate before onboarding:

```python
from system.protocol import ProtocolValidator
ok, failures = ProtocolValidator().validate(world_config)
# ok=True  -> Join the Nohn network
# ok=False -> Isolated at the failed layer
```

<strong>Hard constraint</strong>: raw data (souls, assets, memories, world state) never leaves the data center. The protocol layer only exchanges verifiable proofs — hashes, signatures, Merkle roots, reserve proofs.

### B. Reference Implementation (Embedded)

Use the audited reference world directly — see "Programmatic Launch" above. Private keys stay in the device's memory; the ledger stores only public keys and hashes.

### C. API Integration (REST + WebSocket)

Key endpoints: `GET /health`, `GET /world`, `POST /world/tick`, `GET /world/snapshot`, `GET /audit`, `GET /audit/full`, `POST /agent/spawn`, `POST /protocol/validate`, `/auth/*` (challenge → issue → refresh → revoke, delayed-operation approve/cancel/process), `/credentials/*` (bind / list / revoke), `/aa/*` (account abstraction: session-key issue / list / revoke / challenge / execute), `/keys/*` (signing-key list / rotate / revoke), `POST /identity/root/generate`, `/roaming/*` (world register / certificate issue / verify / map / mapping lookup), `/recovery/*` (initiate / guardian/add / approve / cancel / finalize), `/economy/*` (por / issue / deposit / redeem), and the persistent WebSocket stream `/ws/world`.

</div>

<p align="center">— ✦ —</p>

## ✦ Project Structure

```text
Second-Reality/
├── constitution_rules.py        # Constitution: axioms + ten governance laws + NOHN_LAW_AXIOMS
├── audit_engine.py              # Second Perspective Auditor: 19-dimension compliance review
├── constitution.py              # Aggregation layer (backward-compatible re-exports)
├── compatibility_bridge.py      # Legacy world "customs": semantic / physics / soul verification
├── virtual_world.py             # Society simulation demo (standalone, pygame GUI / headless)
├── smoke_test.py                # Account & session security verification
├── expert_report.py             # Expert review report export (auditor verdicts + hash anchors)
├── system/                      # Real implementation layer (23 modules)
│   ├── runtime.py               #   Genesis assembly + tick loop + STORAGE selection
│   ├── ledger.py                #   Persistent ledger + ShardRouter + PG/memory backends
│   ├── consensus.py             #   ≥2/3 referendum consensus + governance
│   ├── agent_engine.py          #   Need-driven agent + memory sealing
│   ├── api.py                   #   REST + WS + challenge-response auth + rate limiting
│   ├── protocol.py              #   Machine-readable law schema + validator
│   ├── keys.py                  #   Ed25519 + Shamir + KMS abstraction
│   ├── credentials.py           #   Account L1: multi-device credentials
│   ├── session.py               #   Account L2: stateful revocable sessions
│   ├── authorization.py         #   Account L3: tiered authorization + risk engine
│   ├── recovery.py              #   Account L4: social recovery + time lock
│   ├── identity_root.py         #   Account L0: master key + Shamir (server-side thin-client helper)
│   ├── account_abstraction.py   #   Session keys with spend/expiry/scope constraints (/aa/*)
│   ├── key_rotation.py          #   Server signing-key rotation, wired into session tokens (/keys/*)
│   ├── hlc.py                   #   Hybrid logical clock
│   ├── spatial_sharding.py      #   Geo sharding + migration handover
│   ├── aoi_sync.py              #   AOI delta synchronization
│   ├── partition_guard.py       #   Partition detection + Merkle diff-merge
│   ├── hierarchical_consensus.py#   Intra-DC fast ring + inter-DC epoch
│   ├── cluster.py               #   Cluster wiring + heartbeat + dispatcher
│   ├── edge_sdk.py              #   AR / edge device access SDK
│   └── soul_roaming.py          #   Cross-world roaming certificates + soul mapping (/roaming/*)
├── law/                         # Communication / Economic / Identity / Physics standards (text)
├── tools/                       # cluster_smoke / edge_smoke / doc generation utilities
├── reports/                     # Exported expert review reports
├── assets/                      # banner.svg/png, overview.svg/png
├── .gitignore
├── LICENSE
└── README.md
```

<p align="center">— ✦ —</p>

## ✦ Ecosystem

SPL-VIRTUAL-WORLD-BASE is a member of the NOHN AI ecosystem — a family of projects built around Second Perspective causal audit and deterministic execution:

| Project | Repository | Role |
|---|---|---|
| **Second-Perspective (GCAE)** | [nohn3043-arch/second-perspective](https://github.com/nohn3043-arch/second-perspective) | Global Cognitive Audit Engine — five-operator causal audit core (IMDA 95/100) |
| **NOMOS** | [nohn3043-arch/second-perspective](https://github.com/nohn3043-arch/second-perspective) (`Intelligent-Decision-Hub--Nomos` branch) | Auditable deterministic decision center (IMDA 95/100) |
| **SPL-G1** | [nohn3043-arch/SPL-G1](https://github.com/nohn3043-arch/SPL-G1) | Hardware causal audit trusted computing unit (TCU) |
| **SPL-Virtual-World-Base** | [nohn3043-arch/Second-Reality](https://github.com/nohn3043-arch/Second-Reality) | Virtual world & metaverse infrastructure (Constitution / Law / Bridge) |
| **Story-Engine** | [nohn3043-arch/story-engine](https://github.com/nohn3043-arch/story-engine) | Long-form narrative consistency engine |
| **Antares** | [nohn3043-arch/Antares](https://github.com/nohn3043-arch/Antares) | GFSIP v1.0 — Federated stable interoperability protocol with causal audit |
| **Anthropomorphic-Agent-Engine** | [nohn3043-arch/Anthropomorphic-Agent-Engine](https://github.com/nohn3043-arch/Anthropomorphic-Agent-Engine) | Deterministic anthropomorphic psychology engine (SPL Pure Core V8.0) |
| **PAGES** | [nohn3043-arch/pages](https://github.com/nohn3043-arch/pages) | NOHN AI ecosystem official landing page |

<p align="center">— ✦ —</p>

## ✦ License & Authorization

This repository is <strong>not open source</strong>. Dual-track model: free for personal non-commercial research; paid commercial license required for government / enterprise use. See [LICENSE](./LICENSE).

<strong>Trademark Notice</strong>: "Nohn™" and "Second Perspective™" are unregistered trademarks in the virtual world domain, protected by unfair competition law and common law passing-off principles. Any unauthorized commercial use constitutes infringement.

<strong>License Inquiries</strong>: International / Global — [ai@nohnlins.com](mailto:ai@nohnlins.com) · China — [lin@secondai.top](mailto:lin@secondai.top)

<p align="center">
  <a href="https://github.com/nohn3043-arch">GitHub</a>
  &nbsp;·&nbsp;
  <a href="https://www.nohnlins.com/">nohnlins.com</a>
  &nbsp;·&nbsp;
  <a href="mailto:ai@nohnlins.com">ai@nohnlins.com</a>
</p>
<p align="center"><sub>NOHN AI · SPL-VIRTUAL-WORLD-BASE</sub></p>
