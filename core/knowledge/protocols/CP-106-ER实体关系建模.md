---
Title: CP-106：ER 实体关系建模
Lifecycle: 阶段
Created: 2026-05-21
status: candidate
cp_type: "conceptual"
cp_subtypes: ["procedural"]
concept_anchor: "DataModeling.ER"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "public"
source_access: "public"
sources:
  - { system: "webpage", title: "Entity-Relationship Model — Chen 1976", url: "https://www.csub.edu/~ychoi2/MIS%20340/DBLecture/ERD/ERD_article_by_Chen.pdf" }

activation:
  self_recital: "ER建模=实体+关系+属性三要素，基数约束四个类型——数据库概念设计的基石（Peter Chen 1976）"
  task_types: ["database_design", "system_design", "data_modeling", "architecture"]
  concept_anchor: "DataModeling.ER"
  decision_signal: "设计数据库表结构、分析系统实体关系、梳理业务信息架构时需要抽象实体和关系时"
  anti_pattern: "跳过ER概念建模直接建表——导致后续发现遗漏实体或关系时大量返工"
  capability_hint: "数据库概念设计"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，ER模型三要素+基数四类型与 Peter Chen 1976 论文及数据库教材完全一致"
  web_check: null
  doubts_resolved: []
  note: "来源 Peter Chen 1976 ACM论文 'The Entity-Relationship Model–Toward a Unified View of Data'"

depth_level: 4
---

# CP-106：ER 实体关系建模

## 定义

Entity-Relationship（ER）模型是 Peter Chen 在 1976 年提出的数据库概念设计工具——用实体、关系、属性三个抽象概念来描述现实世界的数据结构。ER 图是数据库表结构设计前必须经过的「概念蓝图」阶段。

## 三要素

| 要素 | 含义 | ER 图符号 | 示例 |
|:---|:---|:---|:---|
| **实体（Entity）** | 需要记录信息的"事物"——人、地点、对象、事件 | 矩形 | 学生、课程、订单、仓库 |
| **关系（Relationship）** | 实体之间的联系 | 菱形，用线连接相关实体 | 学生「选修」课程 |
| **属性（Attribute）** | 实体或关系的特征 | 椭圆，连接到实体或关系 | 学生的学号/姓名、课程的学分 |

## 基数约束（Cardinality）

两个实体之间的数量对应关系，共 4 种：

| 类型 | 含义 | 示例 |
|:---|:---|:---|
| **一对一（1:1）** | A 的每个实例最多对应 B 的一个实例，反之亦然 | 员工 ↔ 工位（每人一个固定工位） |
| **一对多（1:N）** | A 的一个实例可对应 B 的多个实例，但 B 的一个实例只对应 A 的一个实例 | 部门 → 员工（一个部门有多个员工） |
| **多对一（N:1）** | 一对多的反向 | 员工 → 部门（多个员工属于一个部门） |
| **多对多（M:N）** | A 和 B 的实例可互相多对应 | 学生 ↔ 课程（一个学生选多门课，一门课有多个学生） |

## 构建 ER 图的 5 步法

| # | 步骤 | 输出 |
|:---|:---|:---|
| 1 | 列出所有候选实体 | 实体清单（名词识别：用户/订单/商品/仓库…） |
| 2 | 识别实体间关系 | 关系名 + 参与实体（动词识别：下单/包含/存储…） |
| 3 | 画 ER 图草图 | 矩形 + 菱形 + 连线——不画属性先 |
| 4 | 标注基数约束 | 1 / N / M 标注在每条关系线两端 |
| 5 | 补充属性 | 每个实体和关系的椭圆——仅关键的（≤5 个） |

## 常见错误

| 错误 | 表现 | 修正 |
|:---|:---|:---|
| 把属性当实体 | 把"地址"画成实体而非学生的一个属性 | 能独立存在且有自己的属性 → 实体；只是描述另一事物的值 → 属性 |
| 漏掉隐性关系 | 画了学生和课程，但没画"教师授课"这个三方关系 | 检查每个动词：谁对谁做了什么？ |
| 基数标错 | 学生-宿舍标成 1:1，实际是 1:N（一栋宿舍住多个学生） | 每次标注时间问："一个 X 可以对应多少个 Y？"再问反方向 |
| 过早细化 | 在概念设计阶段就纠结字段类型和索引 | ER 图只管"有什么"和"什么关系"，不管"怎么存" |

## 与后续设计的衔接

```
ER 概念模型（本协议）
  ↓ 转换规则
关系模式（表 + 主键 + 外键）
  ↓ 规范化
第三范式（3NF）表结构
  ↓ 物理设计
SQL DDL（CREATE TABLE ...）
```

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 下游 | `DataModeling.Dimensional` | ER 模型是 OLTP 的基石，维度建模是 OLAP 的基石——两者互补 |
| 横向 | `ARCH.business_core_elements` | 业务架构的价值流+能力 = 业务流程视角；ER = 数据结构视角 |
