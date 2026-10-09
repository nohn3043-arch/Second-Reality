# Independent Verification Guide

[简体中文](VERIFICATION-zh.md) | English

**Who this is for** — enterprise engineering, security, and audit teams evaluating this system on their own deployment.

**One principle** — the smoke scripts under `tools/` are our engineering tools; treat them as templates at most, never as evidence. This guide maps the repository's public claims to observable behaviors and interfaces, so your team can design and run its own acceptance and security tests.

---

## 1. Claim inventory — start here

Every row is a published claim, where it is stated, and how you can observe it. The suggested designs are starting points; replace them with your own threat model.

### Identity, credentials, sessions

| Claim | Source | Observable | Suggested test |
|---|---|---|---|
| Private keys never leave the device; the server holds zero plaintext credentials | README Quick Start; `law/Identity attestation standard` | server-side storage contents | enroll with your own keypair; dump the storage of your deployment; assert only public keys / fingerprints are present |
| `soul_hash` is SHA-256 (64 hex), derived from the public key; the platform cannot reset an identity | `law/Identity attestation standard` | soul_hash format; re-registration behavior | recompute the hash from your own keypair; after key loss, attempt re-registration → must be refused (identity freeze) |
| Session tokens are device-bound; revocation takes effect immediately; devices are isolated | README Demo & Verification | token verification result | issue tokens to two devices; revoke one; assert its token is dead and the other still valid |
| Guardian recovery is fail-closed | README; smoke scripts | finalize result | initiate recovery; finalize with zero votes → must not succeed |

### World & reality baseline (R1–R5)

| Claim | Source | Observable | Suggested test |
|---|---|---|---|
| R1 genesis lock | `law/Physics baseline standard` V3.0 | world constants | attempt to overwrite constants after genesis → locked |
| R2 global consistency; undeclared ⇒ False (fail-closed) | as above | validator verdict | construct a world with an undeclared dimension → verdict must be False |
| R3 causal closure — every state change has a causal predecessor | as above | audit chain | inject a change with no predecessor → rejected |
| R4 published-as-executed — the published constant set equals the ledger-anchored set | as above | commitment hash | recompute the commitment from public state yourself and compare; a mismatch must be judged False |
| R5 reaction-table completeness | as above | validator verdict | undeclared reaction → False |
| Amendment only via fork — the parent world is never rewritten | README Demo & Verification | fork registry; parent hash | request an amendment; assert only a fork is produced and the parent state/hash is unchanged |

### Communication & economy

| Claim | Source | Observable | Suggested test |
|---|---|---|---|
| Unmappable instructions are handled per the standard (downgraded), never dropped | `law/Communication protocol standard` | handling response | send a private instruction that cannot be mapped → behavior must match the standard's rule |
| Cross-world messages use the standard envelope | `law/Communication protocol standard` | wire format | inspect envelope fields against the standard's vocabulary |
| Redemption channel always on; reserve proof by multi-sig; ≥ 3 independent oracles, median/weighted | `law/Global economic unified standard` | economy behavior | scenario tests inside your own world instance (policy-heavy — design per threat model) |

If a claim you care about cannot be observed from outside, record that as a finding — an untestable claim cannot be verified, only taken on faith.

## 2. Where to attach your tests

- **Programmatic** — `system.runtime.World` and `system.api.WorldAPI.dispatch`. The authoritative route set is `system/api.py` (see also README "API Service").
- **Service level** — `python -m system.api` with **your** deployment profile (`STORAGE=sqlite/postgres/redis` per README). Our scripts use the in-memory backend; testing your target backend is the point of self-testing.
- **Evidence level** — `world.audit_summary()` (24-dimension audit), and the hash-anchor format you can inspect via `expert_report.py` (see `reports/`). Produce your own anchors from your own run — never reuse ours.

## 3. Test techniques worth trying

- **Forgery & tampering** — forged genesis proofs, mutated signature payloads, tampered roaming certificates → must be rejected with no state change.
- **Replay** — nonce reuse, revoked-token reuse, stale resume tokens, stale roaming certificates.
- **Format & boundary** — `soul_hash` format checks; acceptance of externally derived soul_hashes (cross-world).
- **Fail-closed probes** — undeclared physics dimension, zero-vote recovery, missing declarations → must be False or refused, never default-allow.
- **Fault injection** — for the cluster claims (heartbeat, epoch, AOI replication, migration, partition merge), inject delay/drop/partition at the transport and observe degradation and recovery semantics.
- **Determinism & reproducibility** — same stimulus, same audit verdicts and same hashes; a third party must be able to recompute them.

## 4. Our scripts — optional templates

| Script | Claim examples it exercises |
|---|---|
| `smoke_test.py` | identity/session paths: genesis → soul hash, challenge-response, session issuance, per-device revocation, auth audit |
| `tools/wiring_smoke.py` | account abstraction, key rotation, identity root (Shamir), soul roaming |
| `tools/reality_smoke.py` | R1–R5, onboarding gate, referendum fail-closed, fork-only amendment |
| `tools/edge_smoke.py` | device enrollment, challenge login, AOI viewport deltas, nearest-DC routing, relocation, revocation |
| `tools/cluster_smoke.py` | 3-node cluster: heartbeat, epoch, AOI, HLC, migration handshake, partition merge, unknown-op handling |

Reimplement the parts you need as your own tests, or ignore them entirely. The claim inventory in §1 is the durable part.

## 5. Your report

| Field | Content |
|---|---|
| Claim tested | with the source reference (§1 row) |
| Stimulus | exact request / sequence |
| Environment | deployment profile (backend, topology), commit hash |
| Expected / observed | before/after states, tokens, hashes |
| Verdict & evidence | PASS/FAIL, raw logs, hashes |

Pin the commit you tested and attach raw outputs. Reproducible evidence is the only kind that ends debates.

## 6. Coverage boundary

- The repository's own checks are smoke-level; there is no CI, and no third-party verification has been performed yet.
- Our scripts run single-machine and in-memory; treat them as examples, not coverage.
- The four documents under `law/` contain policy-level claims beyond software behavior; test the software-testable subset, and route the rest to governance-level review.
- The pygame society demo is a visualization — not covered here.
- Version pinning: capture the commit hash (or released archive) you tested.

---

License: see `LICENSE`.
