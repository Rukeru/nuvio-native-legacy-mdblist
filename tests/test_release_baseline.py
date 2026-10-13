import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import channel
import webos


class ReviewedBaseline(unittest.TestCase):
    baseline = {'base_tag': 'v2.0.4', 'base_commit': 'd' * 40}
    release = {'id': 404, 'tag_name': 'v2.0.4', 'draft': False, 'prerelease': False}

    def test_new_release_does_not_change_explicit_baseline(self):
        with patch('integration.manifest', return_value=self.baseline), \
                patch('channel.api', return_value=self.release) as api, \
                patch('update_guard.pages') as pages:
            selected, identity = channel.select_upstream(True)
        self.assertEqual(selected, self.release)
        self.assertEqual(identity['expected_upstream_commit'], 'd' * 40)
        self.assertTrue(identity['reviewed_baseline'])
        api.assert_called_once_with('repos/' + channel.UPSTREAM + '/releases/tags/v2.0.4')
        pages.assert_not_called()

    def test_automatic_monitor_still_selects_newest_release(self):
        newer = dict(self.release, id=405, tag_name='v2.0.5')
        with patch('update_guard.pages', return_value=[newer, self.release]), \
                patch('integration.manifest') as manifest:
            selected, identity = channel.select_upstream()
        self.assertEqual(selected, newer)
        self.assertEqual(identity, {})
        manifest.assert_not_called()

    def test_bad_baseline_release_never_falls_back(self):
        for change in ({'draft': True}, {'prerelease': True},
                       {'tag_name': 'v2.0.5'}, {'id': 0}):
            with self.subTest(change=change), \
                    patch('integration.manifest', return_value=self.baseline), \
                    patch('channel.api', return_value=dict(self.release, **change)), \
                    self.assertRaises(ValueError):
                channel.select_upstream(True)
        with patch('integration.manifest', return_value=dict(self.baseline, base_commit='main')), \
                patch('channel.api') as api, self.assertRaises(ValueError):
            channel.select_upstream(True)
        api.assert_not_called()

    def test_both_discovery_paths_preserve_checked_identity(self):
        previous = Path.cwd()
        with TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                with patch('integration.manifest', return_value=self.baseline), \
                        patch('channel.api', return_value=self.release), \
                        patch('update_guard.pages', return_value=[]), \
                        patch('update_guard.blocked', return_value=False), \
                        patch.dict(os.environ, {'GITHUB_OUTPUT': '', 'GITHUB_SHA': 'b' * 40}):
                    args = SimpleNamespace(run=68, force=True, reviewed_baseline=True, state='state.json')
                    channel.discover(args)
                    webos.discover(args)
                for name in ['state.json', 'webos-state.json']:
                    state = json.loads(Path(name).read_text())
                    self.assertEqual(state['upstream'], self.release)
                    self.assertEqual(state['expected_upstream_commit'], 'd' * 40)
                    self.assertEqual(state['builder_commit'], 'b' * 40)
                    self.assertTrue(state['build'])
            finally:
                os.chdir(previous)


if __name__ == '__main__':
    unittest.main()
