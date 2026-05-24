## 增量同步补丁（2026-05-02）

> **合并策略**：局部追加（append）。**不清空**既有正文；与 `plans/Behavior-Preferences-Sync-Playbook.md` 锚点一致。  
> **来源**：`Cursor-usage-profile-and-templates.md` §3（工具与环境等）+ 本轮 WebDAV 同步实践沉淀。

### 工具与环境（增补）

- **工作区 Git / Gitee**：口语「提交git」（别名 Git同步 / 推仓库 / 提交远端）走 `plans/Gitee-Workspace-Git-Workflow.md` 与规则 `git-workspace-commit.mdc`；与 Notion 写入流程相互独立。
- **CloudDrive2 WebDAV + rclone（Cursor_Knowledge）**：入口 `.cursor/tools/cd2_sync_menu.bat`；执行上传/下载脚本前须**二次确认本地盘符**（仅输入 `Y` 继续）；库根使用 `.kb_sync_local_marker.json` 作为本地锚点（脚本侧排除同步，**不上传**远端）；日志与变更清单写入当前库根 `Daily-Backups/TMP_SyncLogs/`（随解析到的库路径自动派生）；终端额外输出 **`file:///...`** 链接，便于在 Cursor 对话内直接打开清单（避免纯 Windows 路径被错误 URI 化）。
- **同步风险提示**：`rclone sync` 以本地为源；路径误判可能造成远端大规模删除；重要操作前先使用菜单 **6**（上传预览）/ **7**（下载预览）做 dry-run。

### 执行记录（Skill）｜2026-05-02

- **对话概览**：WebDAV 同步链路加固（标识文件、盘符二次确认、日志与清单落盘随库路径、`file:///` 清单链接）。
- **观察到的偏好**：远端同步须防误删；日志必须与当前本地库同盘；交互路径须可在对话内可靠打开。
- **置信度**：高（已多轮 dry-run / 正式同步验证）。
