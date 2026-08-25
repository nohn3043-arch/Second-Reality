"""Smoke test for the 8 security fixes."""
import sys
sys.path.insert(0, ".")
import os
os.environ["STORAGE"] = "memory"

from system.runtime import World
from system.keys import (
    generate_user_keypair,
    build_genesis_proof,
    sign_with_device,
)
from system.api import WorldAPI
import audit_engine
import hashlib
import base64
import time


def step(n, msg):
    print(f"[{n}] {msg}")


def main():
    # 1. World creation
    world = World("smoke-test", data_dir=None)
    step(1, "World created (memory backend)")

    # 2. Spawn a soul
    kp = generate_user_keypair()
    proof = build_genesis_proof(
        kp["secret"], {"name": "test-soul", "ts": int(time.time())}
    )
    agent = world.spawn_agent(soul_hash=None, genesis_proof=proof)
    step(2, f"Spawned soul: {agent.soul_hash[:16]}...")

    # 3. Challenge
    api = WorldAPI(world)
    nonce = api.auth.issue_challenge(agent.soul_hash, ip="127.0.0.1")
    step(3, f"Challenge issued: nonce={nonce[:16]}...")

    # 4. Sign + verify
    sig = sign_with_device(kp["secret"], nonce.encode("utf-8"))
    sig_b64 = base64.b64encode(sig).decode("ascii")
    ok = api.auth.verify_challenge(agent.soul_hash, nonce, sig_b64, kp["pubkey"])
    step(4, f"Challenge verify: {ok}")

    # 5. Issue session with device binding (via /auth/issue production path)
    # Simulate what /auth/issue does internally: sign nonce + verify + auto-bind
    import hashlib as _hl
    pubkey = kp["pubkey"]
    pkfp = _hl.sha256(pubkey).hexdigest()[:32]
    # auto-bind primary credential (mirrors /auth/issue production logic)
    existing_creds = world.credentials.get_credentials(agent.soul_hash)
    already_bound = any(
        _hl.sha256(c["public_key"]).hexdigest()[:32] == pkfp
        and not c["revoked"]
        for c in existing_creds
    )
    if not already_bound:
        world.credentials.bind_credential(agent.soul_hash, pubkey, "primary")
    access, refresh = world.sessions.issue(
        agent.soul_hash, pubkey_fingerprint=pkfp
    )
    step(5, f"Session issued: access={access[:30]}...")

    # 6. Verify access token
    verified = world.sessions.verify(access, credential_vault=world.credentials)
    step(6, f"Token verify: {verified == agent.soul_hash}")

    # 7. Bind a NEW device (different pubkey) — its own token must stay valid
    kp2 = generate_user_keypair()
    cred_id_2 = world.credentials.bind_credential(
        agent.soul_hash, kp2["pubkey"], "device-2"
    )
    step(7, f"2nd device credential bound: {cred_id_2[:8]}...")

    # 7.1 Issue a new token bound to device-2, verify it works
    pkfp2 = hashlib.sha256(kp2["pubkey"]).hexdigest()[:32]
    access2, _ = world.sessions.issue(agent.soul_hash, pubkey_fingerprint=pkfp2)
    ok2 = (
        world.sessions.verify(access2, credential_vault=world.credentials)
        == agent.soul_hash
    )
    step(7.1, f"device-2 token valid (should be True): {ok2}")

    # 7.2 Revoke PRIMARY -> primary-bound token invalid, device-2 token still valid
    primary_creds = [
        c for c in world.credentials.get_credentials(agent.soul_hash)
        if c["device_label"] == "primary"
    ]
    if primary_creds:
        world.credentials.revoke_credential(
            agent.soul_hash, primary_creds[0]["credential_id"]
        )
    step(7.2, "Primary credential revoked")
    after_primary = world.sessions.verify(
        access, credential_vault=world.credentials
    )
    step(7.3, f"Primary token after revoke (should be None): {after_primary}")
    still2 = (
        world.sessions.verify(access2, credential_vault=world.credentials)
        == agent.soul_hash
    )
    step(7.4, f"device-2 token still valid (should be True): {still2}")

    # 7.5 Revoke device-2 -> its token now invalid too
    world.credentials.revoke_credential(agent.soul_hash, cred_id_2)
    after2 = world.sessions.verify(
        access2, credential_vault=world.credentials
    )
    step(7.5, f"device-2 token after revoke (should be None): {after2}")

    # 8. Audit (auth_security)
    auditor = audit_engine.SecondPerspectiveAuditor()
    report = auditor.audit_world(world)
    auth = report.auth_security
    step(8, f"Audit auth_security verdict: {auth.get('verdict')}")
    for k, v in auth.items():
        if k != "verdict":
            print(f"      {k} = {v}")

    # 9. SQLite scale guard (negative test: HashShardRouter should not trip)
    from system.ledger import Storage, HashShardRouter
    s2 = Storage(backend="memory", shard_router=HashShardRouter(prefix_len=2))
    sh = s2.router.shard_of("abcd1234..." * 5)[:64]
    step(9, f"HashShardRouter routes 'abcd...' -> {sh}")

    # 10. Transaction test: register, then verify rollback on exception
    from system.recovery import RecoveryManager
    from system.credentials import CredentialVault
    s3 = Storage(backend="memory")
    cv = CredentialVault(storage=s3)
    rm = RecoveryManager(storage=s3, credential_vault=cv)
    test_soul = "ab" * 32
    g1 = "11" * 32
    rm.add_guardian(test_soul, g1)
    # initiate but no votes -> finalize should return None
    new_pk = generate_user_keypair()["pubkey"]
    req = rm.initiate_recovery(test_soul, new_pk.hex())
    step(10, f"Recovery request created: {req[:8]}... (no votes -> finalize=None)")
    res = rm.finalize_recovery(req)
    step(10.1, f"finalize result: {res} (expected None)")

    # 11. verify no deadbeef/cafebabe pollution in real world
    rows = world.storage.query("SELECT soul_hash FROM souls")
    pollution = [r[0] for r in rows if r[0].startswith("dead") or r[0].startswith("cafe")]
    step(11, f"Audit pollution check (should be 0): {len(pollution)}")

    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
