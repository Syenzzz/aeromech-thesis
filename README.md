# AeroMech Thesis

**面向航空机械与飞行器维修工程方向的毕业论文 / 毕业设计研究与写作 Agent Skill**

从选题分析、研究方案、工程分析、数据处理、章节写作，到图表生成、引用审计、质量门禁与答辩准备的全流程助手。

`v1.7.0` · 可回退状态机 · 学术诚信守卫 · 真正可编辑的 DOCX/PDF 交付

---

## 这是什么

`aeromech-thesis`（简称 AMT）是一个按 Agent Skills 约定加载的技能包：给它一个论文题目和你的真实材料（学校模板、文献、技术手册、维修数据），它会按状态机把整篇论文的研究与写作流程走完，并在每一步做质量门禁。

它服务的是**机械 / 维修 / 结构 / 可靠性**这一类专业方向，而不是泛泛的"论文生成"：

- 飞行器维修工程技术、飞机维修与机务工程
- 航空器系统维修（起落架、液压、燃油、飞行控制、环控、机轮刹车）
- 故障诊断与排故、FMEA / FTA / RCA
- 可靠性与维修性（MTBF、MTTR、可用度、Weibull）
- 航空器结构与机械结构分析、有限元 / 应力 / 变形 / 模态 / 疲劳
- 航空发动机机械方向、机械设计与航空器部件设计、航空制造与装配

> 非机械类的航空方向（航空物流、运输经济、民航运营管理、适航政策等），以及查重降重、对抗式答辩演练、纯排版交付，不属于本 Skill 的负责范围。

## 和"通用论文生成工具"的区别

| 维度 | 通用生成工具 | AeroMech Thesis |
|---|---|---|
| 工作顺序 | 先出文字，再补内容 | **Research First, Writing Second**：先建研究框架与工程分析，再写正文 |
| 数据与文献 | 容易"顺手编一条" | 不虚构文献 / 数据 / 标准编号；不确定标【待核实】，模拟数据标【假设/模拟·仅演示方法】 |
| 专业方法 | 无 | 内置 FMEA / FTA / RCA、可靠性分析、有限元流程等航空机械方法 |
| 流程控制 | 一次性生成，出错重来 | 可回退状态机，多轮中断 / 恢复；QA 发现问题可退回对应阶段修复 |
| 交付质量 | 内容看着像就行 | 构建链 + Delivery Gate 五态终局：缺证据即 BLOCK，ERROR 不会被当成 PASS |
| 排版 | 通用格式 | 有学校模板严格对齐模板；无模板用通用工科默认格式，不阻塞流程 |

## 核心能力

| 能力 | 说明 |
|---|---|
| 选题分析 | 可行性、专业匹配度、难度与风险评估，给出修改建议；无题目时可智能推荐 |
| 研究方案 | 技术路线、研究方法选择审计、论文目录（含可行性门禁 RF-01~10） |
| 文献研究 | 文献登记表、GB/T 7714 格式校对、来源分级（L1–L5） |
| 工程分析 | FMEA / FTA / RCA 分析框架、故障链识别、维修策略与维修大纲优化 |
| 数据处理 | 描述统计、数据清洗、单位统一、计算审计（CALC-XXX 可复现） |
| 可靠性分析 | MTBF / MTTR / 可用度计算、Weibull 拟合（须真实数据） |
| 图表生成 | 统一配图工作流：配图计划 → 逐图确认 → 生成 → 审核 → 插入确认；支持 Mermaid/figkit 确定性图与可编辑 PPTX/PNG/SVG |
| 视觉 QA | VIS-01~12 视觉检查进入构建链与交付门禁；渲染失败即失败，不生成假图 |
| 引用完整性 | 观点 → 来源 → 支持度 → 编号 → 格式 全链审计 |
| 研究完整性 | RQ / Evidence / Claim / Conclusion 注册表、可追溯图、模拟数据台账、证据越界检测 |
| QA 体检 | 六大维度检查（结构 / 学术 / 工程 / 数据 / 图表 / 写作），四级风险分级 |
| 答辩准备 | PPT 结构推荐、5/8/10 分钟答辩稿、预测问题库 |
| 文档交付 | 真正可编辑的 Word（Text / Heading / Table / Image）+ 内容一致的 PDF |

