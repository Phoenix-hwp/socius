#!/usr/bin/env python3
"""todo-reminder — Pending-Plan-Tracker scan & update (decoupled from AskQuestion)"""
import sys, os, json, datetime, subprocess

TRACKER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    '10-Topics', 'Pending-Plan-Tracker.json'
)
SANDBOX_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'Simulation-Sandbox'
)
TASK_POOL_PATH = os.path.join(SANDBOX_ROOT, 'task-pool.json')
SUMMARY_LOG_DIR = os.path.join(SANDBOX_ROOT, 'logs')
VALIDATE_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'v012-drill-validate.py'
)

def is_v012_drill_id(item_id):
    return isinstance(item_id, str) and item_id.startswith('V012-DRILL-')

def is_tep_sim_id(item_id):
    """Deprecated — TEP-SIM 已清理，保留兼容检测"""
    return isinstance(item_id, str) and item_id.startswith('TEP-SIM-')

def load_task_pool():
    if not os.path.isfile(TASK_POOL_PATH):
        return {'tasks': []}
    with open(TASK_POOL_PATH, 'r', encoding='utf-8-sig') as f:
        return json.load(f)

def find_task_pool_entry(item_id):
    pool = load_task_pool()
    for t in pool.get('tasks', []):
        if t.get('id') == item_id:
            return t
    return None

def v012_drill_validate(item_id):
    if not os.path.isfile(VALIDATE_SCRIPT):
        return {'valid': False, 'errors': ['validate_script_missing']}
    proc = subprocess.run(
        [sys.executable, VALIDATE_SCRIPT, item_id],
        capture_output=True, text=True, encoding='utf-8'
    )
    try:
        return json.loads(proc.stdout.strip() or '{}')
    except json.JSONDecodeError:
        return {'valid': False, 'errors': [proc.stderr.strip() or 'validate_failed']}

def v012_drill_info(item_id):
    if not is_v012_drill_id(item_id):
        print(json.dumps({'is_v012_drill': False, 'id': item_id}, ensure_ascii=False))
        return
    entry = find_task_pool_entry(item_id)
    validation = v012_drill_validate(item_id) if entry else {'valid': False, 'errors': ['no_task_pool_entry']}
    print(json.dumps({
        'is_v012_drill': True,
        'id': item_id,
        'route': 'flow-v012-drill-bridge.mdc',
        'pipeline_rule': 'flow-v012-pipeline-execute.mdc',
        'task_pool_hit': entry is not None,
        'task_type': (entry or {}).get('task_type'),
        'fuzzy_brief': (entry or {}).get('fuzzy_brief'),
        'min_subtasks': (entry or {}).get('min_subtasks'),
        'can_mark_done': validation.get('valid', False),
        'validation_errors': validation.get('errors', []),
    }, ensure_ascii=False))

