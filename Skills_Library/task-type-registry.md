---
Lifecycle: 阶段
Title: 任务类型注册表
Type: 锚点注册表
Created: 2026-05-12
Updated: 2026-05-15 (三表打通：加 type_id 统一键 + 新增文档生成/PPT生成类型)
related:
  - .cursor/rules/mod-skill-evaluation.mdc（评估体系，引用本表作为任务匹配中枢）
  - Skills_Library/skill-registry.json（技能通过 task_types 字段引用本表类型）
  - Skills_Library/skill-candidates.md（备选技能通过 task_types 字段引用本表类型）
---

# 任务类型注册表

> 本表是技能评估与任务匹配的**中枢锚点**。任务类型定义后，技能通过 `task_types` 字段反向声明覆盖范围。触发关键词可无限扩展，新说法自动追加。

## 结构说明

每条任务类型包含：
- **type_id**：唯一标识，与 `10-Topics/Task-Type-Registry.json` 同键。决策引擎以此为外键串联
- **类型名**：人类可读名称
- **父类型**：可选层级归属
- **触发关键词**：用户自然语言说法（逗号分隔，可无限追加）
- **结果期望**：该类型任务完成的评判标准（供表现评分参考）
- **覆盖技能**：声明覆盖本类型的技能列表（含内部/外部/备选，自动关联）

---

## 任务类型清单

### 1. Git 同步
- type_id：git_commit
- 父类型：—
- 触发关键词：提交git、Git同步、推仓库、提交远端、拉取、pull、push、commit、合并
- 结果期望：变更正确 add/commit/push，无遗漏文件，无密钥泄露
- 覆盖技能：
  - skill-git-crud（内部，active）
  - addyosmani/agent-skills（备选，/ship 子能力）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 2. Notion 写入
- type_id：notion_create
- 父类型：—
- 触发关键词：写入Notion、Notion创建、记到Notion、存到Notion、Notion更新、修改Notion页面
- 结果期望：内容正确写入目标页面，格式完整，无数据丢失
- 覆盖技能：
  - skill-notion-crud（内部，active）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 3. Notion 查询
- type_id：notion_query
- 父类型：—
- 触发关键词：Notion查询、查询Notion、搜Notion、读取Notion、查页面
- 结果期望：精准定位目标页面，展示摘要完整，命中无误
- 覆盖技能：
  - skill-notion-crud（内部，active）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 4. 对话备份
- type_id：conversation_backup
- 父类型：—
- 触发关键词：备份对话、保存对话、本轮总结、收束
- 结果期望：备份文件按归属正确落盘，内容完整，无丢失轮次
- 覆盖技能：
  - skill-conversation（内部，active）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 5. 知识入库
- type_id：knowledge_ingest
- 父类型：—
- 触发关键词：存入图书馆、入馆、存知识、入库
- 结果期望：知识卡片格式规范，索引正确，去重无误
- 覆盖技能：
  - skill-earth-library（内部，active）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 6. 代码审查
- type_id：code_review
- 父类型：办公编程
- 触发关键词：审查代码、代码review、review、检查代码、审阅、code review
- 结果期望：发现关键问题，给出可执行修改建议，无漏报严重缺陷
- 覆盖技能：
  - addyosmani/agent-skills（备选，/review 子能力）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 7. 软件规格
- type_id：software_spec
- 父类型：办公编程
- 触发关键词：写规格、spec、规格文档、定义需求、PRD、技术规格
- 结果期望：规格文档完整，边界清晰，验收标准明确
- 覆盖技能：
  - addyosmani/agent-skills（备选，/spec 子能力）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 8. 方案设计
- type_id：architecture_design
- 父类型：办公编程
- 触发关键词：设计方案、架构设计、plan、技术方案、系统设计
- 结果期望：方案覆盖多路径对比，有取舍说明，可执行
- 覆盖技能：
  - addyosmani/agent-skills（备选，/plan 子能力）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 9. 构建/编码
- type_id：coding_build
- 父类型：办公编程
- 触发关键词：写代码、实现、build、构建、编码
- 结果期望：代码符合规范，通过 lint，功能正确
- 覆盖技能：
  - addyosmani/agent-skills（备选，/build 子能力）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 10. 测试
- type_id：testing
- 父类型：办公编程
- 触发关键词：写测试、测试、test、单元测试、集成测试、跑测试
- 结果期望：覆盖关键路径，测试通过，无 flaky
- 覆盖技能：
  - addyosmani/agent-skills（备选，/test 子能力）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 11. 部署/发布
- type_id：deployment
- 父类型：办公编程
- 触发关键词：部署、发布、发版、上线、ship
- 结果期望：发布流程完整，无遗漏步骤，回滚预案就绪
- 覆盖技能：
  - addyosmani/agent-skills（备选，/ship 子能力）
  - skill-git-crud（内部，active，/push 子能力）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 12. 视频下载
