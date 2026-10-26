# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import subprocess
import sys

import yaml

if sys.platform != 'darwin':
    raise SystemExit('This native rendering test requires macOS.')

repo = Path(__file__).resolve().parents[1]
theme = yaml.safe_load((repo / 'themes/squirrel.yaml').read_text(encoding='utf-8'))
subprocess.run(['swift', str(repo / 'tests/macos_emoji.swift'),
                theme['patch']['style']['candidate_format']], check=True)
