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
  <strong>SPL-VIRTUAL-WORLD-BASE</strong> is an infrastructure framework for virtual worlds and the metaverse, built on a three-layer architecture of "Constitution — Law — Bridge." It provides a governable, interoperable, and evolvable runtime base for virtual spaces, enabling stable alignment of assets, rules, and agents across worlds. The Second Perspective Cognitive Auditor serves as the neutral referee of the entire stack.
</p>

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
# No GPU dependency, no database service dependency — runs on any hardware (see "Hardware Requirements & Deployment Topology")
# Launch GUI demo (requires a graphical environment; two built-in agents)
python virtual_world.py
```

### Programmatic Launch

```python
from virtual_world import NohnWorld, run_gui, run_headless

nexus = NohnWorld()          # Built-in initial resources and two agents
nexus.spawn_agent()          # Optional: spawn an additional agent
run_headless(200, verbose=True)  # Headless simulation 200 ticks; use run_gui() if graphical env available
```

<p align="center">— ✦ —</p>

## ✦ Architecture

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px; font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #2b2b2b; line-height: 1.8;">

The stack is divided into four separable layers, ensuring that rules (read-only), the auditor (neutral referee), the system (implementation), and the demo client never conflate:

- <strong>Constitution Rules</strong> (`constitution_rules.py`): Original axioms and ten governance laws, permanently locked as the root trust anchor. `NOHN_LAW_AXIOMS` is the single authoritative source for all constants.
- <strong>Audit Engine</strong> (`audit_engine.py`): Second Perspective Cognitive Auditor (`ResponsibilityAccount` + pluggable `AuditPlugin` + `SecondPerspectiveAuditor`, with 19-dimension compliance review including authentication security). It is the referee, not part of the world.
- <strong>Law</strong> (`law/`): Four standard layers: Communication Protocol Standard · Unified Global Economic Standard (currency, pegging, reserve proof, redemption) · Identity Proof Standard (soul hash bound identity, with V2.2 credential recovery clause) · Physics Baseline Standard (gravity / time / scale constants).
- <strong>System</strong> (`system/`): Real implementation layer: persistent ledger, ≥2/3 referendum consensus, agent engine, headless runtime, REST/WS API, machine-readable protocol schema, six-layer account system (identity root / credentials / session / authorization / recovery / audit). All exposed state must pass the Second Perspective Auditor's 19-dimension compliance review.
- <strong>Bridge</strong> (`compatibility_bridge.py`): The sole "customs checkpoint" for legacy worlds entering Nohn territory: `translate_intent()` semantic cleansing (removes implicit interpretation rights), `check_physics_constants()` physics constant verification, `verify_soul_hash()` soul hash identity verification.

### System Module Details

`system/` is the runnable implementation carrier for the entire stack, adopting a progressive "stub-to-real" strategy to realize all constitutional contracts. The core runtime depends only on `cryptography` (Ed25519 signing); no database service dependency, no GPU dependency — storage backends (SQLite / Memory / Redis / PG) and key backends (file / cloud KMS) are all pluggable.

| Module | Role | Core Capabilities | Persistence |
|---|---|---|---|
| `__init__.py` | Module entry | Defines system layer boundaries, constraints, and module planning | - |
| `ledger.py` | State ledger | Soul hash attestation (lazy loading + pagination), world history hash chain, reserve proof ledger, world snapshots | SQLite (default `.world_data/` directory) |
| `consensus.py` | Consensus network | Node registration (real signature verification), proposal referendum (≥2/3 supermajority), decentralized governance, genesis bootstrap exemption | Reuses ledger storage |
| `agent_engine.py` | Agent engine | Need-driven agent decision-making, memory sealing/verification (KMS key), memory inalienability guarantee, state persistence | Reuses ledger storage |
| `runtime.py` | Headless runtime | World genesis assembly, tick main loop, causal chain recording, snapshot persistence, 19-dimension audit reporting | Reuses ledger storage |
| `protocol.py` | Interoperability protocol | Four legal standards as machine-readable JSON Schema, third-party implementation onboarding verification | - |
| `api.py` | Service interface | REST service, stateful session authentication (revocable), account system routing, concurrency locks + rate limiting | Session state persisted |
| `keys.py` | Key management | Ed25519 keys, Shamir secret sharing, KMS abstraction (file / cloud KMS pluggable), signing key loading | Key files on disk / cloud KMS托管 |
| `identity_root.py` | Identity root (Layer 0) | Master identity keypair + Shamir(3,5) secret sharing, plaintext master private key generated then immediately cleared | - |
| `credentials.py` | Credential layer (Layer 1) | One soul-bound multi-device credential (server stores only public keys), bind / revoke / verify | SQLite |
| `session.py` | Authentication layer (Layer 2) | Stateful session: access token (15min) + refresh token (rotatable, revocable); session storage pluggable (SQLite / Memory / Redis) | SessionStore pluggable |
| `authorization.py` | Authorization layer (Layer 3) | Tiered authorization (micro-instant / medium-delayed / large-multisig / extra-large-manual) + risk scoring | - |
| `recovery.py` | Recovery layer (Layer 4) | Social recovery (3/5 guardian vote) + time lock (7-day cancellable) | SQLite |

**Multi-Backend Deployment (same codebase, three backends)**

Select storage backend via `STORAGE` environment variable before running; default `sqlite`:

| STORAGE | Ledger | Session | Use Case |
|---|---|---|---|
| `sqlite` (default) | On-disk SQLite (`.world_data/`) | Same database as ledger | Single machine / demo |
| `memory` | In-process `:memory:` (no disk) | In-memory dict | Testing / stateless demo |
| `redis` | Local SQLite | Redis (requires `pip install redis`, falls back to SQLite if absent) | Production horizontal scaling, multi-instance shared sessions |
| `postgres` | Reserved PG driver (currently falls back to SQLite) | SQLite | Production large-scale ledger |

```bash
STORAGE=redis REDIS_URL=redis://cache:6379/0 python -m system.api   # Production example
```

Supporting deployment-level abstractions: `ShardRouter` (shard routing by `soul_hash`, default `SingleShardRouter` single shard), `SessionStore` (externalized session state), `CloudKmsProvider` (cloud KMS envelope encryption, auto-falls back to file backend when no cloud client injected). Multi-datacenter deployment simply lays out units by soul shard — no code changes required.

**Core Features:**
1. Low dependencies: Core runtime requires only `cryptography` (Ed25519 signing); GUI demo requires `pygame`; `redis` backend optional. No database service dependency, no GPU dependency — all storage and key backends are pluggable
2. Full-chain auditability: All operations are traceable and verifiable, fully compliant with the Second Perspective Audit Engine's 19-dimension requirements
3. Multi-implementation inter-recognition: Provides machine-readable protocol standards, supports third-party enterprises building self-developed implementations for network onboarding
4. Production-grade security: Six-layer account system (identity root / credentials / session / authorization / recovery / audit), Shamir secret sharing, KMS key escrow, stateful revocable sessions, social recovery
5. Horizontal scalability: Pluggable storage backends (SQLite / Memory / Redis / PG), shard routing interface ready, externalizable state — multi-datacenter deployment is configuration, not code changes

**Hardware Requirements & Deployment Topology**

Workload is pure CPU logical simulation (need state machine + SHA-256 hash chain + Ed25519 signing), with no matrix operations, no local LLM inference, no GPU dependency. Hardware threshold is extremely low — runs on anything from a Raspberry Pi to a multi-datacenter cluster; the difference is deployment topology, not code.

| Tier | Scenario | Reference Hardware | Storage Backend |
|---|---|---|---|
| Minimum | Single-world demo / smoke_test / audit trail | 1 CPU core · 256MB–1GB RAM · tens of MB disk | `memory` / `sqlite` |
| Standard | Hundred-level agents + full 19-dimension audit | 2–4 cores · 2–4GB · SSD | `sqlite` |
| Scale | Thousand-level agents / production multi-instance | 4–8 cores · 8–16GB · SSD · Redis | `redis` / `postgres` |

- Compute bottleneck is not CPU: Single agent decision is constant time (need threshold mapping), world tick complexity is O(N) (N = agent count). The primary cost of scale growth is ledger and memory storage I/O and disk growth, not compute.
- Multi-instance horizontal scaling: `STORAGE=redis` externalized sessions + `ShardRouter` sharding by `soul_hash` — multi-datacenter deployment is configuration, not code changes.
- The only path that introduces external compute is LLM augmentation (via external API, local requires only network); the local core remains low-configuration.

The demo runtime (`virtual_world.py`) assembles the above layers with `EconomySystem`, `TaskGenerator`, `NohnAgent`, mounted on the real `system.World`.

</div>

<p align="center">— ✦ —</p>

## ✦ Core Modules

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px;">

Grouped by the six layers of the Nohn™ World Stack (all classes verified against current source code):

| Layer | Module (Class) | Responsibility |
|---|---|---|
| **Constitution** | `SpatialSubstrate` | World topology, dimensions, boundaries, minimal units |
|  | `TemporalSubstrate` | Time flow and event ordering |
|  | `CausalClosure` | Causal chain tracking, external intervention detection |
|  | `ExistenceAxiom` | Entity creation, verification, and destruction |
|  | `GenesisCondition` | World initialization and integrity verification |
|  | `ImmutableWorldRule` | Rules modifiable only via global referendum |
|  | `WorldCentralBrain` | Central coordination of world subsystems |
| **Soul** | `SoulAttestation` | Soul registration and verification |
|  | `SoulLedger` | Identity ledger |
|  | `MemoryInalienability` | Memory inalienability |
|  | `MemoryGuardian` | Memory sealing and tamper detection |
|  | `IndependentWill` | Autonomous will (MARL-based, not behavior tree) |
|  | `MemoryVault` | Secure memory storage |
| **Audit** | `ResponsibilityAccount` | Named accountability for each governance action |
|  | `AuditPlugin` | Pluggable audit checks |
|  | `CognitiveAuditEngine` | Cognitive audit engine core |
|  | `SecondPerspectiveAuditor` | Comprehensive compliance review |
|  | `DecentralizationGovernance` | Decentralized governance |
|  | `AestheticCompliance` | Aesthetic / rendering compliance |
|  | `AuditReport` | Structured audit reports |
| **Perpetuity** | `WorldPerpetuity` | Eternal world runtime records |
|  | `HistoryLedger` | History ledger |
|  | `SnapshotRegistry` | Snapshot registration and recovery |
| **Interoperability** | `NohnCompatibilityBridge` | Cross-world bridging protocol |
|  | `MandatoryInteroperability` | Mandatory interoperability protocol |
|  | `UniversalVocabulary` | Universal semantic vocabulary |
|  | `PhysicsBaseline` | Physics baseline alignment |
|  | `IdentityProtocol` | Identity protocol compatibility |
|  | `EconomicBaseline` | Economic standard compliance |
| **Runtime** | `NohnWorld` | World container |
|  | `NohnAgent` | Agent |
|  | `EconomySystem` | Economic system |
|  | `TaskGenerator` | Task generation |
|  | `NohnVisualApp` | Visualization application |
|  | `ConsensusEngine` | World participant consensus |
|  | `SimulationEngine` | World simulation loop |
| **System** | `World` (`system/runtime.py`) | Genesis assembly + tick loop + 19-dimension audit + snapshots + account system six-layer assembly |
|  | `Storage` · `SoulLedger` · `HistoryLedger` · `EconomicReserve` · `SnapshotRegistry` (`system/ledger.py`) | Persistent SQLite ledger (soul / history / economy / snapshot / credentials / session / recovery) |
|  | `ConsensusNetwork` · `Governance` (`system/consensus.py`) | ≥2/3 referendum consensus + governance + genesis bootstrap exemption |
|  | `Agent` (`system/agent_engine.py`) | Need-driven agent + memory sealing + state persistence |
|  | `IdentityRoot` (`system/identity_root.py`) | Identity root + Shamir secret sharing |
|  | `CredentialVault` (`system/credentials.py`) | Multi-device credential management |
|  | `SessionManager` (`system/session.py`) | Stateful revocable sessions |
|  | `AuthorizationEngine` (`system/authorization.py`) | Tiered authorization + risk engine |
|  | `RecoveryManager` (`system/recovery.py`) | Social recovery + time lock |
|  | `ProtocolValidator` (`system/protocol.py`) | Machine-readable law validation + network onboarding |
|  | `SoulAuth` · `WorldAPI` (`system/api.py`) | REST + stateful session authentication + account system routing |

</div>

<p align="center">— ✦ —</p>

## ✦ Enterprise Integration

<div style="max-width: 1100px; margin: 0 auto; padding: 0 16px;">

This base is a <strong>protocol guardian + reference implementation</strong>, not a single-operator platform. Enterprises can integrate in three ways:

### A. Protocol Participant (Self-hosted, Data Stays Local)

Run a self-developed implementation compliant with the four `law/` standards in your own data center. Validate before onboarding:

```python
from system.protocol import ProtocolValidator
ok, failures = ProtocolValidator().validate(world_config)
# ok=True  -> Join the Nohn network
# ok=False -> Isolated at the failed layer
```

<strong>Hard constraint</strong>: Raw data (souls, assets, memories, world state) never leaves the data center. The protocol layer only exchanges verifiable proofs — hashes, signatures, Merkle roots, reserve proofs — never raw data.

### B. Reference Implementation (Embedded)

Directly use the audited reference world:

```python
from system.runtime import World
from system.keys import generate_user_keypair, build_genesis_proof
from system.ledger import derive_soul_hash

