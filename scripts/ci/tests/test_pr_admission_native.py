"""Exercise the real github-script JS in pr-admission.yml without contacting GitHub."""
from pathlib import Path
import json
import subprocess
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/pr-admission.yml"


class AdmissionPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
        cls.steps = workflow["jobs"]["repository-admission"]["steps"]
        cls.code = cls.steps[0]["with"]["script"]
        cls.science = workflow["jobs"]["scientific-admission"]["steps"][0]["with"]["script"]

    def simulate(self, statuses, filenames=("native_cpp/s4.cpp",), draft=True):
        node_code = r"""
const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
const script = process.env.WORKFLOW_CODE;
const statuses = JSON.parse(process.env.CASE_STATUSES);
const files = JSON.parse(process.env.CASE_FILES).map(filename=>({filename}));
const failures = [];
const infos = [];
const github = {rest:{pulls:{listFiles:0},repos:{listCommitStatusesForRef:1}},
 paginate:async (fn)=> fn===0?files:statuses};
const context = {payload:{pull_request:{number:308,head:{sha:'a'.repeat(40)},draft:true}},
repo:{owner:'RRain001',repo:'CTEAS-next'}};
const core = {setFailed:(s)=>failures.push(s),info:(s)=>infos.push(s)};
(async()=>{await new AsyncFunction('github','context','core',script)(github,context,core);
 process.stdout.write(JSON.stringify({failures,infos}));})()
 .catch(e=>{process.stderr.write(String(e));process.exit(3)});
"""
        import os
        env = dict(os.environ)
        env.update(WORKFLOW_CODE=self.code, CASE_STATUSES=json.dumps(statuses),
                   CASE_FILES=json.dumps(filenames))
        r = subprocess.run(["node", "-e", node_code], text=True, capture_output=True,
                           env=env, timeout=10)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_native_full_on_exact_pr_head_accepted(self):
        d = self.simulate([{"context": "ubuntu-native-full", "state": "success"}])
        self.assertFalse(d["failures"])
        self.assertIn("ubuntu-native-full", " ".join(d["infos"]))

    def test_legacy_docker_full_still_accepted(self):
        d = self.simulate([{"context": "ubuntu-docker-full", "state": "success"}])
        self.assertFalse(d["failures"])

    def test_missing_status_fails_closed(self):
        self.assertTrue(self.simulate([])["failures"])

    def test_failed_native_and_missing_docker_fails_closed(self):
        self.assertTrue(self.simulate([{"context": "ubuntu-native-full", "state": "failure"}])["failures"])

    def test_latest_native_failure_not_overridden_by_older_success(self):
        self.assertTrue(self.simulate([
            {"context": "ubuntu-native-full", "state": "failure"},
            {"context": "ubuntu-native-full", "state": "success"}
        ])["failures"])

    def test_docs_only_no_full_build(self):
        self.assertFalse(self.simulate([], ("docs/ci/policy.md",))["failures"])

    def test_science_gate_kept(self):
        for item in ("pr.draft", "science-validated", "listReviews",
                     "commit_id === pr.head.sha", "APPROVED", "Bot"):
            self.assertIn(item, self.science)

    def test_workflow_auto_ci_not_deleted(self):
        raw = WORKFLOW.read_text()
        self.assertIn("pull_request:", raw)
        self.assertIn("synchronize", raw)
        self.assertIn("repository-admission:", raw)
        self.assertIn("scientific-admission:", raw)


if __name__ == "__main__":
    unittest.main()
