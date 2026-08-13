<p align="center">
  <img src="assets/banner.png" alt="SPL-Virtual-World-Base banner" style="width:100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/metaverse--D4AF37?style=flat-square" alt="metaverse">  <img src="https://img.shields.io/badge/infrastructure--D4AF37?style=flat-square" alt="infrastructure">  <img src="https://img.shields.io/badge/constitution--D4AF37?style=flat-square" alt="constitution">
</p>

<blockquote align="center">
  <em>Virtual World &amp; Metaverse Infrastructure Foundation</em>
</blockquote>

<div style="max-width:880px;margin:0 auto;padding:0 16px">

## ✦ About

<p style="font-size:15px;line-height:1.8;color:#2C2C2C">SPL-VIRTUAL-WORLD-BASE is the infrastructure framework for virtual worlds and metaverses, built on a three-layer architecture — Constitution, Law, and Bridge — providing a governable, interoperable, and evolvable runtime foundation for virtual spaces. It enables stable bridging and collaboration of assets, rules, and agents across different worlds.</p>

<p align="center">
  <img src="assets/overview.png" alt="SPL-Virtual-World-Base overview" style="width:100%">
</p>

</div>

<p align="center">— ✦ —</p>

## ✦ Quick Start

```bash
git clone git@github.com:NOHN-AI/SPL-virtual-world-base.git
cd SPL-virtual-world-base
# Pure Python ≥3.8 — standard library only, nothing to install
# Launch the GUI demo (requires a graphical environment; spawns two built-in agents)
python virtual_world.py
```

Programmatic start:

```python
from virtual_world import NohnWorld, NohnVisualApp
nexus = NohnWorld()
nexus.spawn("Explorer_01", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
NohnVisualApp(nexus).root.mainloop()
```

<p align="center">— ✦ —</p>

## ✦ Architecture

<div style="max-width:880px;margin:0 auto;padding:0 16px">

The stack is organized as four separable layers, so that rules (read-only), the auditor (neutral referee), the system (implementation), and the demo client never conflate:

- **Constitution rules** (`constitution_rules.py`) — the primordial axioms and ten governance laws, permanently locked as the root trust anchor. `NOHN_LAW_AXIOMS` is the single authoritative source for all constants.
- **Audit engine** (`audit_engine.py`) — the second-perspective cognitive auditor (`ResponsibilityAccount` + pluggable `AuditPlugin`s + `SecondPerspectiveAuditor` with an 18-dimension compliance review). It is the *referee*, not part of the world.
- **Law** (`law/`) — four standard layers:
  - *Communication protocol standard*
  - *Global economic unified standard* — currency, peg, proof-of-reserve, redemption
  - *Identity attestation standard* — soul-hash bound identity
  - *Physics baseline standard* — gravity / time / scale constants
- **System** (`system/`) — the real implementation layer: persistent ledger, ≥2/3 referendum consensus, agent engine, headless runtime, REST/WS API, machine-readable protocol schemas, and production security.
- **Bridge** (`compatibility_bridge.py`) — the only "customs" through which legacy worlds join Nohn territory:
  - `translate_intent()` — semantic wash: maps vendor-private instructions to the Nohn standard vocabulary, stripping hidden interpretation rights.
  - `check_physics_constants()` — rejects worlds whose physics constants diverge from `NOHN_LAW_AXIOMS`.
  - `verify_soul_hash()` — verifies identity against the soul-hash anchor.

The demo runtime (`virtual_world.py`) wires these together with an `EconomySystem`, `TaskGenerator`, and `NohnAgent`, mounted on the real `system.World`.

</div>

## ✦ Architecture Modules

Every class below is verified against the current source. Grouped by the six layers of the Nohn™ world stack:

| Layer | Module (class) | Responsibility |
|---|---|---|
| **Constitution** | `SpatialSubstrate` | world topology, dimensions, boundaries, minimal units |
| | `TemporalSubstrate` | time flow and event sequencing |
| | `CausalClosure` | causal-chain tracking, external intervention detection |
| | `ExistenceAxiom` | entity creation, verification, and destruction |
| | `GenesisCondition` | world initialization and integrity validation |
| | `ImmutableWorldRule` | rules that require global referendum to amend |
| | `WorldCentralBrain` | central coordination of world subsystems |
| **Soul** | `SoulAttestation` | soul registration and verification |
| | `SoulLedger` | identity ledger |
| | `MemoryInalienability` | memory non-seizability |
| | `MemoryGuardian` | memory sealing and tamper detection |
| | `IndependentWill` | autonomous will (MARL-based, not behavior trees) |
| | `MemoryVault` | secure memory storage |
| **Audit** | `ResponsibilityAccount` | named accountability for every governance action |
| | `AuditPlugin` | pluggable audit checks |
| | `CognitiveAuditEngine` | cognitive-audit engine core |
| | `SecondPerspectiveAuditor` | comprehensive compliance review |
| | `DecentralizationGovernance` | decentralized governance |
| | `AestheticCompliance` | aesthetic/rendering compliance |
| | `AuditReport` | structured audit report |
| **Perpetuity** | `WorldPerpetuity` | eternal world-running record |
| | `HistoryLedger` | history ledger |
| | `SnapshotRegistry` | snapshot registration and recovery |
| **Interoperability** | `NohnCompatibilityBridge` | cross-world bridge protocol |
| | `MandatoryInteroperability` | mandatory interop protocol |
| | `UniversalVocabulary` | universal semantic vocabulary |
| | `PhysicsBaseline` | physics baseline alignment |
| | `IdentityProtocol` | identity protocol compatibility |
| | `EconomicBaseline` | economic standard compliance |
| **Runtime** | `NohnWorld` | world container |
| | `NohnAgent` | agent |
| | `EconomySystem` | economy system |
| | `TaskGenerator` | task generation |
| | `NohnVisualApp` | visualization app |
| | `ConsensusEngine` | consensus among world actors |
| | `SimulationEngine` | world simulation loop |