## 仓库结构

```
.
├── aeromech-thesis/          # Skill 本体（唯一权威编辑源，可整体安装）
│   ├── SKILL.md              # 主入口：路由、门禁、状态机
│   ├── README.md             # 面向使用者的完整说明
│   ├── CHANGELOG.md          # 逐版本变更与验证记录
│   ├── references/           # 规则库、子 Agent 说明、领域知识与模板
│   ├── scripts/              # 可执行实现（构建、QA、图表、研究引擎、生图）
│   └── tests/                # 回归测试套件（v1_4 / v1_4_1 / v1_5 / v1_6 / v1_6_5 / v1_7 / Test A / Test B）
├── docs/v1.6.5/              # 设计与规格文档（视觉系统、图类型规范、生图架构等）
├── docs/v1.7.0/              # 配图模块实施计划
├── .aeromech/artifacts/      # 开发期审计与各阶段报告（分析、QA、发布就绪）
├── sync.py                   # 开发目录 ⇄ 安装目录同步器（镜像同步 + 安全护栏）
├── build_skill_package.py    # WorkBuddy 平台技能包打包脚本（输出 dist/）
├── assets/                   # 平台头像/图标生成素材
├── DEV_SYNC.md               # 开发目录规程（权威源）
└── INSTALL_SYNC.md           # 安装目录规程（运行副本）
```

`aeromech-thesis/` 是一个自包含目录：**把整个目录拷进宿主 skills 目录即可使用**，不依赖仓库其他部分。

## 快速开始

### 1. 环境依赖

| 依赖 | 用途 | 是否必需 |
|---|---|---|
| Python 3.8+ | 运行 `scripts/` 下的全部实现 | 必需 |
| `python-docx`、`matplotlib`、`Pillow` | DOCX 生成、数据图绘制、图片处理 | 必需 |
| `docx2pdf` + Microsoft Word | DOCX → PDF 导出（Windows / macOS） | 需要 PDF 时必需 |
| Node.js + `mermaid-cli`（`mmdc`） | 技术路线图 / 流程图 / 故障树渲染 | 需要结构图时必需 |
| Google Chrome 或 Puppeteer chrome-headless-shell | Mermaid 渲染引擎（自动探测，无需配环境变量） | 随 `mmdc` |

```bash
pip install python-docx matplotlib Pillow docx2pdf
npm install -g @mermaid-js/mermaid-cli
```

### 2. 安装 Skill

把 `aeromech-thesis/` 整个目录放进你所使用宿主的 skills 目录：

```bash
# WorkBuddy
cp -r aeromech-thesis ~/.workbuddy/skills/

# Qoder
cp -r aeromech-thesis ~/.qoder-cn/skills/

# 其它按 Agent Skills 约定加载 SKILL.md 的宿主：对应 skills 目录
```

安装后目录里应当能直接看到 `SKILL.md`（即 `<skills>/aeromech-thesis/SKILL.md`）。

### 3. 调用

在对话中直接说：

```
调用 aeromech-thesis
```

随后按需提供材料（都可以后补，不会阻塞启动）：论文题目、学校格式要求 / Word 模板、任务书、参考文献（CNKI 题录或 PDF）、技术手册（AMM / CMM / IPC / TSM / SRM）、标准（GB / HB / MH / CCAR）、实验或维修数据、往届样文（仅参考结构与版式）。

**不需要**手动调用内部的 Figure / Data / QA 等模块，Skill 会按阶段自动加载。

### 可选：外部生图（不配置也完全可用）

概念示意图可以选择接入你自己的 OpenAI 兼容 Image API。不配置任何 Key 时，Skill 照常使用本地确定性图形管线，**零阻塞、零费用**：

```bash
python scripts/image_cli.py config   # 交互式写入 ~/.aeromech/.env，Key 输入不回显
python scripts/image_cli.py status   # 查看当前解析到的凭据状态（全掩码）
python scripts/image_cli.py test     # 真实冒烟（会提示费用，各模型仅调用 1 次）
```

配置模板见 [`aeromech-thesis/.env.example`](aeromech-thesis/.env.example)。凭据永不入库、永不写日志，`scripts/secret_leak_qa.py` 是三 scope 的泄漏防线。

