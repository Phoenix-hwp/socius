import json, os

base = r'd:\Phoenix\cursor-knowledge'
files = [
    'Simulation-Sandbox/scenarios.json',
    'Simulation-Sandbox/task-pool.json',
    'Simulation-Sandbox/training-plan.json',
    'Simulation-Sandbox/scenario-S2-1-boundary-test.json'
]
for f in files:
    try:
        with open(os.path.join(base, f), 'r', encoding='utf-8') as fh:
            d = json.load(fh)
        print(f'{f}: OK')
    except Exception as e:
        print(f'{f}: {e}')

tp = json.load(open(os.path.join(base, 'Simulation-Sandbox/task-pool.json'), 'r', encoding='utf-8'))
new_tasks = ['TG-019','TG-020','TG-021','TG-022','TG-023','TG-024','TG-025','TG-026']
found = [t['id'] for t in tp['tasks'] if t['id'] in new_tasks]
print(f'Tasks: {len(found)}/8 -> {found}')

sc = json.load(open(os.path.join(base, 'Simulation-Sandbox/scenarios.json'), 'r', encoding='utf-8'))
new_sc = ['S2-psychology-boundary','S2-lollapalooza-detector','S2-dual-track-ask','S2-full-chain-layered']
found_sc = [s['id'] for s in sc['scenarios'] if s['id'] in new_sc]
print(f'Scenarios: {len(found_sc)}/4 -> {found_sc}')

tr = json.load(open(os.path.join(base, 'Simulation-Sandbox/training-plan.json'), 'r', encoding='utf-8'))
p4 = tr['phases'].get('phase_4_layered', {})
print(f'Phase 4 days: {len(p4.get("schedule", []))}')
print(f'Phases: {list(tr["phases"].keys())}')
