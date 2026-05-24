---
Title: CP-107：维度建模——星型与雪花 Schema
Lifecycle: 阶段
Created: 2026-05-21
status: candidate
cp_type: "conceptual"
cp_subtypes: ["structural"]
concept_anchor: "DataModeling.Dimensional"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "public"
source_access: "public"
sources:
  - { system: "webpage", title: "Dimensional Modeling Techniques — Kimball Group", url: "https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/" }

activation:
  self_recital: "维度建模=事实表(度量)+维度表(上下文)，星型扁平快查询，雪花节约存储——OLAP分析查询的基石（Ralph Kimball）"
  task_types: ["data_warehouse", "analytics", "reporting", "BI", "data_modeling"]
  concept_anchor: "DataModeling.Dimensional"
  decision_signal: "设计数据仓库/BI报表/分析型数据库时——需要在查询速度和存储效率之间做选择"
  anti_pattern: "用ER建模的范式化思维设计分析型表——导致每次查询都要JOIN十几张表"
  capability_hint: "数据仓库与BI建模"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，Kimball 星型/雪花 Schema 定义与 Kimball Group 官方文档一致"
  web_check: null
  doubts_resolved: []
  note: "来源 Kimball Group (Ralph Kimball) 官方技术文档，Kimball 被公认为维度建模之父"

depth_level: 4
---

# CP-107：维度建模——星型与雪花 Schema

## 定义

维度建模是 Ralph Kimball 提出的数据仓库设计方法论——将世界分为**度量（事实）**和**上下文（维度）**两大类。目标是让业务用户直观理解数据、让查询高效快速。

## 核心组件

| 组件 | 含义 | 内容 | 示例 |
|:---|:---|:---|:---|
| **事实表（Fact Table）** | 记录业务事件的数字度量 | 外键（指向各维度表）+ 数值度量列 | 销售事实：`date_key, product_key, store_key, sales_amount, quantity` |
| **维度表（Dimension Table）** | 描述度量发生的"5W1H"上下文 | 主键 + 描述性属性（文本为主） | 产品维度：`product_key, name, category, brand, price` |

## 星型 Schema vs 雪花 Schema

| 维度 | 星型 Schema | 雪花 Schema |
|:---|:---|:---|
| **结构** | 1 个事实表 + N 个**扁平**维度表（维度表不拆分） | 维度表进一步规范化为子表（层级拆分） |
| **JOIN 数** | 每个查询 1-N 个 JOIN（事实→N个维度） | 更多 JOIN（事实→维度→子维度） |
| **查询速度** | 快 ⚡ | 慢（JOIN 多） |
| **存储空间** | 冗余多（维度表宽） | 省（规范化减少冗余） |
| **业务理解** | 直观——业务用户一眼看懂 | 复杂——需理解规范化层级 |
| **适用场景** | 查询密集型 BI（报表/Dashboard） | 存储敏感 + 维度层级深（如产品→品类→大类） |

```
星型（Star）：                         雪花（Snowflake）：
     ┌─DIM_Date                       ┌─DIM_Date
     │                                │
FACT_Sales──DIM_Product          FACT_Sales──DIM_Product──DIM_Category──DIM_Department
     │                                │
     └─DIM_Store                      └─DIM_Store──DIM_Region──DIM_Country
```

## 四步维度建模设计流程

| # | 步骤 | 产出 |
|:---|:---|:---|
| 1 | 选择业务过程 | 要分析什么？（销售/库存/物流） |
| 2 | 声明粒度 | 事实表一行代表什么？（"每笔销售的每个商品行"） |
| 3 | 选择维度 | 从哪些角度分析？（日期/产品/门店/客户） |
| 4 | 确定事实 | 要度量什么？（金额/数量/折扣） |

**粒度是维度建模最关键的决定**——粒度错了，后续一切分析都偏离。

## 缓慢变化维度（SCD）— 维度数据变了怎么办

| 类型 | 策略 | 适用场景 |
|:---|:---|:---|
| **Type 0** | 保留原值不动 | 出生日期等永不变属性 |
| **Type 1** | 覆盖（丢历史） | 纠正拼写错误 |
| **Type 2** | 新增一行 + 有效期标记 | 需要完整历史——如客户地址变更 |
| **Type 3** | 新增列保存前值 | 只关心最近一次变化 |

**最常用 = Type 2**：新增行 + `effective_date` / `expiry_date` + `is_current` 标记。

## OLTP（ER 模型） vs OLAP（维度模型）

| 维度 | OLTP（ER 模型） | OLAP（维度模型） |
|:---|:---|:---|
| 目的 | 快速录入/修改单条数据 | 快速汇总分析千万条数据 |
| 设计原则 | 规范化——消除冗余，保证一致性 | 反规范化——牺牲冗余换查询速度 |
| 典型操作 | INSERT / UPDATE / DELETE 单行 | SELECT ... GROUP BY 百万行 |
| 表结构 | 多表 JOIN，每表窄 | 少量维度表宽，事实表深（行多） |

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 互补 | `DataModeling.ER` | ER 建模管 OLTP，维度建模管 OLAP——两者解决不同问题，互不替代 |
| 横向 | `BS.business_architecture` | 业务架构定义"分析什么"，维度建模定义"怎么存分析数据" |
