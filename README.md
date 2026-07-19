<p align="center">
  <img src="https://sourceforge.net/p/spl-virtual-world-base/git/ci/main/tree/assets/banner.png?format=raw" alt="SPL-虚拟世界基地横幅" style="width:100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/metaverse--D4AF37?style=flat-square" alt="metaverse">  <img src="https://img.shields.io/badge/infrastructure--D4AF37?style=flat-square" alt="infrastructure">  <img src="https://img.shields.io/badge/constitution--D4AF37?style=flat-square" alt="constitution">
</p>

<blockquote align="center">
  <em>Virtual World & Metaverse Infrastructure Foundation</em>
</blockquote>

<div style="max-width:880px;margin:0 auto;padding:0 16px">

## ✦ About

<p style="font-size:15px;line-height:1.8;color:#2C2C2C">SPL-VIRTUAL-WORLD-BASE is the infrastructure framework for virtual worlds and metaverses, built on a three-layer architecture — Constitution, Law, and Bridge — providing a governable, interoperable, and evolvable runtime foundation for virtual spaces. It enables stable bridging and collaboration of assets, rules, and agents across different worlds.</p>

<p align="center">
  <img src="https://sourceforge.net/p/spl-virtual-world-base/git/ci/main/tree/assets/overview.png?format=raw" alt="SPL-虚拟世界基础概述" style="width:100%">
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

## ✦ Project Structure

```
SPL-Virtual-world-base/
├── constitution.py              # world axioms + embedded cognitive-audit engine
├── compatibility_bridge.py      # legacy-world "customs": semantic wash + physics/soul checks
├── virtual_world.py             # runtime: economy, tasks, agents
├── law/                         # Communication / Economic / Identity / Physics standards
├── assets/                      # banner.svg/png, overview.svg/png
└── LICENSE
```

## ✦ License & Authorization

This repository is **not open-source**. Dual-track model: free for individual non-commercial research; paid commercial authorization required for government / enterprise. See [LICENSE](./LICENSE).

<p align="center">
  <a href="https://github.com/NOHN-AI">NOHN-AI</a>
  &nbsp;·&nbsp;
  <a href="https://www.nohnlins.com/">nohnlins.com</a>
  &nbsp;·&nbsp;
  <a href="mailto:ai@nohnlins.com">ai@nohnlins.com</a>
</p>
<p align="center"><sub>NOHN AI · SPL-VIRTUAL-WORLD-BASE</sub></p>
