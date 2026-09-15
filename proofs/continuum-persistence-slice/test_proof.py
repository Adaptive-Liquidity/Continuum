import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROOF = ROOT / "proof.py"


def load_proof():
    spec = importlib.util.spec_from_file_location("continuum_persistence_proof", PROOF)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ContinuumPersistenceSliceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = load_proof()

    def _run_slice(self):
        work = Path(tempfile.mkdtemp())
        db = work / "continuum.db"
        artifact = work / "artifact.json"
        p1 = subprocess.run(
            [sys.executable, str(PROOF), "phase1", "--db", str(db), "--artifact", str(artifact)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(p1.returncode, 0, p1.stderr)
        phase1 = json.loads(p1.stdout)
        p2 = subprocess.run(
            [sys.executable, str(PROOF), "phase2", "--db", str(db), "--artifact", str(artifact)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(p2.returncode, 0, p2.stderr)
        phase2 = json.loads(p2.stdout)
        data = json.loads(artifact.read_text(encoding="utf-8"))
        return phase1, phase2, data

    def test_process_restart_preserves_principal_state_authority_and_evidence(self):
        phase1, phase2, data = self._run_slice()
        self.assertEqual(phase1["computer_id"], phase2["computer_id"])
        self.assertEqual(phase1["vera_id"], phase2["vera_id"])
        self.assertNotEqual(phase1["process_id"], phase2["process_id"])
        self.assertEqual(phase2["state_value"], "continuum-state-survives-restart")
        self.assertEqual(phase2["effect_before_revocation"], "COMMITTED")
        self.assertEqual(phase2["effect_after_revocation"], "DENIED")
        self.assertEqual(data["execution"]["effect_class"], "in_process_sqlite_status_write")
        self.assertEqual(data["execution"]["mediator"], "continuum-persistence-slice-effect-boundary")
        computed = self.proof.compute_acceptance(data)
        self.assertTrue(all(computed.values()), computed)
        verify = subprocess.run(
            [sys.executable, str(PROOF), "verify", "--artifact", str(Path(tempfile.mkdtemp()) / "unused")],
            check=False,
            capture_output=True,
            text=True,
        )
        del verify
        artifact_path = Path(tempfile.mkdtemp()) / "artifact.json"
        artifact_path.write_text(json.dumps(data), encoding="utf-8")
        verified = self.proof.verify_artifact(artifact_path)
        self.assertTrue(verified["valid"], verified)
        self.assertTrue(verified["producer_acceptance_ignored"])
        self.assertTrue(all(verified["acceptance"].values()))

    def test_ac1_fails_when_only_computer_id_changes(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        mutated["computer_id"] = "continuum-computer-mutated"
        mutated["identity_continuity"]["post_computer_id"] = "continuum-computer-mutated"
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertFalse(computed["AC-1"])
        self.assertTrue(computed["AC-2"])

    def test_ac2_fails_when_only_vera_id_changes(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        mutated["vera_id"] = "vera-mutated"
        mutated["identity_continuity"]["post_vera_id"] = "vera-mutated"
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertTrue(computed["AC-1"])
        self.assertFalse(computed["AC-2"])

    def test_ac5_fails_when_mediator_is_modelish(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        mutated["execution"]["mediator"] = "llm-narrator"
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertFalse(computed["AC-5"])
        self.assertTrue(computed["AC-1"])
        self.assertTrue(computed["AC-2"])

    def test_ac8_fails_when_host_migration_marked_proven(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        mutated["excluded_scope"]["host_migration"] = True
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertFalse(computed["AC-8"])
        self.assertTrue(computed["AC-1"])

    def test_ac8_is_never_a_literal_true_in_source(self):
        source = PROOF.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r'["\']AC-8["\']\s*:\s*True', source))
        self.assertIn("def compute_acceptance", source)


if __name__ == "__main__":
    unittest.main()
