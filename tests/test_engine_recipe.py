import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from engine_recipe import pin_recipe,record_overlay

class EngineRecipeTests(unittest.TestCase):
    def test_legacy_pin_is_preserved(self):
        with TemporaryDirectory() as t:
            r=Path(t);p=r/'build.sh';p.write_text('COMMIT=abcdef123\n')
            self.assertEqual(pin_recipe(r,p),(p,'COMMIT','abcdef123',None))
    def test_shared_pin_and_overlay_are_recorded(self):
        with TemporaryDirectory() as t:
            r=Path(t);d=r/'tools/p2p-motor';d.mkdir(parents=True)
            p=d/'build-arm.sh';p.write_text('. tools/p2p-motor/pasta.sh; nv_p2p_raiz\nnv_p2p_fonte "$W/nuvio-engine"\n')
            shared=d/'pasta.sh';shared.write_text('NV_P2P_COMMIT=02938d7\ngit -C "$1" checkout -q "$NV_P2P_COMMIT"\np=janela-334.patch\ngit -C "$1" apply "$p"\n')
            overlay=d/'janela-334.patch';overlay.write_bytes(b'fixture overlay')
            self.assertEqual(pin_recipe(r,p),(shared,'NV_P2P_COMMIT','02938d7',overlay))
            state={};record_overlay(state,overlay)
            import hashlib
            self.assertEqual(state['engine_overlay']['sha256'],hashlib.sha256(b'fixture overlay').hexdigest())
            shared.write_text(shared.read_text()+'NV_P2P_COMMIT=1234567\n')
            with self.assertRaises(ValueError):pin_recipe(r,p)
    def test_missing_pin_fails_closed(self):
        with TemporaryDirectory() as t:
            r=Path(t);p=r/'build.sh';p.write_text('git checkout main\n')
            with self.assertRaises(ValueError):pin_recipe(r,p)
