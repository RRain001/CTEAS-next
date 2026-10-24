"""Test Ubuntu exact-SHA full contracts without needing remote credentials."""
from pathlib import Path
import unittest
from scripts.ci.cteas_native_full import REQUIRED, commands, step_environment


class NativeFullSourceBinariesTests(unittest.TestCase):
    def setUp(self):
        self.root = Path('/tmp/cteas-native-frozen-source')
        self.build = Path('/tmp/cteas-native-full-evidence/build')
        self.python = '/tmp/cteas-native-py311/bin/python'

    def test_auxiliary_build_steps_and_provenance(self):
        steps = commands(self.root, self.build, 12, self.python)
        self.assertEqual(tuple(name for name, _ in steps), REQUIRED)
        index = dict(steps)
        self.assertIn('-DCMAKE_CXX_COMPILER=/usr/bin/g++-12', index['cmake-configure'])
        for module in ('p1', 'p3'):
            self.assertIn(str(self.root / 'native_cpp' / module),
                          index[module + '-configure'])
            self.assertIn('-DCMAKE_CXX_COMPILER=/usr/bin/g++-12',
                          index[module + '-configure'])
            self.assertIn(module + '-build', REQUIRED)
            self.assertIn(module + '-ctest', REQUIRED)
        self.assertIn('-DPython3_EXECUTABLE=' + self.python, index['p3-configure'])

    def test_s2g_binaries_are_from_current_build(self):
        env = step_environment('s2g-python', self.build)
        self.assertEqual(env['P1_CASE_BINARY'],
                         str(self.build.parent / 'build-p1/cteas_p1_terrain_case'))
        self.assertEqual(env['P2_D3_GLCC'],
                         str(self.build / 'cteas_p2_glcc_lu_dat'))
        self.assertEqual(env['P12_OLD_ADAPTER'],
                         str(self.build.parent / 'build-p3/cteas_p12_to_p3_dat'))
        self.assertEqual(env['P2_GLCC_TEST_DRIVER'],
                         str(self.build / 'cteas_p2_glcc_gen_test_driver'))
        self.assertEqual(env['P2_GEN_CLI'],
                         str(self.build / 'cteas_p2_gen_fraction'))
        self.assertEqual(env['CXX'], '/usr/bin/g++-12')
        for name in REQUIRED:
            if name != 's2g-python':
                self.assertEqual(step_environment(name, self.build), {})


if __name__ == '__main__':
    unittest.main()
