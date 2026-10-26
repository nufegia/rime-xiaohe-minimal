#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare a selected prefix's remaining code with an independent code query."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--probe', type=Path, required=True)
p.add_argument('--shared-data', type=Path, required=True)
p.add_argument('--work-dir', type=Path, required=True)
args = p.parse_args()
work = args.work_dir.resolve()
work.mkdir(parents=True, exist_ok=True)
if any(work.iterdir()):
    raise SystemExit('Use an empty work directory')


def run(root, commands, deploy=False):
    result = subprocess.run([str(args.probe.resolve()), str(root), str(args.shared_data.resolve())]
                            + (['--deploy'] if deploy else []), input='\n'.join(commands)+'\n',
                            capture_output=True, text=True, encoding='utf-8', check=True)
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    assert len(rows) == len(commands), result.stderr
    return rows


def words(row):
    return [candidate['text'] for candidate in row['candidates']]


reports = []
for frontend in ('macos', 'windows', 'fcitx5', 'ibus'):
    root = work / frontend
    subprocess.run([sys.executable, str(REPO/'scripts/manage.py'), 'install',
                    '--platform', frontend, '--user-dir', str(root)], check=True,
                   capture_output=True)
    run(root, ['keys\t'], deploy=True)
    cases = 0
    for flag, expected in [('0', '没'), ('1', '沒')]:
        mode = 'traditional\t'+flag
        baseline = run(root, [mode, 'keys\tm', 'step\t{Tab}',
                              'keys\tmw', 'keys\tmwd', 'keys\tmwdy'])
        rows = run(root, [mode, 'keys\tqrdzm', 'step\t ', 'step\t{Tab}',
                         'step\t{Shift+Tab}', 'step\t '])
        assert words(rows[1])[0] == '全都'
        assert rows[2]['preedit'] == '全都m' and words(rows[2]) == words(baseline[1]), rows[2]
        assert words(rows[3]) == words(baseline[2]) and rows[3]['logical_page'] == '1'
        assert words(rows[4]) == words(baseline[1]) and rows[4]['logical_page'] == '0'
        assert rows[5]['commit'] == '全都'+expected
        cases += 5
        for sequence, committed in [('qrdzm11', '全都'+expected),
                                    ('qrdzm1;', '全都'+words(baseline[1])[1]),
                                    ("qrdzm1'", '全都'+words(baseline[1])[2]),
                                    ('qrdzm1{Tab}0', '全都'+words(baseline[2])[9]),
                                    ('qrdzm1{Down} ', '全都'+words(baseline[1])[1]),
                                    ('qrdzm1wdy ', '全都'+expected),
                                    ('qrdzm1{Escape}m ', '全都'+expected)]:
            result = run(root, [mode, 'keys\t'+sequence])[-1]
            assert result['commit'] == committed, result
            assert '\u200b' not in result['commit']
            cases += 1
        continued = run(root, [mode, 'keys\tqrdzm1', 'step\tw', 'step\td', 'step\ty', 'step\t '])
        for row, reference in zip(continued[2:5], baseline[3:6]):
            assert words(row) == words(reference), (row, reference)
            cases += 1
        assert continued[-1]['commit'] == '全都'+expected
        cases += 1
    assert not (root/'loginput_xiaohe_smart.userdb').exists()
    reports.append({'platform': frontend, 'checks': cases, 'failures': 0,
                    'native_frontend_ui_verified': False,
                    'simplified_and_traditional': True,
                    'residual_code_matches_independent_query': True})
(work/'report.json').write_text(json.dumps(reports, indent=2)+'\n', encoding='utf-8')
print(json.dumps(reports, indent=2))
