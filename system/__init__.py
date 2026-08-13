# system/ 系统层 - SPL-Virtual-World-Base 的实现载体
# ============================================================
# 职责：承载虚拟世界的"实际运行"能力，取代 constitution.py /
# constitution_rules.py 中 blockchain / multi_agent 的占位桩。
#
# 分层边界：
#   constitution_rules.py  宪法规则（只读、不可变）
#   audit_engine.py        第二视角审计引擎（元层裁判）
#   system/                系统实现（本包）
#   virtual_world.py       演示运行时客户端
#
# 约束：本包暴露的状态必须可被 audit_engine.SecondPerspectiveAuditor
# 的 18 项审计检查；创世（GenesisCondition.initiate_genesis）所需的
# 组件全部由本包真实创建并注入。
#
# 模块规划（桩转实渐进式落地）：
#   ledger.py        状态账本：SoulLedger / HistoryLedger / EconomicReserve（持久化）
#   consensus.py     共识：节点注册、提案、公投计票（≥2/3）
#   agent_engine.py  智能体：决策 + 记忆封存/校验
#   runtime.py       无头运行时：tick 循环 + 快照 + 审计上报
#   api.py           服务接口：REST/WebSocket + 鉴权
