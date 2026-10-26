# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / 'scripts/manage.py'
spec = importlib.util.spec_from_file_location('manage', SCRIPT)
manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage)


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / '用户配置 existing user config'
        self.root.mkdir()
        self.table = self.base / '自用码表 user-provided.txt'
        # Synthetic test data, not taken from a third-party code table.
        self.table.write_text('测试甲\tabcd\t0\n测试乙\tabcd\t999\n', encoding='utf-8')
        self.original = {'patch': {'schema_list': [{'schema': 'luna_pinyin'}],
                                   'menu/page_size': 7}}
        (self.root / 'default.custom.yaml').write_bytes(manage.dump(self.original))

    def run_script(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPT), *args], text=True,
                                encoding='utf-8', capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def install(self, frontend='macos', *extra):
        return self.run_script('install', '--platform', frontend, '--user-dir', str(self.root), *extra)

    def backups(self):
        return sorted((self.root / '.xiaohe-backups').iterdir())

    def test_roundtrip_preserves_existing_config_and_database(self):
        database = self.root / 'unrelated.userdb'
        database.mkdir()
        (database / 'private').write_bytes(b'never-touch')
        self.install('macos', '--table', str(self.table))
        config = manage.read_yaml(self.root / 'default.custom.yaml')
        self.assertEqual(config['patch']['schema_list'], self.original['patch']['schema_list'])
        self.assertEqual(config['patch']['schema_list/+'], [{'schema': 'loginput_xiaohe'}])
        generated = (self.root / manage.TABLE).read_text(encoding='utf-8')
        self.assertIn('测试甲\tabcd\t999999\n测试乙\tabcd\t999998', generated)
        self.run_script('restore', '--backup', str(self.backups()[0]))
        self.assertEqual(manage.read_yaml(self.root / 'default.custom.yaml'), self.original)
        self.assertFalse((self.root / manage.TABLE).exists())
        self.assertEqual((database / 'private').read_bytes(), b'never-touch')

    def test_windows_style_and_idempotent_registration(self):
        self.install('windows', '--table', str(self.table))
        self.install('windows')
        config = manage.read_yaml(self.root / 'default.custom.yaml')
        self.assertEqual(config['patch']['schema_list/+'], [{'schema': 'loginput_xiaohe'}])
        style = manage.read_yaml(self.root / 'loginput_xiaohe.custom.yaml')['patch']['style']
        self.assertEqual(style['layout']['shadow_radius'], 0)
        self.assertEqual(style['label_font_point'], 11)
        self.assertEqual(style['label_format'], '%s')
        self.assertEqual(style['comment_font_point'], 0)
        self.assertTrue((self.root / 'lua/xiaohe_pager_keys.lua').exists())
        self.assertTrue((self.root / 'lua/xiaohe_pager_filter.lua').exists())

    def test_linux_profiles_roundtrip_without_overriding_panel_styles(self):
        for frontend in ('fcitx5', 'ibus'):
            with self.subTest(frontend=frontend):
                self.install(frontend, '--table', str(self.table))
                config = manage.read_yaml(self.root / 'loginput_xiaohe.custom.yaml')['patch']
                self.assertNotIn('style', config)
                self.assertTrue(config['xiaohe_pager/native_labels'])
                self.assertEqual(config['menu']['page_size'], 10)
                self.assertEqual(config['menu']['alternative_select_keys'], ' ' * 10)
                self.assertEqual(config['menu']['alternative_select_labels'], [])
                self.assertIn('lua_filter@*xiaohe_pager_filter', config['engine/filters'])
                self.assertTrue((self.root / 'lua/xiaohe_pager_keys.lua').exists())
                self.run_script('restore', '--backup', str(self.backups()[-1]))
                self.assertEqual(manage.read_yaml(self.root / 'default.custom.yaml'), self.original)
                self.assertFalse((self.root / 'lua/xiaohe_pager_keys.lua').exists())

    def test_linux_paths_and_explicit_frontend_choice(self):
        with patch.dict(manage.os.environ, {'XDG_DATA_HOME': str(self.base / 'data'),
                                           'XDG_CONFIG_HOME': str(self.base / 'config')}):
            self.assertEqual(manage.default_user_dir('fcitx5'), self.base / 'data/fcitx5/rime')
            self.assertEqual(manage.default_user_dir('ibus'), Path.home() / '.config/ibus/rime')
        with patch.object(manage.platform, 'system', return_value='Linux'):
            with self.assertRaises(ValueError):
                manage.frontend_name(None)

    def test_old_flat_menu_patches_cannot_override_pager(self):
        (self.root / 'loginput_xiaohe.custom.yaml').write_bytes(manage.dump({'patch': {
            'menu/page_size': 3, 'menu/alternative_select_labels': ['old'] * 10}}))
        self.install('windows')
        config = manage.read_yaml(self.root / 'loginput_xiaohe.custom.yaml')['patch']
        self.assertNotIn('menu/page_size', config)
        self.assertNotIn('menu/alternative_select_labels', config)
        self.assertEqual(config['menu']['alternative_select_labels'], [])

    def test_switching_back_to_macos_restores_comment_labels(self):
        self.install('windows')
        self.install('macos')
        config = manage.read_yaml(self.root / 'loginput_xiaohe.custom.yaml')['patch']
        self.assertFalse(config['xiaohe_pager/native_labels'])
        self.assertEqual(config['style']['candidate_format'], '\u200b[comment][candidate]')

    def test_dry_run_is_read_only(self):
        self.install('macos', '--table', str(self.table), '--dry-run')
        self.assertEqual(set(p.name for p in self.root.iterdir()), {'default.custom.yaml'})

    def test_bundled_table_default(self):
        self.install('macos')
        generated = (self.root / manage.TABLE).read_text(encoding='utf-8')
        self.assertIn('name: loginput_xiaohe_fixed', generated)
        self.assertTrue((self.root / 'lua/xiaohe_pager_keys.lua').exists())
        self.assertTrue((self.root / 'lua/xiaohe_pager_filter.lua').exists())
        patch = manage.read_yaml(self.root / 'loginput_xiaohe.custom.yaml')['patch']
        self.assertEqual(patch['menu']['page_size'], 10)
        self.assertIn('lua_filter@*xiaohe_pager_filter', patch['engine/filters'])
        self.assertGreater(len(generated.splitlines()), 40000)

    def test_phonetic_only_has_no_fixed_dependency(self):
        self.install('windows', '--phonetic-only')
        schema = manage.read_yaml(self.root / 'loginput_xiaohe.schema.yaml')
        self.assertNotIn('dependencies', schema['schema'])
        self.assertFalse(schema['translator']['enable_user_dict'])
        self.assertFalse((self.root / manage.TABLE).exists())
        self.assertIn('if env.fixed and #input', (self.root / 'lua/loginput_mix.lua').read_text(encoding='utf-8'))

    def test_restore_refuses_later_edits(self):
        self.install('macos', '--table', str(self.table))
        target = self.root / 'loginput_xiaohe.schema.yaml'
        target.write_bytes(target.read_bytes() + b'\n# later edit\n')
        result = self.run_script('restore', '--backup', str(self.backups()[0]), ok=False)
        self.assertIn('changed after installation', result.stderr)
        self.assertIn(b'# later edit', target.read_bytes())

    def test_unsafe_custom_learning_override_fails_before_writing(self):
        (self.root / 'loginput_xiaohe.custom.yaml').write_bytes(manage.dump({'patch': {'translator/enable_user_dict': True}}))
        self.run_script('install', '--platform', 'macos', '--user-dir', str(self.root),
                        '--table', str(self.table), ok=False)
        self.assertFalse((self.root / manage.TABLE).exists())

    def test_personal_date_bindings_are_not_overwritten(self):
        phrase = self.root / 'loginput_xiaohe_custom.txt'
        phrase.write_bytes(b'my-private-phrase\top\t100\n')
        self.run_script('install', '--platform', 'macos', '--user-dir', str(self.root),
                        '--table', str(self.table), ok=False)
        self.assertEqual(phrase.read_bytes(), b'my-private-phrase\top\t100\n')


if __name__ == '__main__':
    unittest.main()
