import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from regression_dependencies import provision,requires_emsdk

class DependencyDiscovery(unittest.TestCase):
    def test_quoted_sdk_path_and_memory_fixture_are_detected(self):
        self.assertTrue(requires_emsdk(': "${EMSDK_DIR:=$HOME/emsdk}"\n'
            '"$EMSDK_DIR/upstream/emscripten/emcc" tests/tizen-memory.c -O2 -pthread'))
    def test_bare_compiler_and_environment_activated_fixtures_are_detected(self):
        for script in ('emcc -O0 a.c','EMCC="${EMCC:-emcc}"',
                       'source "$EMSDK_DIR/emsdk_env.sh"'):
            with self.subTest(script=script):self.assertTrue(requires_emsdk(script))
    def test_plain_native_fixture_does_not_require_wasm_sdk(self):
        self.assertFalse(requires_emsdk('cc tests/account.c src/account.c -o test\n./test'))
    def test_linux_dts_keeps_real_encoders_and_source_pinned_decoder(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'tests').mkdir();(root/'tools').mkdir()
            (root/'tests/dts_engine.sh').write_text('cc tests/dts_engine.c')
            (root/'tools/testa-tudo.sh').write_text('case "$n" in unused.sh) pulados=1;; esac')
            environment={name:str(root/name) for name in ('GITHUB_ENV','GITHUB_PATH','GITHUB_OUTPUT')}
            environment['RUNNER_TEMP']=str(root)
            encoders='\n'.join(' V..... '+name+' real encoder' for name in ('libx264','libvpx-vp9','libaom-av1','dca','aac'))
            with patch.dict(os.environ,environment),patch('regression_dependencies.sys.platform','linux'),patch('regression_dependencies.shutil.which',return_value='/usr/bin/ffmpeg'),patch('regression_dependencies.subprocess.check_output',return_value=encoders),patch('regression_dependencies.network_command') as command:
                provision(root,0,1)
                command.assert_called_once_with(['bash',str(root/'tools/build-dts-ffmpeg.sh')])
                self.assertEqual(os.environ['NUVIO_DTS_HOST'],'1')
                self.assertEqual(os.environ['CC'],'cc')
                self.assertIn('NUVIO_DTS_ROOT=',(root/'GITHUB_ENV').read_text())
            with patch.dict(os.environ,environment),patch('regression_dependencies.sys.platform','linux'),patch('regression_dependencies.shutil.which',return_value='/usr/bin/ffmpeg'),patch('regression_dependencies.subprocess.check_output',return_value=encoders.replace('libaom-av1','omitted')),patch('regression_dependencies.network_command') as command:
                with self.assertRaisesRegex(ValueError,'libaom-av1'):provision(root,0,1)
                command.assert_not_called()
