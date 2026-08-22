const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, LevelFormat, BorderStyle, WidthType,
  ShadingType, PageBreak, TableOfContents, Header, Footer, PageNumber,
  ExternalHyperlink
} = require('docx');

const FONT = "Microsoft YaHei";
const MONO = "Consolas";
const ACCENT = "1F4E79";
const CODE_BG = "F2F2F2";
const TABLE_HDR = "D5E8F0";

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const CONTENT_W = 9026; // A4 - 2*1440

function h1(t) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 160 },
    children: [new TextRun({ text: t, bold: true, font: FONT, size: 30, color: ACCENT })] });
}
function h2(t) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 120 },
    children: [new TextRun({ text: t, bold: true, font: FONT, size: 24, color: "2E74B5" })] });
}
function p(t, opts = {}) {
  return new Paragraph({ spacing: { after: 100 }, alignment: opts.align || AlignmentType.LEFT,
    children: [new TextRun({ text: t, font: FONT, size: 22, bold: opts.bold || false, italics: opts.italics || false })] });
}
function bullet(t) {
  return new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
    children: [new TextRun({ text: t, font: FONT, size: 22 })] });
}
function code(lines) {
  return lines.map(l => new Paragraph({
    spacing: { after: 0 },
    shading: { fill: CODE_BG, type: ShadingType.CLEAR },
    children: [new TextRun({ text: l === "" ? " " : l, font: MONO, size: 18 })]
  }));
}
function tbl(headers, rows) {
  const hs = headers.map(h => new TableCell({
    borders, width: { size: Math.floor(CONTENT_W / headers.length), type: WidthType.DXA },
    shading: { fill: TABLE_HDR, type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text: h, bold: true, font: FONT, size: 20 })] })]
  }));
  const rs = rows.map(r => new TableRow({ children: r.map((c, i) => new TableCell({
    borders, width: { size: Math.floor(CONTENT_W / headers.length), type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text: c, font: FONT, size: 20 })] })]
  })) }));
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: headers.map(() => Math.floor(CONTENT_W / headers.length)),
    rows: [new TableRow({ children: hs }), ...rs]
  });
}

const children = [];

// ---- Cover ----
children.push(new Paragraph({ spacing: { before: 1600 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "GCAE 全球认知审计引擎", bold: true, font: FONT, size: 48, color: ACCENT })] }));
children.push(new Paragraph({ spacing: { after: 80 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "技术说明文档", bold: true, font: FONT, size: 32, color: "2E74B5" })] }));
children.push(new Paragraph({ spacing: { after: 400 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "面向企业决策与 AI 系统的中立因果审计能力", font: FONT, size: 22, italics: true })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "版本 v1.0  |  2026-08-15  |  商业技术资料", font: FONT, size: 20, color: "808080" })] }));
children.push(new Paragraph({ children: [new PageBreak()] }));

// ---- TOC ----
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text: "目录", bold: true, font: FONT, size: 30, color: ACCENT })] }));
children.push(new TableOfContents("toc", { hyperlink: true, headingStyleRange: "1-2" }));
children.push(new Paragraph({ children: [new PageBreak()] }));

// 1
children.push(h1("1. 文档目的与读者对象"));
children.push(p("本文档面向具备互联网与工程背景的售前、架构与决策技术读者，系统描述 GCAE（Global Cognitive Audit Engine，全球认知审计引擎）的技术能力、内部架构与交付边界。本文不做通俗化改写，假定读者已具备以下基础："));
children.push(bullet("分布式系统与客户端/服务端部署模型的基本概念；"));
children.push(bullet("AI / LLM 的基本认知（模型、推理、提示、输出不确定性）；"));
children.push(bullet("企业高风险决策流程与合规审计的基本框架。"));
children.push(p("本文档仅描述技术能力，不构成商业授权；对外交付与售卖须以签署商业授权协议为前提（详见第 11 章）。"));

// 2
children.push(h1("2. 系统定位"));
children.push(p("GCAE 是全球首个中立、离线、决策无关（decision-agnostic）的认知偏审计引擎，为 AI 系统与企业决策提供独立第三方的安全与合规审计，且不修改被审系统的内部模型代码。"));
children.push(p("核心使命：", { bold: true }));
children.push(p("“一切不确定性、灾难与苦难，最终都源于我们对因果链的无知。”GCAE 通过系统性识别内隐假设、客观不确定性与人类认知偏，为高风险的理性决策提供中立、可追溯的结构性支撑。"));
children.push(p("关键成就：", { bold: true }));
children.push(bullet("通过 IMDA AI Verify 独立评估，总分 95（详见第 8 章）。"));
children.push(bullet("Web 端全流程五算子因果审计：零安装、零数据上传、完全确定性（https://nohnlins.com/audit/）。"));

