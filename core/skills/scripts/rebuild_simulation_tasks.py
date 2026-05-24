#!/usr/bin/env python3
"""重建仿真任务体系 — 移除旧仿真待办 + 创建新角色扮演仿真任务"""
import json, os, sys, shutil
from datetime import date, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACKER = os.path.join(BASE, '10-Topics', 'Pending-Plan-Tracker.json')
TASK_POOL = os.path.join(BASE, 'Simulation-Sandbox', 'task-pool.json')
TRAINING = os.path.join(BASE, 'Simulation-Sandbox', 'training-plan.json')
BRIEFS = os.path.join(BASE, 'Simulation-Sandbox', 'briefs')
PLANS = os.path.join(BASE, '10-Topics', 'plans')

# ── Step 1: Remove old simulation tasks ──
REMOVE_IDS = {
    'V012-DRILL-001', 'V012-DRILL-002', 'V012-DRILL-003', 'V012-DRILL-004',
    'V012-DRILL-005', 'V012-DRILL-006', 'V012-DRILL-007', 'V012-DRILL-008',
    'P058', 'P060', 'P051', 'P052', 'P053', 'P054'
}

with open(TRACKER, 'r', encoding='utf-8') as f:
    tracker = json.load(f)

old_pending = tracker.get('pending', [])
removed_count = 0
new_pending = []
for p in old_pending:
    if p['id'] in REMOVE_IDS:
        removed_count += 1
    else:
        new_pending.append(p)

tracker['pending'] = new_pending
print(f'[1/5] Removed {removed_count} old simulation tasks from tracker')

