# tools/cluster_smoke.py - 跨数据中心接线验收（地平线二）
# ============================================================
# 用途：证明跨节点链路确实有流量，而不是"零件造好没装车"。
#
# 判据很直接——接线之前下列指标恒为零 / 恒为假：
#   心跳活性表、远端 epoch、远端 AOI 实体、HLC 入站合流、
#   跨域迁移握手、分区降级与恢复、未知 op 降级。
#
# 用法：
#   python tools/cluster_smoke.py
# 退出码 0 = 全部通过，1 = 存在未通过项。
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
# dc_b 持有 shard_1_0_0（包围盒 1..2 / 0..1 / 0..1），dc_c 持有 shard_2_0_0
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
    """向内核要一个空闲端口，供节点预先声明静态端点。"""
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

    # ---- 0. 单机形态回归：cluster=None 必须完全不接线 ----
    print("[0] 单机形态回归（cluster=None）")
    solo = World("solo-world", data_dir=None)
    check("未装配集群", solo.cluster is None and solo.heartbeat_loop is None)
    check("未启动监听线程", solo.transport is not None and solo.transport._thread is None)
    check("未注册任何端点", len(solo.consensus.endpoints) == 0)
    solo.tick()
    check("单机 tick 正常推进", solo.temporal_substrate.global_clock == 1)
    solo.close()

    # ---- 1. 起三节点集群 ----
    print("[1] 启动三节点集群")
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

    # ---- 2. 心跳活性 ----
    print("[2] 心跳活性探测")
    for name, w in worlds.items():
        active = w.consensus.active_nodes(ttl=5.0)
        check("%s 探测到活跃对端" % name, len(active) >= 2, "active=%s" % active)

    # ---- 3. Epoch 跨 DC 广播 ----
    print("[3] Epoch 跨 DC 广播")
    for name, w in worlds.items():
        w.tick()
    time.sleep(2.0)
    for _ in range(2):
        for name, w in worlds.items():
            w.tick()
        time.sleep(0.6)
    for name, w in worlds.items():
        remote = w.interdc_consensus.epoch_manager._remote_epochs
        check("%s 收到远端 epoch" % name, len(remote) >= 2, "remote_epochs=%s" % remote)

    # ---- 4. AOI 增量复制 ----
    print("[4] AOI 增量复制")
    for _ in range(3):
        for name, w in worlds.items():
            w.tick()
        time.sleep(0.5)
    for name, w in worlds.items():
        remotes = w.aoi_tracker._remote_entities
        check(
            "%s 登记了远端实体" % name,
            len(remotes) >= 1,
            "remote_entities=%d" % len(remotes),
        )

    # ---- 5. HLC 因果合流 ----
    print("[5] HLC 跨节点合流")
    for name, w in worlds.items():
        # 用入站合流计数判定：hlc.state()["ll"] 会被随后的 send() 清零，不能作为证据
        check(
            "%s HLC 完成入站合流" % name,
            w._hlc_merges > 0,
            "merges=%d state=%s" % (w._hlc_merges, w.hlc.state()),
        )

    # ---- 6. 跨域迁移握手 ----
    print("[6] 跨数据中心迁移握手")
    a = worlds["node_a"]
    soul = sorted(a.npcs)[0]
    moved = a.move_agent(soul, [1.5, 0.5, 0.5])  # shard_1_0_0 → 归属 dc_b
    check("移动指令被接受", moved)
    time.sleep(0.6)
    b = worlds["node_b"]
    check(
        "node_b 收到 handover 请求",
        len(b._received_handovers) >= 1,
        "received=%s" % b._received_handovers,
    )
    pending = a.shard_manager.handover.active_handovers()
    check("node_a 无悬挂迁移", len(pending) == 0, "pending=%s" % pending)

    # ---- 7. 分区降级 → 恢复 → 合并 ----
    print("[7] 分区降级 → 恢复 → 状态合并")
    worlds["node_b"].transport.stop()
    worlds["node_c"].transport.stop()
    # 需等足 max_missed × 心跳周期：连接失败判定本身也要花到超时才返回
    time.sleep(2.5)
    for _ in range(4):
        a.tick()
        time.sleep(0.3)
    check(
        "node_a 判定进入分区",
        a.partition_guard.in_partition,
        "miss_counts=%s" % a.partition_guard.detector._heartbeat_count,
    )

    worlds["node_b"].transport.start()
    worlds["node_c"].transport.start()
    time.sleep(2.5)
    for _ in range(4):
        a.tick()
        time.sleep(0.3)
    check("node_a 判定分区恢复", not a.partition_guard.in_partition)
    merged = a.merge_partition_state({"ghost-soul": [0.0, 0.0, 0.0]})
    check(
        "分区合并可执行",
        isinstance(merged, dict) and "ghost-soul" in merged,
        "merged_keys=%d" % len(merged),
    )

    # ---- 8. 入站白名单 ----
    print("[8] 未知 op 降级")
    resp = a._on_message("node_b", {"op": "drop_everything"})
    check("未知 op 被拒绝", resp.get("_error") == "unknown_op", "resp=%s" % resp)

    for w in worlds.values():
        w.close()

    print("")
    if _FAILURES:
        print("FAIL: %d 项未通过" % len(_FAILURES))
        for f in _FAILURES:
            print("  - " + f)
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