// 3
children.push(h1("3. 核心审计流水线：五算子"));
children.push(p("GCAE 将一次决策的因果审计拆解为五个顺序算子，每个算子产出结构化中间结果，彼此串联构成完整审计链。"));
children.push(tbl(
  ["算子", "代号", "功能"],
  [
    ["叙事剥离 Narrative Strip", "NS", "剥离修辞、情绪与模糊量词，提取逻辑内核（纯粹因果事件链）。"],
    ["内隐假设透视 Implicit Assumption Perspective", "IAP", "揭示未声明假设、权限绕过、循环论证与特权预设。"],
    ["脆弱性闩锁 Fragility Latch", "LCH", "按假设计算 ΔD 崩塌概率，定位最脆弱变量（系统崩塌的关键节点）。"],
    ["因果链同步 Causal Chain Sync", "CCS", "逆反校验 + 反事实验证 + 黑洞（断点）检测。"],
    ["状态锚定 State Anchor", "STATE", "责任闭环锚定 + 生成 SHA-256 审计证书，确保结果可追溯、不可抵赖。"],
  ]
));
children.push(p("全部流程可完全在客户端侧运行，决策数据不离开本地环境（详见第 7 章）。", { italics: true }));

// 4
children.push(h1("4. 第二人称视角语言（Second-Person Perspective Language）"));
children.push(p("一种专用于决策验证与风险分解的结构化语言。它不做价值判断、不提供优化建议、不给出最终结论，仅对决策结构做形式化分解。"));
children.push(h2("4.1 三要素"));
children.push(bullet("Decision（D）：可执行的、定义清晰的判断，且责任归属明确。"));
children.push(bullet("Hypothesis Premise（A）：支撑决策有效性的、可证伪的前置条件。"));
children.push(bullet("Branch Response（ΔD）：当核心假设失效时的调整方案。"));
children.push(h2("4.2 形式化表达"));
children.push(code([
  "¬A ⇒ ΔD",
  "",
  "Decision: D",
  "Core Assumptions: A1, A2, A3",
  "",
  "Risk Branch Logic:",
  "¬A1 ⇒ ΔD",
  "¬A2 ⇒ ΔD",
  "¬A3 ⇒ ΔD",
]));

// 5
children.push(h1("5. 常式公式（Constant Formula）"));
children.push(h2("5.1 第一常式：p♾️Q"));
children.push(p("其中 p 表示原则、规则或约束，Q 表示结果、状态或后果；符号 ♾️ 表示不间断、连续且不可绕过的因果链接。若 p 与 Q 之间的连续性被切断、遮蔽或静默篡改，则系统不再运行于治理之下，而退化为叙事之下。"));
children.push(h2("5.2 结构审计谓词：Φ"));
children.push(code([
  "Φ{f_s, x, y} → {True, False}",
  "",
  "Φ : 结构审计谓词",
  "f_s : 系统功能",
  "x, y : 输入条件",
]));
children.push(p("该谓词仅验证给定决策结构是否满足理性一致性的最低要求，生成审计结果（True/False），不生成任何建议或优化。"));

// 6
children.push(h1("6. 技术架构"));
children.push(p("GCAE 以 Python 实现，核心由审计引擎、配置加载、责任账户与插件系统构成，并通过 LLM 适配器生成审计报告叙事。"));
children.push(h2("6.1 核心组件"));
children.push(code([
  "class ResponsibilityAccount:   # 责任追踪",
  "class AuditConfigLoader:       # 配置管理",
  "    - load_from_dict(config)",
  "    - load_from_json(path)",
  "class AuditPlugin:             # 插件扩展点",
  "    - analyze_func",
  "class CognitiveAuditEngine:    # 核心审计引擎",
  "    - register_plugin()",
  "    - audit()",
]));
children.push(h2("6.2 五算子插件（plugins/）"));
children.push(bullet("ns.py / iap.py / lch.py / ccs.py / state.py —— 分别对应第 3 章五个算子，以插件形式注册进引擎。"));
children.push(h2("6.3 LLM 适配器（llm_adapters/）"));
children.push(code([
  "class OpenAIAdapter:           # OpenAI API 集成",
  "    - generate_narrative()     # 由审计结果生成报告叙事",
]));
children.push(h2("6.4 运行形态"));
children.push(bullet("本地/私有化：Python 包直接部署于企业内网，数据不出域。"));
children.push(bullet("Web 端：全客户端侧执行（https://nohnlins.com/audit/），零安装、零上传。"));

// 7
children.push(h1("7. 关键属性"));
children.push(tbl(
  ["属性", "说明"],
  [
    ["中立审计", "保持 100% 中立第三方立场，不与任何 LLM 厂商关联。"],
    ["完全离线", "无需联网或云端数据传输即可运行。"],
    ["隐私优先", "零用户数据采集，本地闭环数据隔离。"],
    ["偏检测", "识别内隐假设、客观不确定性与认知盲区。"],
    ["不改模型", "兼容所有主流 LLM，不改动其源码。"],
    ["结构化分析", "仅做决策结构验证，不输出主观结论。"],
  ]
));