## 使用流程

```
项目初始化（建立 .aeromech/ 工作区）
   ↓
S1  选题分析        →  S2  选题确认（无题目则推荐候选）
   ↓
S3  研究方案（技术路线 / 方法选择 / 目录）
   ↓
S4  文献研究（登记 + GB/T 7714 校对）
   ↓
S5  工程分析（FMEA / FTA / RCA 框架与缺口清单）
   ↓
S6  数据分析（清洗 / 统计 / 计算审计）
   ↓
S7  章节写作        →  S8  图表规划与生成
   ↓
S9  QA 论文体检（六大维度，可回退修复）
   ↓
S10 答辩准备
   ↓
交付：毕业论文.docx + 毕业论文.pdf
```

状态机支持任意断点中断与恢复（`state.yaml` + CK-XXX 检查点），也支持发现问题时回退到对应阶段修复。所有阶段迁移都有程序化校验，非法迁移会被拒绝而不是静默通过。

## 论文项目工作区

调用后会在你的工作目录建立如下结构：

```
你的论文项目/
├── materials/                # 你放原始材料的目录（Skill 只读不改）
│   ├── school/               #   学校格式要求 / 模板
│   ├── literature/           #   文献 PDF / CNKI 题录
│   ├── technical_manual/     #   AMM / CMM / IPC / TSM / SRM
│   ├── standard/             #   GB / HB / MH / CCAR
│   ├── project_data/         #   实验数据、维修记录
│   └── samples/              #   往届样文（仅参考结构版式，禁止复制内容）
├── .aeromech/                # Skill 内部工作区（不需要手动修改）
│   ├── state.yaml            #   状态机：当前阶段 / 迁移历史 / 未关闭问题
│   ├── context.md            #   上下文摘要
│   ├── materials.yaml        #   材料登记总表
│   ├── school-format.yaml    #   学校格式配置
│   ├── research/             #   研究完整性注册表
│   ├── artifacts/            #   分析 / 章节 / 图表 / 计算 / QA / 答辩产物
│   └── transcripts/          #   会话记录
├── 毕业论文.docx             # 最终交付物
└── 毕业论文.pdf
```

你负责：提供真实材料、确认选题与关键判断、最终审核内容。
你不必负责：编辑任何 YAML / 脚本、手绘图表、手工排版、手动调用子模块。

## 学术诚信底线

| 禁止行为 | 处理方式 |
|---|---|
| 虚构文献（作者 / 题名 / 期刊 / DOI） | 拒绝生成，要求提供真实题录 |
| 虚构 DOI、标准编号、手册内容 | 拒绝生成，标【待核实】 |
| 虚构实验或维修数据 | 拒绝生成，要求提供真实数据 |
| 把模拟数据当实测数据 | 必须标【假设/模拟·仅演示方法】，且不得进入正式结论 |
| AI 生成图像冒充研究证据 | 禁止标 verified/partial，仅可作为示意 |
| 渲染失败后用无关图占位 | 直接 FAIL 并阻止交付（不允许语义造假） |

不确定内容一律标【待核实】，而不是猜一个看起来合理的值。

## 开发与测试

开发目录（本仓库的 `aeromech-thesis/`）是**唯一权威编辑源**，安装目录只是运行副本，不得直接手改。

```bash
cd aeromech-thesis

# 全量回归（v1_4 / v1_4_1 / v1_5 / v1_6 / v1_6_5 / Test A / Test B）
python tests/run_all.py
python tests/run_all.py --list          # 列出套件
python tests/run_all.py --only v1_6_5   # 只跑单个套件
```

测试入口是 fail-closed 的：任一套件真实 FAIL → 总体 FAIL；只有 SKIP 而无 PASS 也记为未验证 → 总体 FAIL；SKIP 永不计入 PASS。

同步到安装目录：

```bash
python sync.py --to-install --dry-run   # 预览变更
python sync.py --to-install             # 执行同步
python sync.py --check                  # 期望 IDENTICAL，rc=0
```

