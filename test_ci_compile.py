import tempfile,unittest
from pathlib import Path
from ci_compile import plan

class CompilePlan(unittest.TestCase):
    def test_exact_flags_sources_and_link_order(self):
        args=['src/a.c','tests/b.c','-Isrc','-DCOUNT=3','-UNDEBUG','-O2','-g',
              '-include','forced.h','-L/lib','-lSDL2','-framework','OpenGL',
              '-pthread','-o','program']
        compile,link=plan(args,'objects')
        for command,source in zip(compile,['src/a.c','tests/b.c']):
            self.assertEqual(command[:-4],['-Isrc','-DCOUNT=3','-UNDEBUG','-O2','-g','-include','forced.h','-pthread'])
            self.assertEqual(command[-4],source)
            self.assertEqual(command[-3:-1],['-c','-o'])
        self.assertEqual(link,[str(Path('objects/unit-0000.o')),str(Path('objects/unit-0001.o')),*args[2:]])

    def test_unknown_and_side_effect_driver_modes_are_unchanged(self):
        base=['a.c','b.c','-o','app']
        for flag in ['-c','-E','-S','-MMD','-save-temps','-flto','-x','-arch','@args','-fprofile-arcs','-fsyntax-only','-Xclang','--version']:
            with self.subTest(flag=flag):self.assertIsNone(plan(base+[flag],'tmp'))
        for args in [['a.c','-o','app'],['a.c','b.c'],['a.c','b.cpp','-o','app'],base+['-o','second'],base+['-include']]:
            with self.subTest(args=args):self.assertIsNone(plan(args,'tmp'))

    def test_duplicate_basenames_have_distinct_objects(self):
        commands,_=plan(['a/same.c','b/same.c','-o','app'],'tmp')
        self.assertNotEqual(commands[0][-1],commands[1][-1])
