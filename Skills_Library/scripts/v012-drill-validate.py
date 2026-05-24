#!/usr/bin/env python3
"""v012-drill-validate — V012-DRILL pipeline artifact gate before mark-done"""
import sys, os, json

ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'Simulation-Sandbox'
)
SCHEMA_PATH = os.path.join(ROOT, 'v012-runtime-schema.json')
TASK_POOL_PATH = os.path.join(ROOT, 'task-pool.json')


def load_json(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def load_jsonl(path):
    rows = []
    with open(path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def find_task(drill_id):
    pool = load_json(TASK_POOL_PATH)
    for t in pool.get('tasks', []):
        if t.get('id') == drill_id:
            return t
    return None


def validate(drill_id):
    errors = []
    schema = load_json(SCHEMA_PATH)
    audit_cfg = schema.get('summary_pipeline_audit', {})
    min_subtasks = audit_cfg.get('min_subtasks', 3)
    min_steps = audit_cfg.get('min_workflow_steps', 3)

    task = find_task(drill_id)
    if task:
        min_subtasks = max(min_subtasks, task.get('min_subtasks', min_subtasks))

    state_dir = os.path.join(ROOT, 'state', drill_id)
    logs_dir = os.path.join(ROOT, 'logs', drill_id)
    summary_path = os.path.join(ROOT, 'logs', f'summary-{drill_id}.json')

    paths = {
        'tep_state': os.path.join(state_dir, 'tep-state.json'),
        'slots': os.path.join(state_dir, 'slots.json'),
        'tracker': os.path.join(state_dir, 'active-task-tracker.json'),
        'decomposition': os.path.join(logs_dir, 'decomposition-log.jsonl'),
        'workflow': os.path.join(logs_dir, 'workflow-steps.jsonl'),
        'load_check': os.path.join(logs_dir, 'load-check.json'),
        'summary': summary_path,
    }
    for name, p in paths.items():
        if not os.path.isfile(p):
            errors.append(f'missing:{name}:{p}')

    if errors:
        return {'valid': False, 'id': drill_id, 'errors': errors}

    tep = load_json(paths['tep_state'])
    history_states = [h.get('state') for h in tep.get('history', [])]
    history_states.append(tep.get('current_state'))
    for req in audit_cfg.get('required_tep_states', []):
        if req not in history_states:
            errors.append(f'tep_state_missing:{req}')

    slots = load_json(paths['slots'])
    unfilled = [s for s in slots.get('slots', []) if s.get('status') != 'filled']
    if unfilled:
        errors.append(f'slots_unfilled:{len(unfilled)}')

    tracker = load_json(paths['tracker'])
    children = []
    for item in tracker.get('active', []):
        children.extend(item.get('children') or [])
    if len(children) < min_subtasks:
        errors.append(f'subtasks_insufficient:{len(children)}<{min_subtasks}')

    steps = load_jsonl(paths['workflow'])
    verified = [s for s in steps if s.get('verified')]
    if len(verified) < min_steps:
        errors.append(f'workflow_steps_insufficient:{len(verified)}<{min_steps}')

    summary = load_json(paths['summary'])
    pa = summary.get('pipeline_audit') or {}
    for step in audit_cfg.get('required_tip_steps', []):
        if step not in (pa.get('tip_steps') or []):
            errors.append(f'tip_step_missing:{step}')
    if summary.get('result') not in ('success', 'partial_success'):
        errors.append('summary_result_invalid')

    return {
        'valid': len(errors) == 0,
        'id': drill_id,
        'errors': errors,
        'checks_passed': len(errors) == 0,
    }


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 2:
        print('Usage: v012-drill-validate.py <V012-DRILL-ID>')
        sys.exit(1)
    result = validate(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['valid'] else 1)