`sync.py` 是镜像同步（新增 + 覆盖 + 删除目标侧多余文件），v1.5.0 起带四道护栏：删除只发生在目标侧、单次删除超过 10 个文件需 `--force`、源目录为空时拒绝执行、`--dry-run` 只打印计划。详见 [`DEV_SYNC.md`](DEV_SYNC.md) 与 [`INSTALL_SYNC.md`](INSTALL_SYNC.md)。

## 文档索引

| 文档 | 内容 |
|---|---|
| [`aeromech-thesis/SKILL.md`](aeromech-thesis/SKILL.md) | 主入口：触发判据、路由、阶段门禁、状态机规则 |
| [`aeromech-thesis/README.md`](aeromech-thesis/README.md) | 使用说明：能力清单、材料准备、示例对话、注意事项 |
| [`aeromech-thesis/CHANGELOG.md`](aeromech-thesis/CHANGELOG.md) | 逐版本变更、发布验证证据、已知限制 |
| [`references/`](aeromech-thesis/references) | 完整性、编排、研究智能、状态机、模板保真等领域规则 |
| [`docs/v1.6.5/`](docs/v1.6.5) | 视觉设计系统、图类型规范、图像 Provider 架构与测试计划 |
| [`docs/v1.7.0/`](docs/v1.7.0) | 统一配图模块实施计划 |
| [`DEV_SYNC.md`](DEV_SYNC.md) / [`INSTALL_SYNC.md`](INSTALL_SYNC.md) | 开发目录与安装目录的同步规程 |

## 版本

当前版本 **v1.7.0**（统一论文配图工作流）。

- **v1.7.0** — 统一配图工作流：配图计划与逐图确认、导入/登记已有图片、可编辑 PPTX 图形与柱线图/表格、PNG/SVG 导出、项目级外部生图额度与插入确认；旧项目图片可登记后重新确认。
- **v1.6.5** — 学术视觉系统单一来源、Visual QA（VIS-01~12）入交付门禁、用户自配 Image Provider（可选、零阻塞）、受控 AI 生图（Figure Plan 九字段闸 + 成本闸）、AI 视觉 ≠ 研究证据、三 scope 密钥泄漏扫描。
- **v1.6.0** — 全栈编排：StateIO / 检查点 / 断点恢复、统一材料进入、学校要求 provenance、阶段调度矩阵、Thesis Build、Delivery Gate 全聚合。
- **v1.5.0** — 研究智能层：方法选择审计与可行性门禁、统一诊断、白名单自动修复、Agent Loop（≤5 轮）、8 维质量评分。
- **v1.4.x** — 研究完整性层与稳定性加固：注册表 + RQG 门禁、人工复核回路、统一七态状态模型、开发/安装同步规程。
- **v1.0 ~ v1.3.x** — 交付链路：DOCX/PDF 引擎、目录与分页、封面 / 页面 / 图表保真、图质量检查。

完整变更与每次发布的验证证据见 [`CHANGELOG.md`](aeromech-thesis/CHANGELOG.md)。

## 已知限制

1. **学校正式模板缺失时**只能使用通用工科默认格式（宋体、小四、1.5 倍行距等）。这些是 fallback 默认值，不代表任何学校的正式要求；拿到模板后会自动重新应用格式。
2. **结构图依赖渲染环境**：没有 Chrome / `mmdc` 时，Mermaid 图会返回 `FIGURE_ERROR` 并阻止交付（v1.6.5 起不再自动 fallback）。此时应修复渲染环境，或改用 `figkit` 按真实节点数据程序化重绘。
3. **FMEA 评分不能代填**：S/O/D/RPN 无真实依据时只提供分析表骨架，需你回填真实依据。
4. **不提供可引用的文献条目**：只提供检索策略与登记框架，需自行从 CNKI / 万方等数据库获取真实文献。
5. **PDF 导出依赖 Word**（`docx2pdf`），无 Word 环境时只能交付 DOCX。
6. **最终格式仍以学校正式文件为准**：提交前建议对照学校最新要求做一次终检。

## 说明

本 README 描述的是**当前已实现并经过测试**的能力；未实现的功能不会提前写进文档。若发现文档与实现不一致，以 `SKILL.md` 与 `scripts/` 的实际行为为准，欢迎提 Issue 指出。

学术诚信是这个 Skill 的第一约束：它不会替你放心地"编一个看起来合理的答案"，而是把缺什么、待核实什么明确标出来。