world = World("my-world", data_dir="./my_data")
device = generate_user_keypair()   # Private key stays in device secure enclave (memory), never uploaded
genesis_proof = build_genesis_proof(device["secret"], {"genesis_id": "my-first-soul"})
soul_hash = derive_soul_hash(genesis_proof)   # = SHA-256(public_key)
world.spawn_agent(soul_hash=soul_hash, genesis_proof=genesis_proof)
world.tick()
print(world.audit_summary())   # 19-dimension Second Perspective audit
```

### C. API Integration (REST + WebSocket)

```python
from system.api import serve
serve(world, host="0.0.0.0", port=8000)
```

Key endpoints: `GET /health`, `GET /world`, `GET /audit`, `POST /protocol/validate`, `POST /agent/spawn`, `POST /auth/issue`, `POST /auth/refresh`, `POST /auth/revoke`, `GET/POST /credentials/*`, `POST /recovery/*`, `GET/POST /economy/*`.

</div>

<p align="center">— ✦ —</p>

## ✦ Project Structure

```text
Second-Reality/
├── constitution_rules.py        # Constitution rules: axioms + ten governance laws + NOHN_LAW_AXIOMS
├── audit_engine.py              # Second Perspective Auditor: 19-dimension compliance review (incl. auth security)
├── constitution.py              # Aggregation layer (backward-compatible re-exports)
├── compatibility_bridge.py      # Legacy world "customs": semantic cleansing + physics / soul verification
├── virtual_world.py             # Demo runtime (GUI / headless), mounted on system.World
├── _build_vw*.py                # Virtual world build script series
├── _gen*.py                     # Content generation script series
├── _write_vw.py                 # World writing tool
├── package.json                 # Node.js dependencies (documentation generation tools)
├── system/                      # Real implementation layer
│   ├── __init__.py
│   ├── ledger.py                #   Persistent ledger (Soul/History/Economic/credentials/session/recovery) + ShardRouter + memory backend
│   ├── consensus.py             #   ≥2/3 referendum consensus + governance + genesis bootstrap exemption
│   ├── agent_engine.py          #   Need-driven agent + memory sealing + state persistence
│   ├── runtime.py               #   Genesis assembly + tick loop + 19-dimension audit + account system assembly (STORAGE backend selection)
│   ├── api.py                   #   REST + stateful session auth + account system routing + rate limiting
│   ├── protocol.py              #   Machine-readable law schema + validator
│   ├── keys.py                  #   Signing key management + Shamir secret sharing + KMS abstraction (file / CloudKmsProvider)
│   ├── identity_root.py         #   Identity root (Layer 0): master key + Shamir secret sharing
│   ├── credentials.py           #   Credential layer (Layer 1): multi-device credential management
│   ├── session.py               #   Authentication layer (Layer 2): stateful revocable session (SessionStore pluggable)
│   ├── authorization.py         #   Authorization layer (Layer 3): tiered authorization + risk engine
│   └── recovery.py              #   Recovery layer (Layer 4): social recovery + time lock
├── law/                         # Communication / Economic / Identity / Physics standards
├── tools/                       # Tool scripts
│   ├── gen_gcae_doc.js          #   GCAE document generator
│   ├── md2pdf.py                #   Markdown to PDF tool
│   └── updated_rules.md         #   Rules update log
├── docs/                        # Technical documentation
│   ├── audit_engine_vs_safety_benchmarks.md  # Audit engine safety benchmark report
│   └── audit_engine_vs_safety_benchmarks.pdf # PDF version
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
