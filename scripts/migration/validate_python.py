#!/usr/bin/env python3
"""Run upstream data-preparation/G5 tests, recording external-only NOT_RUN cases."""
import argparse
import json
import os
from pathlib import Path
import sys
import unittest

EXTERNAL_ONLY = {'test_p5_rules.P5MissingPolicyTests.test_original_smerge_calmet_calm_source_contract'}
PATHS = ['native_cpp/modules/p4_read62/data_prep/tests',
         'native_cpp/modules/p5_smerge/data_prep/tests', 'engine/gui_g5/tests']


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--portable', action='store_true')
    args = ap.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    if out == root or root in out.parents:
        ap.error('--out must be outside the checkout')
    sys.path.insert(0, str(root))
    sys.dont_write_bytecode = True
    os.chdir(root)
    out.mkdir(parents=True, exist_ok=True)
    tests = []
    for path in PATHS:
        tests.extend(flatten(unittest.TestLoader().discover(str(root / path), pattern='test_*.py')))
    if not EXTERNAL_ONLY <= {t.id() for t in tests}:
        raise RuntimeError('Expected external-only test identity not found')
    selected = []
    plan = []
    for test in tests:
        omitted = args.portable and test.id() in EXTERNAL_ONLY
        plan.append(dict(name=test.id(), status='NOT_RUN' if omitted else 'SCHEDULED',
                         reason='Requires excluded original SMERGE/CALMET source' if omitted else 'upstream test unchanged'))
        if not omitted:
            selected.append(test)
    (out / 'python-selection.json').write_text(json.dumps(plan, indent=2) + '\n')
    with (out / 'python-unittest.log').open('w') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(unittest.TestSuite(selected))
    summary = dict(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                   not_run=sum(t['status'] == 'NOT_RUN' for t in plan),
                   status='PASS_SOFTWARE' if result.wasSuccessful() else 'FAIL')
    (out / 'python-results.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return not result.wasSuccessful()


if __name__ == '__main__':
    raise SystemExit(main())
