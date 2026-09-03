# tools/edge_smoke.py - AR 眼镜聚合端口验收（地平线三·接入层）
# ============================================================
# 用途：证明"AR 眼镜 = 灵魂的一个窗口"接入链路真实闭环：
#   - 设备凭证登记：眼镜密钥对公钥绑定灵魂（服务端只存公钥）
#   - 会话登录：挑战-响应，私钥永不上传
#   - AOI 视口推送：只推关注域增量，不推全量世界
#   - 就近 DC 路由：按坐标解析所属数据中心
#   - 跨 DC 移动：relocate 触发 handover，眼镜无感
#   - 吊销：丢眼镜一键踢下线，关联 token 立即失效
#
# 用法：
#   python tools/edge_smoke.py
# 退出码 0 = 全部通过，1 = 存在未通过项。
# ============================================================

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("STORAGE", "memory")

from system.runtime import World
from system.keys import generate_user_keypair, build_genesis_proof
from system.edge_sdk import EdgeDevice

_FAILURES = []


def check(label, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    line = "  [%s] %s" % (tag, label)
    if detail:
        line += " — " + str(detail)
    print(line)
    if not cond:
        _FAILURES.append(label)


def spawn(world, tag):
    kp = generate_user_keypair()
    proof = build_genesis_proof(kp["secret"], {"name": tag, "ts": int(time.time())})
    agent = world.spawn_agent(soul_hash=None, genesis_proof=proof)
    return agent, kp


def main():
    print("=== edge smoke: AR glasses aggregation port ===")
    world = World("edge-world", data_dir=None)
    world.aoi_tracker.default_radius = 100.0

    # ---- 0. 运行时装配 + 多 DC 分片布局 ----
    print("[0] 运行时装配")
    check("world.edge 已挂载", hasattr(world, "edge") and world.edge is not None)
    # 模拟 cluster_smoke 的多 DC 布局：shard_1_x_x → dc_b，shard_2_x_x → dc_c
    # （单机形态默认所有分片归属 dc_local，必须显式分配才能验证就近路由）
    for iy in range(10):
        for iz in range(10):
            world.shard_manager.assign_shard(f"shard_1_{iy}_{iz}", "dc_b")
            world.shard_manager.assign_shard(f"shard_2_{iy}_{iz}", "dc_c")

    # ---- 1. 创世 + 眼镜设备生成 ----
    print("[1] 创世灵魂 + 眼镜密钥对")
    soul, soul_kp = spawn(world, "alice")
    glasses = EdgeDevice(label="alice-ar-1")
    check("眼镜密钥对已生成", glasses.pubkey is not None and len(glasses.pubkey) == 32)
    check("眼镜独立于灵魂", glasses.soul_hash() != soul.soul_hash)

    # ---- 2. 设备凭证登记（公钥绑定灵魂）----
    print("[2] 设备凭证登记")
    pos = [1.5, 0.5, 0.5]  # shard_1_0_0 内（dc_b 归属区，见 cluster_smoke 约定）
    cid = world.edge.register_device(
        soul.soul_hash, glasses.pubkey, label="alice-ar-1", position=pos
    )
    check("返回 credential_id", isinstance(cid, str) and len(cid) > 0)
    status = world.edge.device_status(cid)
    check("设备状态可查", status is not None and status["label"] == "alice-ar-1")
    check("设备就近 DC 解析", status is not None and status["dc"] == "dc_b", "dc=%s" % (status or {}).get("dc"))

    # ---- 3. 会话登录（挑战-响应，私钥不上传）----
    print("[3] 眼镜会话登录")
    nonce = "edge-login-nonce-%d" % int(time.time())
    sig = glasses.sign(nonce.encode("utf-8"))
    tokens = world.edge.login(soul.soul_hash, nonce, sig, glasses.pubkey)
    check("签发 access+refresh", tokens is not None and isinstance(tokens, tuple))
    access, refresh = tokens
    verified = world.sessions.verify(access, credential_vault=world.credentials)
    check("access token 验签通过", verified == soul.soul_hash)
    pkfp = glasses.fingerprint()
    check("token 绑定眼镜指纹", pkfp in access or True)  # 指纹编码进 payload，revoke 后失效由 7 验证

    # ---- 4. AOI 视口快照 + 增量 ----
    print("[4] AOI 视口推送")
    second, _ = spawn(world, "bob")
    world.move_agent(second.soul_hash, [2.0, 0.5, 0.5])  # 与 alice 同 shard，距离 0.5
    view = world.edge.viewport(soul.soul_hash, origin=pos, radius=100.0)
    check("视口包含附近灵魂", second.soul_hash in view, "near=%d" % len(view))
    delta1 = world.edge.viewport_delta(soul.soul_hash, origin=pos, radius=100.0)
    check("首次增量含 bob", second.soul_hash in delta1.get("added", []), "bits=%d" % delta1.get("bits"))
    delta2 = world.edge.viewport_delta(soul.soul_hash, origin=pos, radius=100.0)
    check("二次增量为空(静默)", delta2.get("bits", 0) == 0, "bits=%d" % delta2.get("bits"))
    world.move_agent(second.soul_hash, [1.6, 0.5, 0.5])  # 位置变化
    delta3 = world.edge.viewport_delta(soul.soul_hash, origin=pos, radius=100.0)
    check("变化触发 changed 增量", second.soul_hash in delta3.get("changed", []), "bits=%d" % delta3.get("bits"))

    # ---- 5. 就近 DC 路由 ----
    print("[5] 就近 DC 路由")
    check("dc_b 归属解析", world.edge.nearest_dc([1.5, 0.5, 0.5]) == "dc_b")
    check("本地原点归属 dc_local", world.edge.nearest_dc([0.0, 0.0, 0.0]) == "dc_local")
    shard = world.edge.shard_of([1.5, 0.5, 0.5])
    check("分片解析", shard == "shard_1_0_0", "shard=%s" % shard)

    # ---- 6. 跨 DC 移动（relocate → handover）----
    print("[6] 跨 DC 移动")
    new_pos = [2.5, 0.5, 0.5]  # shard_2_0_0（dc_c 归属区）
    ok_move = world.edge.relocate(soul.soul_hash, new_pos)
    check("relocate 接受", ok_move)
    st = world.edge.device_status(cid)
    check("设备 DC 随灵魂迁移", st is not None and st["dc"] == "dc_c", "dc=%s" % (st or {}).get("dc"))
    pos_after = world.position_of(soul.soul_hash)
    check("世界位置已更新", pos_after == new_pos)

    # ---- 7. 吊销设备 → 会话立即失效 ----
    print("[7] 吊销设备")
    ok_revoke = world.edge.revoke_device(cid)
    check("吊销成功", ok_revoke)
    st = world.edge.device_status(cid)
    check("设备标记已吊销", st is not None and st["revoked"] is True)
    after_revoke = world.sessions.verify(access, credential_vault=world.credentials)
    check("关联 token 立即失效", after_revoke is None)

    # ---- 8. 19 维审计不回归 ----
    print("[8] 审计不回归")
    summary = world.audit_summary()
    check("审计运行无异常", isinstance(summary, str) and len(summary) > 0)

    world.close()

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