## ✦ Enterprise Usage

The base is a **protocol guardian + reference implementation**, not a single-operator platform. An enterprise integrates in one of three ways:

### A. Protocol Participant (self-hosted, data stays on-premise)

Run your own implementation inside your own data center, conforming to the four `law/` standards, and validate on-boarding before joining the network:

```python
from system.protocol import ProtocolValidator

ok, failures = ProtocolValidator().validate(world_config)
# ok=True  -> on-board to the Nohn network
# ok=False -> isolated at the failed layer(s)
```

**Hard constraint**: your raw data (souls, assets, memories, world state) never leaves your data center. The protocol layer exchanges only verifiable proofs — hashes, signatures, Merkle roots, proof-of-reserve — never raw data.

### B. Reference Implementation (embedded)

Use the audited reference world directly:

```python
from system.runtime import World

world = World("my-world", data_dir="./my_data")
world.spawn_agent("ab" * 32)
world.tick()
print(world.audit_summary())   # 18-dimension second-perspective audit
```

### C. API Integration (REST + WebSocket)

Run the service and integrate over HTTP:

```python
from system.api import serve
serve(world, host="0.0.0.0", port=8000)
```

Key endpoints: `GET /health`, `GET /world`, `GET /audit`, `POST /protocol/validate`, `POST /agent/spawn`, `POST /auth/issue`, `GET/POST /economy/*`, `WS /ws/world`.

### Customization boundary

Enterprise-specific differences live in the **configuration layer** (industry parameters, jurisdiction, deployment topology) — never in the core constitution, audit, or consensus rules, which remain identical for every enterprise.

<p align="center">— ✦ —</p>

## ✦ Project Structure

```
SPL-Virtual-world-base/
├── constitution_rules.py        # constitution rules: axioms + ten governance laws + NOHN_LAW_AXIOMS
├── audit_engine.py              # second-perspective auditor: 18-dimension compliance review
├── constitution.py              # thin aggregate layer (backward-compatible re-export)
├── compatibility_bridge.py      # legacy-world "customs": semantic wash + physics/soul checks
├── virtual_world.py             # demo runtime (GUI/headless), mounted on system.World
├── system/                      # real implementation layer
│   ├── ledger.py                #   persistent Soul/History/Economic ledger (SQLite)
│   ├── consensus.py             #   ≥2/3 referendum consensus + governance
│   ├── agent_engine.py          #   need-driven agents + memory sealing
│   ├── runtime.py               #   genesis assembly + tick loop + audit report
│   ├── api.py                   #   REST + WebSocket + HMAC auth
│   ├── protocol.py              #   machine-readable law schemas + validator
│   └── keys.py                  #   signing key management
├── law/                         # Communication / Economic / Identity / Physics standards
├── assets/                      # banner.svg/png, overview.svg/png
└── LICENSE
```

## ✦ License & Authorization

This repository is **not open-source**. Dual-track model: free for individual non-commercial research; paid commercial authorization required for government / enterprise. See [LICENSE](./LICENSE).

**Trademark notice**: "Nohn™" and "Second Perspective™" are unregistered trademarks in the virtual-world domain, protected under unfair-competition law and common-law passing-off doctrine. Any unauthorized commercial use constitutes infringement.

**Licensing inquiries**:
- International / global: ai@nohnlins.com
- China: lin@secondai.top

<p align="center">
  <a href="https://github.com/NOHN-AI">NOHN-AI</a>
  &nbsp;·&nbsp;
  <a href="https://www.nohnlins.com/">nohnlins.com</a>
  &nbsp;·&nbsp;
  <a href="mailto:ai@nohnlins.com">ai@nohnlins.com</a>
</p>
<p align="center"><sub>NOHN AI · SPL-VIRTUAL-WORLD-BASE</sub></p>