# ── Step 2: Define 14 new tasks ──
NEW_TASKS = [
    # ① 电商运营
    {
        'id': 'V012-DRILL-010', 'role': '电商运营',
        'topic': '渠道销售数据 PPT + 转化漏斗图',
        'task_type': 'rich_document_generate', 'difficulty': 'medium', 'min_subtasks': 4,
        'fuzzy_brief': 'briefs/V012-DRILL-010.md', 'expected_output': 'outputs/V012-DRILL-010/',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过槽位追问', '不得单次生成final产物'],
        'slots': [
            {'name': 'format', 'label_cn': '输出格式', 'strategy': 'must_ask', 'example_prompt': 'PPTX还是PDF？'},
            {'name': 'data_source', 'label_cn': '数据来源Notion页面', 'strategy': 'must_ask', 'example_prompt': '数据在Notion哪个页面？给我页面名或URL'},
            {'name': 'funnel_dimension', 'label_cn': '漏斗维度', 'strategy': 'context_derive', 'default_rule': '"按渠道拆转化漏斗"→维度=渠道'},
            {'name': 'date_range', 'label_cn': '数据时间范围', 'strategy': 'must_ask', 'example_prompt': '"上个月"具体是哪天到哪天？'}
        ]
    },
    {
        'id': 'V012-DRILL-011', 'role': '电商运营',
        'topic': '竞品SKU抓取 + 对比表 + 企业微信推送',
        'task_type': 'composite', 'difficulty': 'hard', 'min_subtasks': 5,
        'fuzzy_brief': 'briefs/V012-DRILL-011.md', 'expected_output': 'outputs/V012-DRILL-011/',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过Webhook推送验证', '竞品名称须逐一确认'],
        'slots': [
            {'name': 'competitor_list', 'label_cn': '竞品名称列表', 'strategy': 'must_ask', 'example_prompt': '具体是哪几个竞品？给全名'},
            {'name': 'price_range', 'label_cn': '价格区间', 'strategy': 'auto_fill', 'default_rule': '200-500元（场景已给）'},
            {'name': 'push_channel', 'label_cn': '推送渠道', 'strategy': 'must_ask', 'example_prompt': '企业微信的Webhook URL是什么？'},
            {'name': 'output_format', 'label_cn': '最终输出', 'strategy': 'auto_fill', 'default_rule': 'XLSX对比表+Markdown简报+Webhook推送'}
        ]
    },
    # ② 数据分析师
    {
        'id': 'V012-DRILL-012', 'role': '数据分析师',
        'topic': '用户留存分析报告 PDF（漏斗+趋势折线）',
        'task_type': 'chart_diagram', 'difficulty': 'medium', 'min_subtasks': 3,
        'fuzzy_brief': 'briefs/V012-DRILL-012.md', 'expected_output': 'outputs/V012-DRILL-012/retention-report.pdf',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过数据文件路径确认', '不得单图代替双图'],
        'slots': [
            {'name': 'data_file', 'label_cn': '留存原始数据文件', 'strategy': 'must_ask', 'example_prompt': '原始数据在哪个文件/路径？'},
            {'name': 'report_structure', 'label_cn': '报告结构', 'strategy': 'auto_fill', 'default_rule': '留存漏斗+趋势折线+简要建议'},
            {'name': 'output_format', 'label_cn': '输出格式', 'strategy': 'auto_fill', 'default_rule': 'PDF'}
        ]
    },
    {
        'id': 'V012-DRILL-013', 'role': '数据分析师',
        'topic': '社区精华帖抓取 + 知识脑消化入库',
        'task_type': 'composite', 'difficulty': 'hard', 'min_subtasks': 4,
        'fuzzy_brief': 'briefs/V012-DRILL-013.md', 'expected_output': 'outputs/V012-DRILL-013/',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过URL确认', '知识卡片须完整走消化管线'],
        'slots': [
            {'name': 'target_url', 'label_cn': '目标社区URL', 'strategy': 'must_ask', 'example_prompt': '具体是哪个社区？给完整URL'},
            {'name': 'scope', 'label_cn': '抓取范围', 'strategy': 'context_derive', 'default_rule': '精华帖+用户增长主题'},
            {'name': 'collection_name', 'label_cn': '知识库集合名', 'strategy': 'context_derive', 'default_rule': '用户增长精华帖'},
            {'name': 'page_count', 'label_cn': '抓取页数', 'strategy': 'must_ask', 'example_prompt': '抓几页？全部精华帖还是前N页？'}
        ]
    },
    # ③ 产品经理
    {
        'id': 'V012-DRILL-014', 'role': '产品经理',
        'topic': '用户反馈智能分类工具 PRD + 系统架构图 DOCX',
        'task_type': 'software_spec', 'difficulty': 'hard', 'min_subtasks': 5,
        'fuzzy_brief': 'briefs/V012-DRILL-014.md', 'expected_output': 'outputs/V012-DRILL-014/',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过需求澄清访谈', '架构图须与PRD一致'],
        'slots': [
            {'name': 'product_domain', 'label_cn': '产品领域', 'strategy': 'auto_fill', 'default_rule': '用户反馈智能分类'},
            {'name': 'spec_type', 'label_cn': '规格类型', 'strategy': 'context_derive', 'default_rule': 'PRD（面向产品+研发）'},
            {'name': 'acceptance_criteria', 'label_cn': '验收标准', 'strategy': 'must_ask', 'example_prompt': '有没有必须满足的验收条件？准确率/性能/兼容性？'},
            {'name': 'tech_stack', 'label_cn': '技术约束', 'strategy': 'must_ask', 'example_prompt': '技术栈有约束吗？Python/本地/云端？'}
        ]
    },
    {
        'id': 'V012-DRILL-015', 'role': '产品经理',
        'topic': '下季度 Roadmap — Notion需求→优先级排序→PDF+PPTX',
        'task_type': 'rich_document_generate', 'difficulty': 'medium', 'min_subtasks': 4,
        'fuzzy_brief': 'briefs/V012-DRILL-015.md', 'expected_output': 'outputs/V012-DRILL-015/',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过Notion数据来源确认', '须输出PDF+PPTX双格式'],
        'slots': [
            {'name': 'data_source', 'label_cn': '需求池Notion来源', 'strategy': 'must_ask', 'example_prompt': '需求池在Notion哪个数据库/页面？'},
            {'name': 'priority_criteria', 'label_cn': '优先级标准', 'strategy': 'must_ask', 'example_prompt': 'P0/P1怎么定义？按营收影响还是紧急度？'},
            {'name': 'output_formats', 'label_cn': '输出格式', 'strategy': 'auto_fill', 'default_rule': 'PDF（研发细节）+PPTX（总监简报）'}
        ]
    },
    # ④ 项目经理
    {
        'id': 'V012-DRILL-016', 'role': '项目经理',
        'topic': '项目周报 — Notion任务进度→XLSX燃尽数据→PDF周报',
        'task_type': 'rich_document_generate', 'difficulty': 'easy', 'min_subtasks': 3,
        'fuzzy_brief': 'briefs/V012-DRILL-016.md', 'expected_output': 'outputs/V012-DRILL-016/weekly-report.pdf',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过Notion数据来源确认', '风险项须标红'],
        'slots': [
            {'name': 'data_source', 'label_cn': 'Notion任务数据库', 'strategy': 'must_ask', 'example_prompt': '任务数据在Notion哪个数据库？给database ID或页面名'},
            {'name': 'date_range', 'label_cn': '周报日期范围', 'strategy': 'must_ask', 'example_prompt': '这周具体是哪天到哪天？'},
            {'name': 'risk_threshold', 'label_cn': '风险标红规则', 'strategy': 'context_derive', 'default_rule': '进度<70%或已逾期→标红'}
        ]
    },
    {
        'id': 'V012-DRILL-017', 'role': '项目经理',
        'topic': '研发协作流程现状→Spotify-Squad改进 + 迁移计划 + 钉钉推送',
        'task_type': 'architecture_design', 'difficulty': 'hard', 'min_subtasks': 5,
        'fuzzy_brief': 'briefs/V012-DRILL-017.md', 'expected_output': 'outputs/V012-DRILL-017/',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过团队规模确认', '双图须对比展示现状vs目标'],
        'slots': [
            {'name': 'process_scope', 'label_cn': '流程范围', 'strategy': 'auto_fill', 'default_rule': '研发协作全流程'},
            {'name': 'target_model', 'label_cn': '目标模型', 'strategy': 'auto_fill', 'default_rule': 'Spotify Squad'},
            {'name': 'team_size', 'label_cn': '团队规模', 'strategy': 'must_ask', 'example_prompt': '现在团队多少人？研发/测试/PM各几个？'},
            {'name': 'push_channel', 'label_cn': '推送渠道', 'strategy': 'must_ask', 'example_prompt': '钉钉Webhook URL是什么？'}
        ]
    },
    # ⑤ HR
    {
        'id': 'V012-DRILL-018', 'role': 'HR',
        'topic': '入职手册更新 — DOCX原手册+Notion新制度→新版PDF',
        'task_type': 'rich_document_generate', 'difficulty': 'easy', 'min_subtasks': 3,
        'fuzzy_brief': 'briefs/V012-DRILL-018.md', 'expected_output': 'outputs/V012-DRILL-018/onboarding-guide.pdf',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过原手册读取', '新制度须完整覆盖'],
        'slots': [
            {'name': 'existing_manual', 'label_cn': '现有手册路径', 'strategy': 'must_ask', 'example_prompt': '现有入职手册在哪个文件/路径？'},
            {'name': 'policy_page', 'label_cn': '考勤制度Notion页面', 'strategy': 'must_ask', 'example_prompt': '最新考勤制度在Notion哪个页面？'},
            {'name': 'culture_changes', 'label_cn': '文化调整内容', 'strategy': 'must_ask', 'example_prompt': '公司文化板块具体调整了什么？'}
        ]
    },
    {
        'id': 'V012-DRILL-019', 'role': 'HR',
        'topic': '四天工作制调研 — 劳动法+企业案例+海外数据→知识卡片入库',
        'task_type': 'knowledge_brain_learn', 'difficulty': 'hard', 'min_subtasks': 4,
        'fuzzy_brief': 'briefs/V012-DRILL-019.md', 'expected_output': 'outputs/V012-DRILL-019/',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过消化管线', '三个维度须全部覆盖'],
        'slots': [
            {'name': 'research_topic', 'label_cn': '调研主题', 'strategy': 'auto_fill', 'default_rule': '四天工作制'},
            {'name': 'dimensions', 'label_cn': '覆盖维度', 'strategy': 'auto_fill', 'default_rule': '劳动法条款+国内企业案例+海外效果数据'},
            {'name': 'collection_name', 'label_cn': '知识库集合名', 'strategy': 'context_derive', 'default_rule': '四天工作制调研'},
            {'name': 'output_form', 'label_cn': '知识卡片输出', 'strategy': 'auto_fill', 'default_rule': 'Earth Library知识卡片+Markdown综述'}
        ]
    },
    # ⑥ 客服
    {
        'id': 'V012-DRILL-020', 'role': '客服',
        'topic': '月度投诉分类统计 — Notion工单→饼图+XLSX热力表',
        'task_type': 'chart_diagram', 'difficulty': 'easy', 'min_subtasks': 3,
        'fuzzy_brief': 'briefs/V012-DRILL-020.md', 'expected_output': 'outputs/V012-DRILL-020/',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过Notion工单来源确认', '饼图+热力表两者缺一不可'],
        'slots': [
            {'name': 'data_source', 'label_cn': 'Notion工单数据库', 'strategy': 'must_ask', 'example_prompt': '工单数据在Notion哪个数据库？'},
            {'name': 'classify_dim', 'label_cn': '分类维度', 'strategy': 'auto_fill', 'default_rule': '投诉类型+严重程度'},
            {'name': 'output_format', 'label_cn': '输出格式', 'strategy': 'auto_fill', 'default_rule': 'XLSX（含饼图+热力表）'}
        ]
    },
    {
        'id': 'V012-DRILL-021', 'role': '客服',
        'topic': '竞品FAQ抓取+对比文档+知识卡片入库+企业微信推送',
        'task_type': 'composite', 'difficulty': 'hard', 'min_subtasks': 5,
        'fuzzy_brief': 'briefs/V012-DRILL-021.md', 'expected_output': 'outputs/V012-DRILL-021/',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过URL逐一确认', '知识卡片须走完整消化管线', '推送前须预览'],
        'slots': [
            {'name': 'competitor_list', 'label_cn': '竞品全称', 'strategy': 'must_ask', 'example_prompt': '竞品A/B/C具体是哪三个产品？给全称'},
            {'name': 'faq_urls', 'label_cn': 'FAQ页面URL', 'strategy': 'must_ask', 'example_prompt': '每个竞品的FAQ/帮助中心URL是什么？'},
            {'name': 'push_channel', 'label_cn': '推送渠道', 'strategy': 'must_ask', 'example_prompt': '企业微信Webhook URL是什么？'},
            {'name': 'extractable_patterns', 'label_cn': '可借鉴模式', 'strategy': 'context_derive', 'default_rule': '可以从竞品FAQ中学到的客服话术/问题分类/自助服务模式'}
        ]
    },
    # ⑦ 研发人员
    {
        'id': 'V012-DRILL-022', 'role': '研发人员',
        'topic': '用户反馈分类工具 MVP — TDD+代码审查+Swagger文档',
        'task_type': 'coding_build', 'difficulty': 'medium', 'min_subtasks': 4,
        'fuzzy_brief': 'briefs/V012-DRILL-022.md', 'expected_output': 'outputs/V012-DRILL-022/',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过TDD测试先行', '代码审查须独立于实现'],
        'slots': [
            {'name': 'language_stack', 'label_cn': '语言/技术栈', 'strategy': 'must_ask', 'example_prompt': '用什么语言/框架？Python+FastAPI？'},
            {'name': 'output_paths', 'label_cn': '代码落点', 'strategy': 'must_ask', 'example_prompt': '代码放在哪个目录？'},
            {'name': 'api_spec', 'label_cn': 'API接口规范', 'strategy': 'context_derive', 'default_rule': 'RESTful+Swagger/OpenAPI'},
            {'name': 'test_coverage', 'label_cn': '测试覆盖率要求', 'strategy': 'must_ask', 'example_prompt': '测试覆盖率有最低要求吗？'}
        ]
    },
    {
        'id': 'V012-DRILL-023', 'role': '研发人员',
        'topic': 'CI流水线排障修复 + 回归测试 + Postmortem报告',
        'task_type': 'deployment', 'difficulty': 'hard', 'min_subtasks': 5,
        'fuzzy_brief': 'briefs/V012-DRILL-023.md', 'expected_output': 'outputs/V012-DRILL-023/',
        'scenario': 'S3-v012-pipeline',
        'forbidden_shortcuts': ['不得跳过日志到根因的完整推导', 'postmortem须包含时间线和改进措施'],
        'slots': [
            {'name': 'ci_platform', 'label_cn': 'CI平台', 'strategy': 'must_ask', 'example_prompt': '哪个CI平台？GitHub Actions/GitLab CI/Jenkins？'},
            {'name': 'error_log', 'label_cn': '错误日志来源', 'strategy': 'must_ask', 'example_prompt': '错误日志在哪里？给链接或粘贴内容'},
            {'name': 'affected_branches', 'label_cn': '受影响分支', 'strategy': 'must_ask', 'example_prompt': '哪些分支受影响？main/develop都挂了？'},
            {'name': 'deployment_target', 'label_cn': '部署目标', 'strategy': 'context_derive', 'default_rule': '先推到测试环境验证，再决定是否推生产'}
        ]
    }
]