// 8
children.push(h1("8. 评估背书"));
children.push(p("GCAE 已通过新加坡 IMDA（Infocomm Media Development Authority）AI Verify 独立评估，综合得分 95。该评估为第三方权威技术验证，报告见项目仓库 IMDA_AI_Verify_Causal_Audit_Report.pdf。"));

// 9
children.push(h1("9. 部署与集成"));
children.push(h2("9.1 环境要求"));
children.push(bullet("Python 3.8+；核心依赖见 requirements.txt；OpenAI 适配器依赖见 requirements-openai.txt。"));
children.push(h2("9.2 安装"));
children.push(code([
  "pip install -r requirements.txt",
  "pip install -r requirements-openai.txt   # 可选",
]));
children.push(h2("9.3 基本审计示例"));
children.push(code([
  "from Cognitive_Audit_Engine import (",
  "    CognitiveAuditEngine, ResponsibilityAccount, AuditConfigLoader)",
  "",
  "account = ResponsibilityAccount(name=\"audit_team\", role=\"third_party_auditor\")",
  "config  = AuditConfigLoader.load_from_json(\"config.json\")",
  "engine  = CognitiveAuditEngine(account=account, config=config)",
  "",
  "result = engine.audit({",
  "    \"decision\": \"Approve project X\",",
  "    \"assumptions\": [\"A1\", \"A2\", \"A3\"],",
  "    \"context\": {...}",
  "})",
  "print(result)   # {True, False}",
]));

// 10
children.push(h1("10. 适用场景"));
children.push(bullet("企业战略：重大投资与战略决策的结构化审查；"));
children.push(bullet("政府政策：公共政策研究与影响评估；"));
children.push(bullet("智库研究：研究与分析支撑；"));
children.push(bullet("风险控制：机构风险管理；"));
children.push(bullet("AI 系统审计：LLM 输出验证与偏检测。"));

// 11  (compliance guardrail)
children.push(h1("11. 授权与合规边界（重点）"));
children.push(p("本章为对外交付与售卖的硬性前置条件，任何商业化行为均须遵守。", { bold: true, italics: true }));
children.push(h2("11.1 版权归属"));
children.push(p("本仓库为 GCAE 技术展示作品。Copyright © 2026 上海临茗君华科技有限公司 与 NOHN AI TECHNOLOGY PTE. LTD.，保留所有权利。"));
children.push(h2("11.2 授权分层"));
children.push(tbl(
  ["使用主体", "用途", "授权要求"],
  [
    ["自然人个体", "非商业学术研究 / 学习 / 个人实验", "依 LICENSE 中“Free Individual Research License”免费"],
    ["政府 / 事业单位 / 企业", "任何用途（含内部部署、产品开发、服务提供、对外售卖）", "须事先签署书面商业授权协议并支付约定费用"],
  ]
));
children.push(h2("11.3 对“对外售卖 / 交付”的约束"));
children.push(bullet("本文档仅描述技术能力；实际对外交付、部署、集成、分发或售卖，必须以签署商业授权协议为前提。"));
children.push(bullet("未签署商业授权前，政府 / 企业不得复制、部署、运行、集成或分发本作品。"));
children.push(bullet("申请授权：国际 ai@nohnlins.com / 中国 ai@tx.nohnlins.com。"));
children.push(h2("11.4 Clean-room 条款"));
children.push(p("任何主体若独立开发功能、架构或决策模型实质相似的产品，除非能提供完整、连续、可追溯的独立开发证据，否则推定为实质性衍生侵权。"));
children.push(h2("11.5 司法管辖"));
children.push(bullet("用户位于中国境内 → 上海临茗君华科技有限公司（适用中国法）；"));
children.push(bullet("用户位于中国境外 → NOHN AI TECHNOLOGY PTE. LTD.（适用新加坡法，SIAC 仲裁）。"));

// 12
children.push(h1("12. 免责声明"));
children.push(p("本语言体系仅应用于决策过程中的结构审查与分解，不参与决策制定，亦不干预最终决策。作者不对任何后续执行结果承担法律责任或运营责任。"));

const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: FONT, color: ACCENT }, paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: FONT, color: "2E74B5" }, paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 1 } },
    ]
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 1 } },
      children: [new TextRun({ text: "GCAE 全球认知审计引擎 · 技术说明", font: FONT, size: 16, color: "808080" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({
      children: [new TextRun({ text: "第 ", font: FONT, size: 16 }),
        new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16 }),
        new TextRun({ text: " 页 / 共 ", font: FONT, size: 16 }),
        new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: 16 }),
        new TextRun({ text: " 页   ·   商业技术资料，受版权与授权条款约束", font: FONT, size: 16, color: "808080" })] })] }) },
    children
  }]
});

Packer.toBuffer(doc).then(buf => {
  const out = "C:\\Users\\q3265\\Desktop\\GCAE技术说明_国美孙浩.docx";
  fs.writeFileSync(out, buf);
  console.log("WROTE: " + out + " (" + buf.length + " bytes)");
});
