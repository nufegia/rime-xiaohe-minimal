#!/usr/bin/env python3
"""Local, reversible installation. No uploads or network downloads."""
# SPDX-License-Identifier: GPL-3.0-or-later
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
from datetime import datetime, timezone

import yaml

REPO = Path(__file__).resolve().parents[1]
SCHEMA = 'loginput_xiaohe'
TABLE = SCHEMA + '_fixed.dict.yaml'


def read_yaml(path):
    value = yaml.safe_load(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f'Expected a YAML mapping: {path}')
    return value


def dump(value):
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False).encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build_table(source):
    """Convert text TAB code [TAB weight] to source-order-preserving Rime data.

    Existing compatible Rime YAML is copied verbatim; its weights are preserved.
    The caller supplies and retains responsibility for the source's permission.
    """
    text = source.read_text(encoding='utf-8-sig')
    lines = text.splitlines()
    if any(line.strip() == '---' for line in lines):
        if '\n...\n' not in text.replace('\r\n', '\n'):
            raise ValueError('Rime dictionary must contain a YAML header and ... separator')
        normalized = text.replace('\r\n', '\n')
        header, data = normalized.split('\n...\n', 1)
        meta = yaml.safe_load(header)
        if meta.get('name') != SCHEMA + '_fixed':
            raise ValueError('Rime dictionary name must be loginput_xiaohe_fixed')
        if meta.get('import_tables'):
            raise ValueError('Split dictionaries are not imported automatically; provide a standalone table')
        columns = meta.get('columns', ['text', 'code', 'weight'])
        if 'text' not in columns or 'code' not in columns:
            raise ValueError('Dictionary requires text and code columns')
        count = 0
        for line in data.splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 2 or not re.fullmatch('[a-z]+', parts[columns.index('code')]):
                raise ValueError(f'Unsupported dictionary row {count + 1}')
            count += 1
        if not count:
            raise ValueError('Empty dictionary')
        return normalized.encode('utf-8'), count
    rows = []
    per_code = {}
    for number, line in enumerate(lines, 1):
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) not in (2, 3) or not parts[0] or not re.fullmatch('[a-z]+', parts[1]):
            raise ValueError(f'Line {number}: expected text TAB lowercase-code [TAB weight]')
        word, code = parts[:2]
        if word.startswith('@date:'):
            raise ValueError('Date templates belong in the custom phrase file, not the fixed table')
        rank = per_code.get(code, 0)
        per_code[code] = rank + 1
        if rank >= 999999:
            raise ValueError('Too many candidates for one code')
        rows.append(f'{word}\t{code}\t{999999-rank}\n')
    if not rows:
        raise ValueError('Empty code table')
    header = {'name': SCHEMA + '_fixed', 'version': 'local', 'sort': 'by_weight',
              'use_preset_vocabulary': False, 'columns': ['text', 'code', 'weight']}
    return ('# Generated locally from a user-provided table. Not covered by the repository license.\n---\n'
            + yaml.safe_dump(header, allow_unicode=True, sort_keys=False)
            + '...\n' + ''.join(rows)).encode('utf-8'), len(rows)


def frontend_name(requested):
    if requested:
        return requested
    current = platform.system()
    if current == 'Darwin':
        return 'macos'
    if current == 'Windows':
        return 'windows'
    raise ValueError('Use --platform macos or windows for staging on another platform')


def default_user_dir(frontend):
    if frontend == 'macos':
        return Path.home() / 'Library/Rime'
    if 'APPDATA' not in os.environ:
        raise ValueError('APPDATA is unavailable; pass --user-dir explicitly')
    # Custom Weasel paths must be passed explicitly after checking the user folder.
    return Path(os.environ['APPDATA']) / 'Rime'


def merged_schema_list(doc):
    patch = doc.setdefault('patch', {})
    if not isinstance(patch, dict):
        raise ValueError('default.custom.yaml patch must be a mapping')
    for key in ('schema_list', 'schema_list/+', 'schema_list/@next'):
        existing = patch.get(key, [])
        values = existing if isinstance(existing, list) else [existing]
        if any(isinstance(item, dict) and item.get('schema') == SCHEMA for item in values):
            return doc
    addition = patch.setdefault('schema_list/+', [])
    if not isinstance(addition, list):
        raise ValueError('schema_list/+ must be a list; merge this custom configuration manually')
    addition.append({'schema': SCHEMA})
    return doc


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.xiaohe-tmp')
    temporary.write_bytes(data)
    temporary.replace(path)