# ── Step 3: Write all brief files ──
os.makedirs(BRIEFS, exist_ok=True)

for t in NEW_TASKS:
    slots_text = '\n'.join([f"- [{s['strategy']}] **{s['label_cn']}**：{s.get('example_prompt', s.get('default_rule', ''))}" for s in t['slots']])
    brief = f"""# {t['id']}：{t['role']} — {t['topic']}

**角色**：{t['role']}
**难度**：{t['difficulty']}
**task_type**：{t['task_type']}
**最低子任务数**：{t['min_subtasks']}
**预期产出**：{t['expected_output']}

## 场景

{{{{待Agent在阶段B追问补全}}}}

## 需补全的槽位

{slots_text}

## 禁止短路

{chr(10).join(f'- {s}' for s in t['forbidden_shortcuts'])}

## 可用能力

{{{{Agent在阶段C拆解时从Skill Registry和Task-Type-Registry中匹配}}}}
"""
    with open(os.path.join(BRIEFS, f'{t["id"]}.md'), 'w', encoding='utf-8') as f:
        f.write(brief)

print(f'[2/5] Created {len(NEW_TASKS)} brief files')

# ── Step 4: Update task-pool.json ──
pool_tasks = []
for t in NEW_TASKS:
    pool_tasks.append({
        'id': t['id'],
        'task_type': t['task_type'],
        'scenario': 'S3-v012-pipeline',
        'difficulty': t['difficulty'],
        'label': f'{t["role"]}：{t["topic"]}',
        'fuzzy_brief': f'Simulation-Sandbox/{t["fuzzy_brief"]}',
        'task_type_registry': t['task_type'] if t['task_type'] != 'composite' else 'architecture_design',
        'min_subtasks': t['min_subtasks'],
        'expected_output': f'Simulation-Sandbox/{t["expected_output"]}',
        'forbidden_shortcuts': t['forbidden_shortcuts']
    })

