# tools/cluster_smoke.py - Cross-datacentre wiring acceptance (Horizon II)
# ============================================================
# Purpose: prove the cross-node links actually carry traffic, rather than "parts built but never fitted".
#
# The criteria are direct: before wiring, the following stay permanently zero / false:
#   heartbeat liveness, remote epoch, remote AOI entities, HLC inbound merge,
#   cross-domain migration handshake, partition degradation and recovery, unknown-op downgrade.
#
# Usage:
#   python tools/cluster_smoke.py
# Exit code 0 = all passed, 1 = some checks failed.
# ============================================================

import os
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("STORAGE", "memory")

from system.runtime import World
from system.cluster import ClusterConfig
from system.keys import generate_user_keypair, build_genesis_proof

NODES = {
    "node_a": "dc_a",
    "node_b": "dc_b",
    "node_c": "dc_c",
}
# dc_b holds shard_1_0_0 (bounds 1..2 / 0..1 / 0..1), dc_c holds shard_2_0_0
DC_SHARDS = {"dc_b": ["shard_1_0_0"], "dc_c": ["shard_2_0_0"]}

HEARTBEAT_INTERVAL = 0.3
AOI_INTERVAL = 0.3
EPOCH_INTERVAL = 0.5

_FAILURES = []


def check(label, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    line = "  [%s] %s" % (tag, label)
    if detail:
        line += " — " + str(detail)
    print(line)
    if not cond:
        _FAILURES.append(label)


def free_port():
    """Ask the kernel for an idle port so a node can pre-declare a static endpoint."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def config_for(name, ports):
    return ClusterConfig(
        local_dc=NODES[name],
        node_endpoint="127.0.0.1:%d" % ports[name],
        peers={n: "127.0.0.1:%d" % ports[n] for n in NODES if n != name},
        dc_peers={dc: [n] for n, dc in NODES.items()},
        dc_shards=DC_SHARDS,
        heartbeat_interval_sec=HEARTBEAT_INTERVAL,
        aoi_interval_sec=AOI_INTERVAL,
    )


def spawn(world, tag):
    kp = generate_user_keypair()
    proof = build_genesis_proof(kp["secret"], {"name": tag, "ts": int(time.time())})
    return world.spawn_agent(soul_hash=None, genesis_proof=proof)


def main():
    print("=== cluster smoke: 3 nodes / 3 DCs ===")
    ports = {n: free_port() for n in NODES}

# ---- 0. Single-node regression: cluster=None must wire nothing ----
    print("[0] Single-node regression (cluster=None)")
    solo = World("solo-world", data_dir=None)
    check("no cluster assembled", solo.cluster is None and solo.heartbeat_loop is None)
    check("no listener thread started", solo.transport is not None and solo.transport._thread is None)
    check("no endpoints registered", len(solo.consensus.endpoints) == 0)
    solo.tick()
    check("single-node tick advances normally", solo.temporal_substrate.global_clock == 1)
    solo.close()

# ---- 1. Start a three-node cluster ----
    print("[1] Starting a three-node cluster")
    worlds = {}
    for name in NODES:
        w = World(name, data_dir=None, cluster=config_for(name, ports))
        w.interdc_consensus.epoch_manager.epoch_interval = EPOCH_INTERVAL
        w.partition_guard.detector.check_interval = 0.2
        w.partition_guard.detector.max_missed = 2
        spawn(w, name)
        worlds[name] = w
        print("    %s @ 127.0.0.1:%d  dc=%s" % (name, ports[name], NODES[name]))
    time.sleep(1.0)

# ---- 2. Heartbeat liveness ----
    print("[2] Heartbeat liveness probe")
    for name, w in worlds.items():
        active = w.consensus.active_nodes(ttl=5.0)
        check("%s sees live peers" % name, len(active) >= 2, "active=%s" % active)

# ---- 3. Epoch broadcast across DCs ----
    print("[3] Epoch broadcast across DCs")
    for name, w in worlds.items():
        w.tick()
    time.sleep(2.0)
    for _ in range(2):
        for name, w in worlds.items():
            w.tick()
        time.sleep(0.6)
    for name, w in worlds.items():
        remote = w.interdc_consensus.epoch_manager._remote_epochs
        check("%s received remote epochs" % name, len(remote) >= 2, "remote_epochs=%s" % remote)

# ---- 4. AOI delta replication ----
    print("[4] AOI delta replication")
    for _ in range(3):
        for name, w in worlds.items():
            w.tick()
        time.sleep(0.5)
    for name, w in worlds.items():
        remotes = w.aoi_tracker._remote_entities
        check(
            "%s registered remote entities" % name,
            len(remotes) >= 1,
            "remote_entities=%d" % len(remotes),
        )

# ---- 5. HLC causal merge ----
    print("[5] HLC cross-node merge")
    for name, w in worlds.items():
#     judged by the inbound-merge count: hlc.state()["ll"] is cleared by the next send() and cannot serve as evidence
        check(
            "%s completed inbound HLC merge" % name,
            w._hlc_merges > 0,
            "merges=%d state=%s" % (w._hlc_merges, w.hlc.state()),
        )

# ---- 6. Cross-domain migration handshake ----
    print("[6] Cross-datacentre migration handshake")
    a = worlds["node_a"]
    soul = sorted(a.npcs)[0]
    moved = a.move_agent(soul, [1.5, 0.5, 0.5])  # shard_1_0_0 -> owned by dc_b
    check("move command accepted", moved)
    time.sleep(0.6)
    b = worlds["node_b"]
    check(
        "node_b received the handover request",
        len(b._received_handovers) >= 1,
        "received=%s" % b._received_handovers,
    )
    pending = a.shard_manager.handover.active_handovers()
    check("node_a has no pending migration", len(pending) == 0, "pending=%s" % pending)

# ---- 7. Partition degradation -> recovery -> merge ----
    print("[7] Partition degradation -> recovery -> state merge")
    worlds["node_b"].transport.stop()
    worlds["node_c"].transport.stop()
# must wait max_missed x heartbeat period: the connection-failure verdict itself returns only on timeout
    time.sleep(2.5)
    for _ in range(4):
        a.tick()
        time.sleep(0.3)
    check(
        "node_a declared itself in partition",
        a.partition_guard.in_partition,
        "miss_counts=%s" % a.partition_guard.detector._heartbeat_count,
    )

    worlds["node_b"].transport.start()
    worlds["node_c"].transport.start()
    time.sleep(2.5)
    for _ in range(4):
        a.tick()
        time.sleep(0.3)
    check("node_a declares partition recovered", not a.partition_guard.in_partition)
    merged = a.merge_partition_state({"ghost-soul": [0.0, 0.0, 0.0]})
    check(
        "partition merge is executable",
        isinstance(merged, dict) and "ghost-soul" in merged,
        "merged_keys=%d" % len(merged),
    )

# ---- 8. Inbound allow-list ----
    print("[8] Unknown-op downgrade")
    resp = a._on_message("node_b", {"op": "drop_everything"})
    check("unknown op rejected", resp.get("_error") == "unknown_op", "resp=%s" % resp)

    for w in worlds.values():
        w.close()

    print("")
    if _FAILURES:
        print("FAIL: %d checks failed" % len(_FAILURES))
        for f in _FAILURES:
            print("  - " + f)
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