def install(args):
    frontend = frontend_name(args.platform)
    root = (args.user_dir or default_user_dir(frontend)).expanduser().resolve()
    if args.table and args.phonetic_only:
        raise ValueError('--table and --phonetic-only are mutually exclusive')
    table_data = None
    count = 0
    existing = root / TABLE
    if args.table:
        table_data, count = build_table(args.table.expanduser().resolve())
    elif existing.exists() and not args.phonetic_only:
        # Validate before using a pre-existing table; do not overwrite it.
        _, count = build_table(existing)
    elif not args.phonetic_only:
        table_data, count = build_table(REPO / 'rime' / TABLE)
    schema = read_yaml(REPO / 'rime' / (SCHEMA + '.schema.yaml'))
    mix = (REPO / 'rime/lua/loginput_mix.lua').read_text(encoding='utf-8')
    files = {}
    if args.phonetic_only:
        schema['schema']['description'] = '小鹤双拼整句；未导入音形码表；不学习、不调频。'
        schema['schema'].pop('dependencies', None)
        mix = mix.replace("env.fixed = Component.Translator(env.engine, '', 'table_translator@fixed')", 'env.fixed = nil')
        mix = mix.replace('if #input <= 4 and input:match', 'if env.fixed and #input <= 4 and input:match')
    files[SCHEMA + '.schema.yaml'] = dump(schema)
    files['lua/loginput_mix.lua'] = mix.encode('utf-8')
    files['lua/loginput_keys.lua'] = (REPO / 'rime/lua/loginput_keys.lua').read_bytes()
    if frontend == 'macos':
        for name in ('xiaohe_pager_keys.lua', 'xiaohe_pager_filter.lua'):
            files['lua/' + name] = (REPO / 'rime/lua' / name).read_bytes()
    if not args.phonetic_only:
        files[SCHEMA + '_fixed.schema.yaml'] = (REPO / 'rime' / (SCHEMA + '_fixed.schema.yaml')).read_bytes()
        if table_data is not None:
            files[TABLE] = table_data
    # Preserve existing personal phrases. Rime stabledb reads this file without auto-learning.
    if not (root / (SCHEMA + '_custom.txt')).exists():
        files[SCHEMA + '_custom.txt'] = (REPO / 'rime' / (SCHEMA + '_custom.txt')).read_bytes()
    else:
        phrase_text = (root / (SCHEMA + '_custom.txt')).read_text(encoding='utf-8-sig')
        if not all(t in phrase_text for t in ['@date:#yyyy#MM#dd\top', '@date:#yyyy-#MM-#dd\top', '@date:#yyyy.#MM.#dd\top', '@date:#yyyy-#MM-#dd #HH:#mm\top', '@date:#yyyy年#MM月#dd日#HH时#mm分\top']):
            raise ValueError('Existing custom phrase file lacks the standard date templates; merge it manually first to preserve personal op bindings')
    theme = read_yaml(REPO / 'themes' / ('squirrel.yaml' if frontend == 'macos' else 'weasel.yaml'))
    custom = read_yaml(root / (SCHEMA + '.custom.yaml'))
    patch = custom.setdefault('patch', {})
    if not isinstance(patch, dict):
        raise ValueError('Schema custom patch must be a mapping')
    # Platform theme is intentionally replaced; unrelated input customizations survive.
    for key, value in theme['patch'].items():
        if key == 'menu':
            patch.setdefault('menu', {}).update(value)
        else:
            patch[key] = value
    # Refuse custom settings that could silently re-enable learning.
    for key in patch:
        if key == 'translator' or key.startswith('translator/') or key in ('engine', 'engine/translators'):
            raise ValueError(f'Existing custom override {key!r} requires manual review before installing the no-learning schema')
    files[SCHEMA + '.custom.yaml'] = dump(custom)
    files['default.custom.yaml'] = dump(merged_schema_list(read_yaml(root / 'default.custom.yaml')))
    summary = {'platform': frontend, 'user_dir': str(root), 'mode': 'phonetic-only' if args.phonetic_only else 'fixed+phonetic',
               'table_rows': count, 'files': list(files), 'learning': False, 'reload_required': True}
    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    root.mkdir(parents=True, exist_ok=True)
    backup = root / '.xiaohe-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup.mkdir(parents=True, mode=0o700)
    manifest = {'version': 1, 'user_dir': str(root), 'files': {}}
    for relative, data in files.items():
        path = root / relative
        before = path.read_bytes() if path.exists() else None
        if path.is_symlink():
            raise ValueError(f'Refusing to overwrite a symlink: {path}')
        if before is not None:
            saved = backup / 'files' / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(before)
        manifest['files'][relative] = {'existed': before is not None, 'after_sha256': digest(data)}
    # Save recovery information before the first configuration write.
    atomic_write(backup / 'manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8'))
    written = []
    try:
        for relative, data in files.items():
            atomic_write(root / relative, data)
            written.append(relative)
    except Exception:
        for relative in reversed(written):
            if manifest['files'][relative]['existed']:
                atomic_write(root / relative, (backup / 'files' / relative).read_bytes())
            else:
                (root / relative).unlink(missing_ok=True)
        raise
    summary['backup'] = str(backup)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('Now redeploy Rime. macOS: Squirrel --reload. Windows: tray menu > 重新部署.')
    print('Existing learning databases were not deleted; this schema disables their use.')


