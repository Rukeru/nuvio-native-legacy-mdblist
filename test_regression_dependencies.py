import unittest
from regression_dependencies import requires_emsdk

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
