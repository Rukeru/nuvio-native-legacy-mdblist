import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
import json, os
import webos
from webos import package_version, needed

class WebOSRules(unittest.TestCase):
    def test_prepare_preserves_exact_checkout_and_patch_provenance(self):
        old = Path.cwd()
        with TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                root = Path('upstream')
                for directory in ['deploy/app', 'tools/p2p-motor']:
                    (root/directory).mkdir(parents=True)
                (root/'deploy/app/appinfo.json').write_text(json.dumps({'version':'2.0.2'}))
                (root/'tools/tizen-config.xml').write_text('<widget version="2.0.2"/>')
                (root/'tools/p2p-motor/build-arm.sh').write_text('COMMIT=abc123\n')
                (root/'tools/Dockerfile').write_text('RUN curl -fsSL "$SDK_URL" -o /tmp/sdk.tar.gz \\\n  && mkdir -p /opt \\\n')
                props = Path('fixture.properties').resolve()
                props.write_text('NUVIO_SUPABASE_URL=https://example.test\nNUVIO_SUPABASE_ANON_KEY=fixture\nTV_LOGIN_WEB_BASE_URL=https://example.test\n')
                Path('webos-state.json').write_text(json.dumps({'upstream':{'tag_name':'v2.0.2'},'upstream_version':'2.0.2','version':'2.0.200005'}))
                with patch.dict(os.environ, {'NUVIO_PROPERTIES':str(props)}), patch('webos.subprocess.run'), patch('webos.subprocess.check_output',return_value='exact-source-sha\n'), patch('webos.api',return_value={'sha':'engine-sha'}), patch('webos.download'):
                    webos.prepare(None)
                state = json.loads(Path('webos-state.json').read_text())
                self.assertEqual(state['upstream_commit'], 'exact-source-sha')
                self.assertEqual(state['engine_commit'], 'engine-sha')
                self.assertEqual(len(state['tizen_improvements']), 11)
                self.assertEqual(json.loads((root/'deploy/app/appinfo.json').read_text())['version'],'2.0.200005')
            finally:
                os.chdir(old)
    def test_version_order(self):
        self.assertEqual(package_version('v2.0.2',1),'2.0.200001')
        a=tuple(map(int,package_version('v2.0.2',99999).split('.')))
        b=tuple(map(int,package_version('v2.0.3',1).split('.')))
        self.assertLess(a,b)
        with self.assertRaises(ValueError): package_version('v2.0.2',100000)
    def test_independent_channel(self):
        u={'id':42}
        t={'tag_name':'v2.0.2.3','draft':False,'prerelease':False,'body':'<!-- upstream-release: 42 -->'}
        self.assertTrue(needed(u,[t]))
        w={'tag_name':'webos-v2.0.200001','draft':False,'prerelease':False,'body':'<!-- webos-upstream-release: 42 -->'}
        self.assertFalse(needed(u,[t,w]))
        self.assertTrue(needed(u,[t,w],True))
        self.assertTrue(needed({'id':43},[t,w]))
        w['draft']=True
        self.assertTrue(needed(u,[t,w]))