def restore(args):
    backup = args.backup.expanduser().resolve()
    manifest = json.loads((backup / 'manifest.json').read_text(encoding='utf-8'))
    root = Path(manifest['user_dir']).resolve()
    conflicts = []
    for relative, item in manifest['files'].items():
        p = Path(relative)
        if p.is_absolute() or '..' in p.parts:
            raise ValueError('Unsafe backup manifest path')
        path = root / p
        if path.is_symlink():
            raise ValueError(f'Refusing to restore over a symlink: {path}')
        if not path.exists() or digest(path.read_bytes()) != item['after_sha256']:
            conflicts.append(relative)
    if conflicts:
        raise ValueError('Files changed after installation; merge manually instead of overwriting: ' + ', '.join(conflicts))
    for relative, item in manifest['files'].items():
        if item['existed']:
            atomic_write(root / relative, (backup / 'files' / relative).read_bytes())
        else:
            (root / relative).unlink()
    print('Configuration restored. Redeploy Rime. Learning databases and personal data were not modified.')


def doctor(args):
    frontend = frontend_name(args.platform)
    root = (args.user_dir or default_user_dir(frontend)).expanduser().resolve()
    path = root / 'build' / (SCHEMA + '.schema.yaml')
    if not path.exists():
        raise ValueError('Compiled schema missing. Redeploy Rime and check the frontend logs.')
    config = read_yaml(path)
    for key in ['enable_user_dict', 'enable_encoder', 'encode_commit_history']:
        if config.get('translator', {}).get(key) is not False:
            raise ValueError(f'Learning guard failed: translator/{key}')
    expected_size = 10 if frontend == 'macos' else 3
    if config.get('menu', {}).get('page_size') != expected_size:
        raise ValueError(f'Expected menu/page_size={expected_size}')
    if frontend == 'macos':
        if 'lua_filter@*xiaohe_pager_filter' not in config.get('engine', {}).get('filters', []):
            raise ValueError('macOS logical pager filter is missing')
        if 'lua_processor@*xiaohe_pager_keys' not in config.get('engine', {}).get('processors', []):
            raise ValueError('macOS logical pager key handler is missing')
        if config.get('style', {}).get('candidate_format') != '\u200b[comment][candidate]':
            raise ValueError('macOS pager requires the display-only comment prefix')
        print('Compiled configuration verified: learning disabled; macOS 3/10 logical pager installed.')
    else:
        print('Compiled configuration verified: learning disabled; Windows 3 candidates per page.')
    print('Still verify actual input: op, op;, op\', nihcuijp and a known code from your local table.')
    print('Font coverage and frontend UI need native checking; compilation alone does not verify them.')


def main():
    # Windows redirected stdout may otherwise use an ANSI code page. Paths and
    # deployment instructions can contain Chinese even on an English system.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for cmd, handler in [('install', install), ('doctor', doctor)]:
        p = commands.add_parser(cmd)
        p.add_argument('--platform', choices=['macos', 'windows'])
        p.add_argument('--user-dir', type=Path)
        p.set_defaults(handler=handler)
        if cmd == 'install':
            p.add_argument('--table', type=Path)
            p.add_argument('--phonetic-only', action='store_true')
            p.add_argument('--dry-run', action='store_true')
    p = commands.add_parser('restore')
    p.add_argument('--backup', type=Path, required=True)
    p.set_defaults(handler=restore)
    args = parser.parse_args()
    try:
        args.handler(args)
    except (ValueError, OSError, yaml.YAMLError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
