import unittest
from ci_profile import profile,category
from ci_impact import classify


class EvidenceProfiling(unittest.TestCase):
    def test_retained_jobs_not_billed_twice_in_measurement(self):
        job={'id':1,'name':'suite','run_attempt':1,'conclusion':'success',
             'created_at':'2026-10-12T12:00:00Z','started_at':'2026-10-12T12:01:00Z',
             'completed_at':'2026-10-12T12:03:00Z','steps':[]}
        retained={**job,'id':2,'run_attempt':2,'created_at':'2026-10-12T13:00:00Z'}
        result=profile({'jobs':[job,retained]})
        self.assertEqual(result['runner_seconds'],120)
        self.assertEqual(result['sum_job_queue_seconds'],60)
        self.assertEqual(len(result['jobs']),1)
        self.assertEqual(category('Build Tizen 8 using the upstream native toolchain'),'native_build')

    def test_backend_and_unknown_paths_require_explicit_mapping(self):
        with self.assertRaisesRegex(ValueError,'Unclassified'):classify(['backend/worker.js'])

    def test_private_backend_runs_security_checks_without_tv_builds(self):
        result=classify(['private-diagnostics/ingestion.mjs','private-diagnostics/migrations/0001_private_diagnostics.sql'])
        self.assertTrue(result['backend_security_required'])
        self.assertEqual(result['native_platforms'],[])
        self.assertFalse(result['release_validation'])

    def test_application_integration_always_checks_both_platforms(self):
        for path in ('integration/manifest.json','integration-bundle.zip','integration.py','webos-build.sh'):
            result=classify([path]);self.assertEqual(result['native_platforms'],['tizen','webos'])
            self.assertFalse(result['release_validation'])

    def test_ci_and_documentation_do_not_build_tv_packages(self):
        self.assertEqual(classify(['full_regression.py','DEVELOPMENT_LESSONS.md'])['native_platforms'],[])
        self.assertTrue(classify(['ci_compile.py'])['compiler_equivalence_required'])

    def test_historical_rendering_inputs_require_both_native_gates(self):
        for path in ('ci-baselines/deployment.tar.gz','ci-baselines/manifest.json','ci-baselines/v2.0.2.3-src.tar.gz'):
            result=classify([path])
            self.assertEqual(result['native_platforms'],['tizen','webos'])
            self.assertTrue(result['full_release_required_before_publication'])

    def test_relocated_test_files_keep_full_unit_discovery(self):
        self.assertEqual(classify(['tests/test_update_guard.py','tests/__init__.py'])['unit_tests'],'all test_*.py')
        self.assertEqual(classify(['tests/test_update_guard.py'])['native_platforms'],[])