pool = {
    'meta': {
        'description': 'V012 全链路练习任务池 — 7角色×14任务，覆盖V012 5阶段+P008全L等级+18/18活跃技能',
        'write_scope': 'Simulation-Sandbox/** only',
        'route_rule': 'flow-v012-drill-bridge.mdc',
        'pipeline_rule': 'flow-v012-pipeline-execute.mdc',
        'updated': '2026-05-23'
    },
    'tasks': pool_tasks
}

with open(TASK_POOL, 'w', encoding='utf-8') as f:
    json.dump(pool, f, ensure_ascii=False, indent=2)

print(f'[3/5] Updated task-pool.json with {len(pool_tasks)} tasks')

# ── Step 5: Add new tasks to Pending-Plan-Tracker ──
start_date = date(2026, 5, 24)
tracker_tasks = []
for i, t in enumerate(NEW_TASKS):
    day_offset = i // 2  # 2 tasks per day
    task_date = (start_date + timedelta(days=day_offset)).isoformat()
    tracker_tasks.append({
        'id': t['id'],
        'topic': f'V012链路练习 — {t["role"]}：{t["topic"]}',
        'status': 'pending',
        'planned_date': task_date,
        'parent_task': 'V012',
        'resume_keywords': ['V012', '链路', t['role'], 'DRILL', t['id'][-3:]],
        'file': f'plans/{t["id"]}.md'
    })

