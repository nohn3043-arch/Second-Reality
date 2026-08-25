# expert_report.py - 领域专家复核报告导出（Layer 2）
# ============================================================
# 人读产物：把审计引擎的机读结论 + 账本哈希锚点翻译成专家可复核的报告。
# 报告本身是本地展示层，不签名、不声称证据地位；所有可复算锚点（哈希 /
# 审计判定）都指向底层可重跑的原语，专家不必信任报告本身。
# ============================================================

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from audit_engine import SecondPerspectiveAuditor
from system.runtime import World

logger = logging.getLogger(__name__)


def _verdict_of(value) -> str:
    if isinstance(value, dict):
        return str(value.get("verdict", value))
    return str(value)


def _is_pass(value) -> bool:
    if isinstance(value, dict):
        return str(value.get("verdict", "")).startswith("PASS")
    return bool(value)


def export_world_expert_report(
    *,
    world: World,
    auditor: Optional[SecondPerspectiveAuditor] = None,
    out_path: Optional[Path] = None,
    out_dir: Path = Path("reports"),
) -> Path:
    """运行 19 项审计并在本地落一份专家复核 Markdown 报告。返回文件路径。"""
    auditor = auditor or SecondPerspectiveAuditor()
    report = auditor.audit_world(world)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    dims = [
        (attr, label)
        for attr, label in report.FIELDS
        if getattr(report, attr, None) is not None
    ]
    passed = [attr for attr, _ in dims if _is_pass(getattr(report, attr))]
    failed = [attr for attr, _ in dims if not _is_pass(getattr(report, attr))]

    chain = world.history.chain
    head_block = chain[-1][2] if chain else None
    chain_valid = world.history.validate_chain()
    soul_count = len(world.soul_ledger.souls)
    asset_count = len(world.economy._ledger) if hasattr(world.economy, "_ledger") else 0
    oracle_count = len(world.economy.oracle_sources)

    lines: list[str] = []
    lines.append("# Second-Reality 领域专家复核报告")
    lines.append("")
    lines.append(f"- 报告生成时间：{now}")
    lines.append(f"- 世界 ID：`{world.world_id}`")
    lines.append(f"- 存储后端：`{world.storage_backend}`")
    lines.append("")
    lines.append("## 1. 结论摘要")
    lines.append("")
    lines.append(f"- 审计维度：{len(dims)}/19 已执行，**{len(passed)} 通过 / {len(failed)} 未通过**")
    lines.append(f"- 世界历史链完整性校验：`{chain_valid}`")
    lines.append(f"- 灵魂注册数：`{soul_count}`")
    lines.append(f"- 锚定资产数：`{asset_count}`，预言机来源：`{oracle_count}`")
    lines.append("")
    lines.append("## 2. 19 项审计判定")
    lines.append("")
    lines.append("| 维度 | 判定 |")
    lines.append("|---|---|")
    for attr, label in dims:
        verdict = _verdict_of(getattr(report, attr))
        mark = "PASS" if attr in passed else "FAIL"
        lines.append(f"| {label} | `{mark}`：{verdict} |")
    lines.append("")
    if report.disclaimer:
        lines.append(f"声明：{report.disclaimer}")
        lines.append("")
    lines.append("## 3. 机读证据锚点（与 Layer 1 日志对照）")
    lines.append("")
    lines.append(f"- 世界历史链链头块哈希（head block_hash）：`{head_block or '—'}`")
    lines.append(
        f"- 应能在运行日志中找到 `history append block_hash={head_block}` 一行"
        if head_block
        else "- 世界历史链为空"
    )
    lines.append(f"- 每条灵魂注册在日志中对应 `soul registered soul_hash=...` 一行（共 {soul_count} 条）")
    lines.append("")
    lines.append("## 4. 专家复核指引")
    lines.append("")
    lines.append("不信任本报告，直接重跑原语复验：")
    lines.append("")
    lines.append("```bash")
    lines.append("pip install -r requirements.txt")
    lines.append("python - <<'EOF'")
    lines.append("import audit_engine")
    lines.append("from system.runtime import World")
    lines.append("world = World('<world_id>', data_dir='<data_dir>')")
    lines.append("r = audit_engine.SecondPerspectiveAuditor().audit_world(world)")
    lines.append("print(r.summary())")
    lines.append("print('chain_valid =', world.history.validate_chain())")
    lines.append("EOF")
    lines.append("```")
    lines.append("")
    lines.append("## 5. 边界声明")
    lines.append("")
    lines.append("- 本报告为本地展示层文件，**不构成签名审计记录**，不能单独作为合规证据。")
    lines.append("- 19 项审计是结构性合规校验，**不证明世界运行内容正确**；业务正确性由运营方负责。")
    lines.append("- 哈希锚点只能证明账本未被篡改，**不能证明审计判定本身无误**；判定逻辑请审阅 audit_engine.py。")
    lines.append("")

    target = out_path or (out_dir / f"expert-review-{now[:10]}-{world.world_id}.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="导出 Second-Reality 领域专家复核报告")
    parser.add_argument("--world-id", default="expert-review-world", help="世界 ID")
    parser.add_argument("--data-dir", default=None, help="账本数据目录（默认 .world_data）")
    parser.add_argument("--out", default=None, help="输出文件路径（默认 reports/ 下）")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    world = World(args.world_id, data_dir=args.data_dir)
    target = export_world_expert_report(
        world=world,
        out_path=Path(args.out) if args.out else None,
    )
    logger.info("expert review report written to %s", target)
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())