- type_id：video_download
- 父类型：媒体操作
- 触发关键词：下载视频、下视频、保存视频、扒视频、download video、yt-dlp、视频提取
- 结果期望：输出可播放文件，含格式/分辨率选择，支持断点续传
- 覆盖技能：
  - MapleShaw/yt-dlp-downloader-skill（备选）
  - video-db/skills（备选，功能超集）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 13. 视频处理
- type_id：video_processing
- 父类型：媒体操作
- 触发关键词：处理视频、剪辑、字幕、转码、视频合成
- 结果期望：输出符合要求的视频文件，格式/质量达标
- 覆盖技能：
  - video-db/skills（备选）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 14. 网页抓取
- type_id：web_scraping
- 父类型：信息获取
- 触发关键词：爬取、抓取、网页信息、采集数据、scrape、网页获取
- 结果期望：精准提取目标数据，结构化输出，无遗漏
- 覆盖技能：
  - apify/agent-skills（备选）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 15. 行为学习
- type_id：behavior_learning
- 父类型：Agent 增强
- 触发关键词：记住这个、别再用X、纠正、learn、remember、行为偏好
- 结果期望：纠正被正确捕获，下次不再犯同错，且无误写入内核
- 覆盖技能：
  - maorfsdev/reflect-yourself（备选，暂缓）
  - skill-behavior（内部，active，趋势分析）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 16. 图表绘制
- type_id：chart_diagram
- 父类型：可视化
- 触发关键词：画图、流程图、UML、时序图、mermaid、架构图、图表
- 结果期望：图表清晰，语法正确可渲染，逻辑完整
- 覆盖技能：
  - gardusig/cursor-skills（备选）
  - skill-pretty-mermaid（外部，active）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 17. 文档生成
- type_id：docx_generate
- 父类型：办公编程
- 触发关键词：生成文档、生成报告、写报告、出报告、生成word、docx
- 结果期望：文档内容完整，格式规范，排版清晰
- 覆盖技能：
  - python-docx（内部，直接构建）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 18. PPT 生成
- type_id：ppt_generate
- 父类型：办公编程
- 触发关键词：做PPT、生成PPT、汇报PPT、出PPT、制作PPT、PPT报告
- 结果期望：内容完整，结构清晰，排版适配，无内容错配或缺漏
- 覆盖技能：
  - python-pptx + lxml（内部：模板填充 ⚠ 降权 — GROUP 嵌套不可达）
  - python-pptx（内部：直接生成 — 功能型，美观度有限）
  - **缺口**：尚未检索外部 PPT 生成/模板技能（GitHub/MCP）
- **触发计数**：0
- **历史中位轮次**：—
- **历史中位 Token**：—


### 19. PPT 模板填充
- type_id：ppt_template_fill
- 父类型：办公编程
- 触发关键词：套模板、模板填充
- 结果期望：内容正确填入模板，GROUP 嵌套绕行通过
- 覆盖技能：python-pptx + lxml（内部 ⚠ 降权）
- **触发计数**：0 | **历史中位轮次**：— | **历史中位 Token**：—


### 20. Git 拉取
- type_id：git_pull
- 父类型：—
- 触发关键词：拉取git、拉取远端、直接拉取、pull
- 结果期望：远端变更正确并入本地
- 覆盖技能：skill-git-crud（内部，active）
- **触发计数**：0 | **历史中位轮次**：— | **历史中位 Token**：—


### 21. WebSearch 调研
- type_id：web_search_research
- 父类型：信息获取
- 触发关键词：调研、搜索、查资料、WebSearch
- 结果期望：公开数据结构化，引用来源清晰
- 覆盖技能：WebSearch（内置）
- **触发计数**：0 | **历史中位轮次**：— | **历史中位 Token**：—


### 22. 知识脑学习
- type_id：knowledge_brain_learn
- 父类型：Agent 增强
- 触发关键词：学习、Knowledge Brain、知识脑
- 结果期望：结构化总结，逐点讨论固化
- 覆盖技能：Read / FetchMcpResource / WebFetch
- **触发计数**：0 | **历史中位轮次**：— | **历史中位 Token**：—


### 23. 系统审计
- type_id：system_audit
- 父类型：Agent 增强
- 触发关键词：系统检查、自检、审计、巡检系统、健康检查
- 结果期望：全系统架构/数据/编码/技能健康扫描，结构化报告
- 覆盖技能：待创建 mod-system-audit.mdc
- **触发计数**：0 | **历史中位轮次**：— | **历史中位 Token**：—


---

## 维护约定

- **新增任务类型**：当用户提出新的任务需求且不匹配现有类型时，追加一条（触发关键词至少 2 个）
- **追加关键词**：用户使用新说法描述已有任务类型时，直接追加到触发关键词列表（不新增类型）
- **更新覆盖技能**：技能注册/接入时，由 Agent 在对应的任务类型下追加覆盖技能行
- **更新历史数据**：每次完成技能评分后，更新对应任务类型的触发计数、中位轮次、中位 Token