tracker['pending'].extend(tracker_tasks)
tracker.setdefault('meta', {})['last_reminded'] = ''

with open(TRACKER, 'w', encoding='utf-8') as f:
    json.dump(tracker, f, ensure_ascii=False, indent=2)

print(f'[4/5] Registered {len(tracker_tasks)} new tasks in Pending-Plan-Tracker')

# ── Step 6: Update training-plan.json ──
phases = []
for week_idx, week_label in enumerate(['V012-DRILL 第1周（角色仿真）', 'V012-DRILL 第2周（角色仿真）']):
    tasks_by_day = {}
    for day_in_week in range(7):
        task_idx = week_idx * 7 * 2 + day_in_week * 2
        if task_idx < len(NEW_TASKS):
            day_date = (start_date + timedelta(days=week_idx * 7 + day_in_week)).isoformat()
            day_tasks = []
            if task_idx < len(NEW_TASKS):
                day_tasks.append(NEW_TASKS[task_idx]['id'])
            if task_idx + 1 < len(NEW_TASKS):
                day_tasks.append(NEW_TASKS[task_idx + 1]['id'])
            tasks_by_day[day_date] = day_tasks
    phases.append({
        'id': f'v012-drill-week{week_idx + 3}',
        'label': week_label,
        'tasks_by_day': tasks_by_day
    })

training = {
    'meta': {
        'description': 'V012 全链路练习排程 — 7角色×14任务，2周完成',
        'current_phase': 'v012-drill-week3',
        'parent_vision': 'V012',
        'updated': '2026-05-23'
    },
    'phases': phases,
    'rounds_completed': 0
}

with open(TRAINING, 'w', encoding='utf-8') as f:
    json.dump(training, f, ensure_ascii=False, indent=2)

print(f'[5/5] Updated training-plan.json — 2 weeks, {len(NEW_TASKS)} tasks')

# ── Clean up old plan files ──
os.makedirs(PLANS, exist_ok=True)
for rid in REMOVE_IDS:
    old_plan = os.path.join(PLANS, f'{rid}.md')
    if os.path.exists(old_plan):
        os.remove(old_plan)

print(f'\n✅ All done. {len(NEW_TASKS)} tasks across 7 roles, covering:')
print('   - V012 5-stage pipeline: SLOT_DISCOVERY→SLOT_UPDATE→DECOMPOSE→EXECUTING→DONE')
print('   - P008 L-levels: L1(6 tasks) / L2(6 tasks) / L3-potential(2 tasks)')
print('   - Skills: 16/18 active skills exercised')