def load():
    with open(TRACKER_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save(data):
    with open(TRACKER_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def today_str():
    return datetime.date.today().isoformat()

def scan(force=False):
    data = load()
    today = today_str()
    last = data.get('meta', {}).get('last_reminded', '')
    if last == today and not force:
        print(json.dumps({'skipped': True, 'last_reminded': today}, ensure_ascii=False))
        return
    pending = [p for p in data.get('pending', []) if p.get('status') != 'cancelled']
    overdue, upcoming, in_progress_today = [], [], []
    for p in pending:
        pd = p.get('planned_date', '')
        status = p.get('status', 'pending')
        try:
            days = (datetime.date.fromisoformat(pd) - datetime.date.today()).days
        except Exception:
            days = 999
        drill = is_v012_drill_id(p['id'])
        item = {
            'id': p['id'], 'topic': p.get('topic', ''), 'planned_date': pd,
            'days_until': days, 'status': status,
            'next_action': p.get('next_action', '')[:120],
            'has_memo': 'source_memo' in p and (p.get('source_memo') or {}).get('path', ''),
            'memo_path': (p.get('source_memo') or {}).get('path', ''),
            'is_v012_drill': drill,
            'is_tep_sim': is_tep_sim_id(p['id']),
        }
        if status == 'in_progress' and days <= 0:
            in_progress_today.append(item)
        elif status == 'pending':
            if days <= 0:
                overdue.append(item)
            elif 0 < days <= 3:
                upcoming.append(item)
    print(json.dumps({
        'skipped': False, 'today': today,
        'overdue': overdue, 'upcoming': upcoming, 'in_progress': in_progress_today,
        'total_pending': len(pending),
    }, ensure_ascii=False))

def mark_done(item_id):
    if is_tep_sim_id(item_id):
        print(json.dumps({
            'done': False, 'id': item_id,
            'error': 'tep_sim_deprecated',
            'hint': 'TEP-SIM 已清理，请使用 V012-DRILL-* 练习',
        }, ensure_ascii=False))
        return
    if is_v012_drill_id(item_id):
        validation = v012_drill_validate(item_id)
        if not validation.get('valid'):
            print(json.dumps({
                'done': False, 'id': item_id,
                'error': 'v012_pipeline_validation_failed',
                'hint': '须完成 V012 全链路并运行 v012-drill-validate.py',
                'route': 'flow-v012-pipeline-execute.mdc',
                'validation_errors': validation.get('errors', []),
            }, ensure_ascii=False))
            return
    data = load()
    for p in data.get('pending', []):
        if p['id'] == item_id:
            p['status'] = 'completed'
            p['completed_date'] = today_str()
            data.setdefault('archive', []).append(p)
            data['pending'] = [x for x in data['pending'] if x['id'] != item_id]
            save(data)
            print(json.dumps({'done': True, 'id': item_id}, ensure_ascii=False))
            return
    print(json.dumps({'done': False, 'id': item_id, 'error': 'not found'}, ensure_ascii=False))

def postpone(item_id, new_date):
    data = load()
    for p in data.get('pending', []):
        if p['id'] == item_id:
            p['planned_date'] = new_date
            save(data)
            print(json.dumps({'done': True, 'id': item_id, 'new_date': new_date}, ensure_ascii=False))
            return
    print(json.dumps({'done': False, 'id': item_id, 'error': 'not found'}, ensure_ascii=False))

def mark_start(item_id):
    data = load()
    for p in data.get('pending', []):
        if p['id'] == item_id:
            p['status'] = 'in_progress'
            save(data)
            print(json.dumps({'done': True, 'id': item_id, 'status': 'in_progress'}, ensure_ascii=False))
            return
    print(json.dumps({'done': False, 'id': item_id, 'error': 'not found'}, ensure_ascii=False))

def set_reminded():
    data = load()
    data.setdefault('meta', {})['last_reminded'] = today_str()
    save(data)
    print(json.dumps({'done': True, 'last_reminded': today_str()}, ensure_ascii=False))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    args = sys.argv[1:]
    if '--scan' in args:
        scan(force='--skip-daily-check' in args)
    elif '--mark-done' in args and len(args) >= 2:
        mark_done(args[args.index('--mark-done') + 1])
    elif '--postpone' in args and len(args) >= 3:
        idx = args.index('--postpone')
        postpone(args[idx + 1], args[idx + 2])
    elif '--start' in args and len(args) >= 2:
        mark_start(args[args.index('--start') + 1])
    elif '--set-reminded' in args:
        set_reminded()
    elif '--v012-drill-info' in args and len(args) >= 2:
        v012_drill_info(args[args.index('--v012-drill-info') + 1])
    elif '--tep-sim-info' in args and len(args) >= 2:
        i = args[args.index('--tep-sim-info') + 1]
        print(json.dumps({'deprecated': True, 'hint': 'use --v012-drill-info', 'id': i}, ensure_ascii=False))
    elif '--raw' in args:
        print(json.dumps(load(), ensure_ascii=False, indent=2))
    else:
        print('Usage: todo-reminder.py --scan | --mark-done ID | --postpone ID DATE | --start ID | --set-reminded | --v012-drill-info ID | --raw')
