#!/usr/bin/env python3
"""todo-reminder — Pending-Plan-Tracker scan & update (decoupled from AskQuestion)"""
import sys, os, json, datetime

TRACKER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    '10-Topics', 'Pending-Plan-Tracker.json'
)

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
        except:
            days = 999
        item = {
            'id': p['id'], 'topic': p.get('topic', ''), 'planned_date': pd,
            'days_until': days, 'status': status,
            'next_action': p.get('next_action', '')[:120],
            'has_memo': 'source_memo' in p and bool(p.get('source_memo', {}).get('path')),
            'memo_path': (p.get('source_memo', {}) or {}).get('path', ''),
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
    elif '--raw' in args:
        print(json.dumps(load(), ensure_ascii=False, indent=2))
    else:
        print('Usage: todo-reminder.py --scan | --mark-done ID | --postpone ID DATE | --start ID | --set-reminded | --raw')
