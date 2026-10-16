#!/usr/bin/env python3
"""Build the nine upstream standalone CMake entry points without editing them.

This is a software/packaging regression, not renewal of 143h scientific acceptance.
Logs and explicit NOT_RUN records are written outside the source tree by default.
"""
import argparse
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time

SUITES = {
    'inputs': 'native_cpp', 'p1': 'native_cpp/p1', 'p3': 'native_cpp/p3',
    'p4': 'native_cpp/modules/p4_read62', 'p5': 'native_cpp/modules/p5_smerge',
    'p6': 'native_cpp/modules/p6_calmet',
    'p6e': 'native_cpp/modules/p6_calmet/p6e',
    'p6f': 'native_cpp/modules/p6_calmet/p6f',
    'p7': 'native_cpp/modules/p7_calpuff',
}
# These are historical real-case forensic runs, not software smoke tests.
EXCLUDE = 'cteas_p7_hefei_real_(firsthour_h3_receptor|sixhour_comp_precision)_diagnostic'


PORTABLE = {
    'inputs': ['cteas_p1_input_contracts', 'cteas_p2_input_contracts', 'cteas_p2_gen_fraction_contract'],
    'p1': ['cteas_p1_cellind_scoped'], 'p3': [],
    'p4': ['p4_fsl_input_contracts'], 'p5': ['p5_generic_utc_input_contracts'],
    'p6': ['p6a_calmet_scoped_contracts', 'p6c_terrain_envelope_software',
           'p6d_froude_adjust_software', 'p6c_station_geometry_software',
           'p6_native_cpp_hourly_driver_fail_closed_missing_case',
           'p6_native_cpp_comp_history_state_and_rollback'],
    'p6e': ['p6e_solar_software', 'p6e_coordlib_pj09z0_software', 'p6e_pgtstb_software',
            'p6e_heatfx_software', 'p6e_elustr_stable_software', 'p6e_wstarr_software',
            'p6e_mixht_stable_software', 'p6e_elustr_daytime_software'],
    'p6f': ['p6f_calmet_dat21_writer_unit', 'p6f_calmet_dat21_synthetic_cli_roundtrip',
            'p6f_calmet_dat21_e22_contract_cross_read'],
    'p7': ['cteas_p7_control_contract', 'cteas_p7_fortran_record_contract',
           'cteas_p7_calmet21_typed_field_contract', 'cteas_p7c_release_advection_inventory_contract',
           'cteas_p7d_dispersion_contract', 'cteas_p7_calm_idopt1_native_subset',
           'cteas_p7f_dry_deposition_contract', 'cteas_p7h_vertical_coupling_contract',
           'cteas_p7i_ctsg_support_contract', 'cteas_p7e_receptor_sampling_conc_contract'],
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--suite', choices=SUITES, action='append')
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--test-timeout', type=int, default=600, help='Per-test execution seconds, independent of numerical tolerances')
    ap.add_argument('--portable', action='store_true', help='Explicit software subset that needs no external vendor/terrain assets')
    args = ap.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    if out == root or root in out.parents:
        ap.error('--out must be outside the checkout (keeps compiled artifacts out of source)')
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    scratch = out / 'scratch'
    scratch.mkdir(exist_ok=True)
    env['TMPDIR'] = str(scratch)
    tools = out / 'tools'
    tools.mkdir(exist_ok=True)
    fort = shutil.which(env.get('FC', 'gfortran-11'))
    if not fort:
        ap.error('FC or gfortran-11 must be available')
    shim = tools / 'gfortran'
    if not shim.exists():
        shim.symlink_to(fort)
    env['PATH'] = str(tools) + os.pathsep + env['PATH']
    env['FC'] = fort
    results = []

    def run(label, command):
        start = time.monotonic()
        with (out / (label + '.log')).open('w') as log:
            log.write('COMMAND: ' + json.dumps(command) + '\n')
            log.flush()
            proc = subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
        results.append(dict(label=label, command=command, returncode=proc.returncode,
                            seconds=round(time.monotonic() - start, 3), log=label + '.log'))
        (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(label, 'rc=' + str(proc.returncode), flush=True)
        return proc.returncode

    for name in args.suite or SUITES:
        build = out / ('build-' + name)
        rc = run(name + '-configure', ['cmake', '-S', str(root / SUITES[name]), '-B', str(build),
                 '-DCMAKE_BUILD_TYPE=Debug', '-DCMAKE_CXX_COMPILER=' + env.get('CXX', '/usr/bin/g++-12'),
                 '-DPython3_EXECUTABLE=' + sys.executable])
        if rc:
            continue
        rc = run(name + '-build', ['cmake', '--build', str(build), '--parallel', str(args.jobs)])
        if rc:
            continue
        catalog = subprocess.check_output(['ctest', '--test-dir', str(build), '--show-only=json-v1'], env=env)
        (out / (name + '-tests.json')).write_bytes(catalog)
        tests = json.loads(catalog)['tests']
        available = {t['name'] for t in tests}
        if args.portable and not set(PORTABLE[name]) <= available:
            raise RuntimeError('Portable test names missing from upstream CTest: ' + name)
        selection = []
        for t in tests:
            selected = t['name'] in PORTABLE[name] if args.portable else not re.search(EXCLUDE, t['name'])
            selection.append(dict(name=t['name'], status='SCHEDULED' if selected else 'NOT_RUN',
                                  reason='portable software subset' if args.portable else 'historical P7 receptor diagnostic excluded'))
        (out / (name + '-selection.json')).write_text(json.dumps(selection, indent=2) + '\n')
        if args.portable and not PORTABLE[name]:
            print(name + ': no upstream CTest tests (P3 reference comparison is a separate harness)', flush=True)
            continue
        command = ['ctest', '--test-dir', str(build), '--output-on-failure', '--timeout', str(args.test_timeout)]
        if args.portable:
            command += ['--no-tests=error', '-R', '^(' + '|'.join(re.escape(t) for t in PORTABLE[name]) + ')$']
        else:
            command += ['-E', EXCLUDE]
        run(name + '-ctest', command)
    return int(any(r['returncode'] for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
