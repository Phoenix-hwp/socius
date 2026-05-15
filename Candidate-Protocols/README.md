# Candidate-Protocols

> 知识脑学习产出的新协议候选区。
> 
> 所有协议在此标注 `[待验证]` 状态，经过实践验证后再迁移到 `.cursor/rules/` 正式部署。

## 目录约定

- 每个候选协议一个 `.md` 文件
- 文件名格式：`CP-<编号>-<简短名称>.md`
- 开头 frontmatter 标注 `status: candidate`、`validated: false`、`source: <知识来源>`
- 验证通过后：文件移动到 `.cursor/rules/`，编号保留，状态更新为 `status: active`

## 验证标准

1. 在实际任务中至少应用 1 次
2. 产出物符合预期，无用户纠正
3. 与现有规则无冲突
4. 经验收讨论确认后迁移
