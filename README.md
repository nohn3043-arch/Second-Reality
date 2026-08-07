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
git clone git@github.com:NOHN-AI/SPL-VIRTUAL-WORLD-BASE.git
cd SPL-VIRTUAL-WORLD-BASE
# Pure Python ≥3.8 — standard library only, nothing to install
python virtual_world.py --init demo
```

<p align="center">— ✦ —</p>

## ✦ Three-Layer Architecture

<div style="max-width:880px;margin:0 auto;padding:0 16px">

- **Constitution** (`constitution.py`) — the primordial axioms of the virtual world, permanently locked as the root trust anchor. Embeds a ported **cognitive-audit engine** (`ResponsibilityAccount` + pluggable `AuditPlugin`s) so every governance action is accountable.
- **Law** (`law/`) — four standard layers:
  - *Communication protocol standard*
  - *Global economic unified standard* — currency, peg, proof-of-reserve, redemption
  - *Identity attestation standard* — soul-hash bound identity
  - *Physics baseline standard* — gravity / time / scale constants
- **Bridge** (`compatibility_bridge.py`) — the only "customs" through which legacy worlds join Nohn territory:
  - `translate_intent()` — semantic wash: maps vendor-private instructions to the Nohn standard vocabulary, stripping hidden interpretation rights.
  - `check_physics_constants()` — rejects worlds whose physics constants diverge from `NOHN_LAW_AXIOMS`.
  - `verify_soul_hash()` — verifies identity against the soul-hash anchor.

The runtime (`virtual_world.py`) wires these together with an `EconomySystem`, `TaskGenerator`, and `NohnAgent`.

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

## ✦ Project Structure

```
SPL-Virtual-world-base/
├── constitution.py              # world axioms + 6-layer class system (see above)
├── compatibility_bridge.py      # legacy-world "customs": semantic wash + physics/soul checks
├── virtual_world.py             # runtime: world, agents, economy, tasks, visualization
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
