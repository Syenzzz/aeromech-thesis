# 论文配图工作流（v1.7.0）

可编辑图形运行依赖见 `scripts/requirements-figure.txt`，使用用户当前 Python 环境或项目虚拟环境安装；不要把安装到临时测试目录的依赖当作发布内容。图形、表格的排版仍需按论文版心和用户提供的规范人工检查。

适用于完整论文与单独配图。论文模式阅读用户提供的正文、数据、参考资料与学校规范，检查已有图片；对材料冲突或缺少的工程关系列出来源和待确认问题，不编造数据或设备结构。单图模式可简化材料读取与清单，但生成前仍须确认图形内容。

## 外部服务逐步配置

用户希望配置或更换生图服务时，先运行 `python scripts/image_cli.py status` 检查状态，不输出或读取明文密钥；未经用户要求不覆盖现有配置。然后在对话中逐项询问，每次只问一项，根据前一项回答给出下一项的具体提示：

1. 服务商或接口类型：区分 OpenAI 官方与 OpenAI 兼容服务。现有实际生成后端为 `openai` 和兼容的 `qwen`；其他名称即使能登记配置，也不代表已经实现调用。未知兼容性时先核实，不承诺可用。
2. 图片模型名：询问用户提供的模型名。官方 OpenAI 使用项目默认值时说明默认模型及需有对应 API 权限；兼容服务使用其实际提供的模型名，不假定能用默认值。
3. Base URL：询问 API 基础地址。OpenAI 官方默认 `https://api.openai.com/v1`，用户确认使用官方地址时可留空；兼容服务按服务商提供的地址填写。不要要求或接收包含密钥的 URL；区分基础地址与完整的 `/images/generations` 路径。
4. API Key：不要在聊天中索取、接收、展示或记录密钥。提供实际 Skill 根目录下 `scripts/image_cli.py config` 的本地运行方式，让用户本人在终端的 `API Key` 无回显提示中输入。也可以将已确认的非敏感后端、模型和地址作为 CLI 参数传入，密钥仍只在终端输入；参数要使用当前操作系统正确的安全引用，禁止将密钥放入命令行、日志或项目文件。

用户完成后运行 `status`，只报告配置态及不含密钥的信息。配置成功不等于真实调用成功；经用户同意使用已配置服务和调用额度后，再进行一次真实生成测试，说明可能产生费用。失败则报告实际错误并引导修复；未配置时继续支持本地绘图。

1. 先向用户列出配图建议：编号、名称、类型、章节位置、目的、依据、节点及连接关系、数据来源、既有图片处理、待确认项、生成方式、可编辑程度和交付格式。按用户指定数量规划，未指定时适量推荐。反复根据反馈修改，直到用户明确确认。
2. 创建项目的 `.aeromech/figures/figure-plan.yaml`，采用 `figure_iface.save_plan` 保存；每图至少包含 `figure_id`、`name`、`kind`、`source`、`out` 和研究链接。论文图统一放在 `.aeromech/artifacts/figures/final/`，输出文件名使用 `fig1-1.png` 形式并对应章节图号，供既有构建和图形 QA 匹配。调用 `figure_workflow.py <root> sync-plan` 列出并登记当前清单，用户确认后调用 `confirm-plan`。任何内容或源文件改变均需重新确认受影响的图。
3. 研究数据和逻辑图使用确定性方式。`kind=editable` 的 JSON 源为 `nodes`（id/text/x/y/w/h，坐标为厘米；可选 shape=rounded/rectangle/diamond/ellipse、role=normal/medium/high）与 `edges`（from/to，可选 label）；`kind=editable_chart` 的 JSON 源包含 `type`（bar/line）、`categories` 和 `series`（name/values），可选 title/ylabel；`kind=editable_table` 包含 `columns` 与 `rows`，风险矩阵可另提供与 rows 同形状的 `roles`（normal/medium/high）。值必须来自用户材料；无数据时先询问，示意用途须明确标注。输出 PNG、SVG 和含原生对象的 PPTX，源 JSON 一并交付。复杂故障树、事件树或 FMEA 如不能忠实表达时，不得用普通方框冒充合格结果，应改用能准确表达的方法并请用户复核。

   故障树将计划 `type` 设置为 `fault_tree`，节点的 `semantic` 必须明确标注 `top_event`、`gate` 或 `basic_event`；逻辑门文字标明 AND/OR，且门指向至少两个输入事件。该工具使用文字标识逻辑门，若学校或标准要求专用门符号，应采用支持相应符号的绘图工具。
4. 概念插图可用已配置的外部图像服务。项目开始时说明提供商、可能发送的内容和费用；用户授权后运行 `external-policy --allow yes --max-calls N`。不允许发送时设为 `no`。项目额度跨图累计，未授权或耗尽不能调用。外部类型与 Figure Plan 的必填字段见 `references/image-provider.md`。AI 图是示意素材，不是研究证据；不能确定的工程细节不得表现为真实结构。
5. 调用 `figure_iface.py <root> generate --figure FIG-ID`；已有图片在清单中使用 `kind=user_asset` 和项目内 `out` 路径，计划确认后执行 `adopt-existing --figure FIG-ID` 登记来源。然后用 `figure_workflow.py <root> status` 列出图片和状态，向用户展示实际图片。反复处理反馈，默认只改指定图；需要跨图调整时先告知并征求决定。确认某图时运行 `confirm-image --figure FIG-ID`，修改后须重新确认。
6. 列出图号、图题、正文引用与位置。用户另行确认插入后，逐图执行 `confirm-insertion --figure FIG-ID`，再通过既有构建和 PDF QA 交付。不得把未经确认的图片记作用户认可。

学校规范优先；不同图类型可有不同风格，但整个论文要协调。优先交付清晰、可缩放图；AI 位图标明实际像素，不声称放大增加了真实细节。旧项目图片和记录可读取，但旧记录本身不代表用户确认。
