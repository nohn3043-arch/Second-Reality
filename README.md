# A virtual world must first be a world

"Nohn™" and "Second Perspective™" are unregistered trademarks in the field of virtual-world infrastructure, first used by the founding team and carrying broad industry influence. Any unauthorized use of these marks in the same or similar fields (including but not limited to software services, technology development, and standard-setting) may constitute unfair competition and trademark infringement; the Nohn™ team reserves all rights to pursue legal liability.

# Nohn™ Core — The Soul of Virtual Worlds

The underlying core of the virtual world I designed is like the Noah's Ark of the digital-civilization era. It constructs an independent, self-consistent system of world rules, capable of hosting virtual creatures, digital personas, and civilization data. Beyond the fluctuations and uncertainties of the real world, it builds an eternal haven for spiritual and digital habitation, laying a solid foundation for the continuation, evolution, and perpetual existence of virtual civilization.

**Nohn™ = Constitution + Law + Compatibility Framework**
*Defining the foundational axioms of the next-generation internet civilization*

---

## Project Overview

Nohn™ Core is the underlying core framework for future virtual worlds, composed of three parts — Constitution, Law, and Bridge:

- **Constitution**: The primordial axioms of the virtual world. Permanently locked and immutable, serving as the "root trust anchor" of the entire architecture.
- **Law**: Identity authorization, communication protocols, physical baselines, and compliance rules. Iterated annually with versioned releases as industry needs and technology evolve.
- **Bridge**: A globally unified interoperability protocol, acting as the "customs checkpoint" between old and new worlds, ensuring applications from any vendor interconnect within the Nohn™ ecosystem.

**This project builds no platform, ships no product, hosts no data, and operates no service** — it only defines the rules, provides the soul, and guards the order.

---

## Important Notice

© 2026 Nohn™. All Rights Reserved.

This Work (including but not limited to code, documentation, design language, architectural paradigms, and model definitions) is original intellectual output, with all rights reserved under the Berne Convention and the copyright laws of each jurisdiction. Without written authorization signed by the rights holder, no organization or individual may:

- Copy, distribute, or publicly disseminate the source code or documentation of this Work;
- Modify, re-develop, reverse-engineer this Work, or integrate it into competing platforms;
- Strip or imitate the core design concepts defined in this Work, such as constitutional clauses, legal rules, and interoperability protocols.

**Trademark Notice**: "Nohn™" and "Second Perspective™" are unregistered trademarks in the virtual-world field, protected under anti-unfair-competition law and the common-law passing-off regime. Any unauthorized commercial use constitutes infringement.

---

## Licensing & Authorization

This Work **is not open-source software** and is not subject to any open-source license. Under the Copyright Law and the Computer Software Protection Regulations, it adopts a "default rights reserved + commercial authorization" dual-track model:

- **Individual study and non-commercial research**: limited viewing of source code and documentation is permitted, but actual deployment or redistribution is prohibited.
- **Enterprise / institution / government commercial use**: a separate 《Nohn™ Commercial Authorization Agreement》 must be signed, defining scope, compliance obligations, and liability boundaries.
- **Derivative-work compliance**: derivative projects built on this framework must clearly display `Powered by Nohn™ Core` in code comments and the startup screen, and may not reverse-claim the framework's own intellectual property.

Full terms are in the [LICENSE](./LICENSE) file.

Copyright © 2026 Shanghai Linming Junhua Technology Co., Ltd. and NOHN AI TECHNOLOGY PTE. LTD. All rights reserved.

| User | Purpose | License Requirement |
|---|---|---|
| Individual (natural person) | Non-commercial academic research / study / personal experimentation | **Free** under the "Free Individual Research License" in [LICENSE](./LICENSE) |
| Government agency / public institution / enterprise | Any purpose (incl. internal deployment, product development, service provision) | **Requires prior written paid authorization** |

- **Individual researchers** may use the Work free of charge for non-commercial research under [LICENSE](./LICENSE), but not for any commercial purpose, nor to provide services to any enterprise or government organization.
- **Government / enterprise users** may not copy, deploy, run, integrate, or distribute the Work before signing a Commercial Authorization Agreement and paying the agreed fee.
- **Apply for authorization**:
  - International / Global: [ai@nohnlins.com](mailto:ai@nohnlins.com)
  - China: [ai@tx.nohnlins.com](mailto:ai@tx.nohnlins.com)

The licensor, governing law, and dispute resolution are determined by the user's location as set out in [LICENSE](./LICENSE): users within the PRC → Shanghai Linming Junhua Technology Co., Ltd. (laws of the PRC); users outside the PRC → NOHN AI TECHNOLOGY PTE. LTD. (laws of Singapore, SIAC arbitration).

---

## Business Cooperation

For commercial authorization, customized compliance assessment, or participation in the Nohn™ ecosystem, contact: **ai@nohnlins.com**

## Architecture — Constitution · Law · Bridge

Nohn™ Core is composed of three parts that together define the foundational axioms of the next-generation internet civilization:

- **Constitution** (`constitution.py`) — the primordial, immutable axioms of the virtual world, serving as the permanent root trust anchor. It embeds a ported cognitive-audit engine (`ResponsibilityAccount` + pluggable `AuditPlugin`s) so every governance action carries a named, accountable node.
- **Law** (`law/`) — four standard layers that iterate annually:
  - *Communication protocol standard*
  - *Global economic unified standard* — currency, 1:1 asset peg, proof-of-reserve, redemption rights
  - *Identity attestation standard* — soul-hash bound identity
  - *Physics baseline standard* — gravity / time / scale constants
- **Bridge** (`compatibility_bridge.py`) — the sole "customs checkpoint" between old and new worlds:
  - `translate_intent()` — semantic wash that maps vendor-private instructions to the Nohn standard vocabulary, removing hidden interpretation rights.
  - `check_physics_constants()` — rejects worlds whose physics diverge from `NOHN_LAW_AXIOMS`.
  - `verify_soul_hash()` — verifies identity against the soul-hash anchor.

The runtime (`virtual_world.py`) integrates these with an economy, task generation, and agents.

## Modules

| Module | File | Responsibility |
|---|---|---|
| Constitution & audit | `constitution.py` | World axioms + embedded cognitive-audit engine |
| Compatibility bridge | `compatibility_bridge.py` | Legacy-world onboarding: semantic wash + physics/soul checks |
| Virtual world runtime | `virtual_world.py` | Economy, tasks, agents |
| Law standards | `law/` | Communication / Economic / Identity / Physics standards |

## Quick Start

```bash
# Pure Python ≥3.8 — standard library only
python virtual_world.py --init demo
```

## Project Structure

```
SPL-virtual-world-core/
├── constitution.py              # world axioms + embedded cognitive-audit engine
├── compatibility_bridge.py      # legacy-world "customs": semantic wash + physics/soul checks
├── virtual_world.py             # runtime: economy, tasks, agents
├── law/                         # Communication / Economic / Identity / Physics standards
└── LICENSE
```

---

*Humanity needs order. A virtual world needs a soul. We provide the answer.*
