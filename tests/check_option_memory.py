#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test native-menu choice across schema switches, session recreation and restart."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--probe', type=Path, required=True)
parser.add_argument('--shared-data', type=Path, required=True)
parser.add_argument('--work-dir', type=Path, required=True)
args = parser.parse_args()
work = args.work_dir.resolve()
work.mkdir(parents=True, exist_ok=True)
if any(work.iterdir()):
    raise SystemExit('Use an empty work directory')


def run(root, commands, deploy=False):
    result = subprocess.run([str(args.probe.resolve()), str(root), str(args.shared_data.resolve())]
                            + (['--deploy'] if deploy else []),
                            input='\n'.join(commands)+'\n', capture_output=True,
                            text=True, encoding='utf-8', check=True)
    return [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]


report = []
for platform in ('macos', 'windows', 'fcitx5', 'ibus'):
    root = work / platform
    subprocess.run([sys.executable, str(REPO/'scripts/manage.py'), 'install',
                    '--platform', platform, '--user-dir', str(root)], check=True,
                   capture_output=True)
    run(root, [], deploy=True)
    subprocess.run([sys.executable, str(REPO/'scripts/manage.py'), 'doctor',
                    '--platform', platform, '--user-dir', str(root)], check=True,
                   capture_output=True)
    checks = 0
    for current, target in [('简体', True), ('繁體', False)]:
        menu = run(root, ['keys\t{Control+grave}', 'step\t2'])
        index = next(i for i, candidate in enumerate(menu[-1]['candidates'])
                     if candidate['text'] == current)
        commands = ['keys\t{Control+grave}', 'step\t2', 'step\t'+str((index+1)%10),
                    'keys\thjyu ', 'schema\tluna_pinyin', 'schema\tloginput_xiaohe',
                    'keys\thjyu ', 'recreate\t', 'keys\thjyu ']
        results = run(root, commands)
        word = '漢語' if target else '汉语'
        for i in (3, 6, 8):
            assert results[i]['traditional'] is target and results[i]['commit'] == word, results[i]
            checks += 1
        # A separate probe process reads the persisted user configuration.
        restarted = run(root, ['keys\thjyu '])[0]
        assert restarted['traditional'] is target and restarted['commit'] == word, restarted
        checks += 1
    report.append({'platform': platform, 'checks': checks, 'failures': 0,
                   'native_frontend_ui_verified': False,
                   'schema_switch_session_recreation_process_restart': True})
(work/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report, indent=2))
