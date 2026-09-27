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


def failed_criteria(computed):
    return [key for key, value in computed.items() if not value]


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
        self.assertEqual(failed_criteria(computed), ["AC-1"], computed)

    def test_ac2_fails_when_only_vera_id_changes(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        mutated["vera_id"] = "vera-mutated"
        mutated["identity_continuity"]["post_vera_id"] = "vera-mutated"
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertTrue(computed["AC-1"])
        self.assertFalse(computed["AC-2"])
        self.assertEqual(failed_criteria(computed), ["AC-2"], computed)

    def test_ac5_fails_when_mediator_is_modelish(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        mutated["execution"]["mediator"] = "llm-narrator"
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertFalse(computed["AC-5"])
        self.assertTrue(computed["AC-1"])
        self.assertTrue(computed["AC-2"])
        self.assertEqual(failed_criteria(computed), ["AC-5"], computed)

    def test_ac8_fails_when_host_migration_marked_proven(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        mutated["excluded_scope"]["host_migration"] = True
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertFalse(computed["AC-8"])
        self.assertTrue(computed["AC-1"])
        self.assertEqual(failed_criteria(computed), ["AC-8"], computed)

    def test_ac8_is_never_a_literal_true_in_source(self):
        source = PROOF.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r'["\']AC-8["\']\s*:\s*True', source))
        self.assertIn("def compute_acceptance", source)

    def test_ac3_fails_when_only_state_value_changes(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        mutated["state"]["value"] = "continuum-state-was-rewritten"
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertFalse(computed["AC-3"])
        self.assertEqual(failed_criteria(computed), ["AC-3"], computed)

    def test_ac4_fails_when_only_final_grant_state_is_active(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        mutated["authority"]["final_state"] = "ACTIVE"
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertFalse(computed["AC-4"])
        self.assertEqual(failed_criteria(computed), ["AC-4"], computed)

    def test_ac6_fails_when_only_sequence_has_a_gap(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        mutated["evidence"][-1]["seq"] = mutated["evidence"][-1]["seq"] + 10
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertFalse(computed["AC-6"])
        self.assertEqual(failed_criteria(computed), ["AC-6"], computed)

    def test_ac4_fails_when_denied_capability_differs(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        denied = next(event for event in mutated["evidence"] if event["kind"] == "effect.denied")
        denied["payload"]["capability"] = "effect:other.write"
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertFalse(computed["AC-4"])
        self.assertEqual(failed_criteria(computed), ["AC-4"], computed)

    def test_ac1_and_ac2_fail_when_evidence_pids_are_not_a_restart(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        post_pid = mutated["discontinuity"]["post_restart_process_id"]
        for event in mutated["evidence"]:
            event["process_id"] = post_pid
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertFalse(computed["AC-1"])
        self.assertFalse(computed["AC-2"])
        self.assertTrue(computed["AC-3"])
        self.assertTrue(computed["AC-8"])

    def test_ac8_fails_when_claim_ceiling_is_unbounded(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        mutated["claim_ceiling"] = "this is not the same host; we claim host migration"
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertFalse(computed["AC-8"])
        self.assertEqual(failed_criteria(computed), ["AC-8"], computed)

    def test_ac7_fails_when_only_vera_computer_binding_breaks(self):
        _, _, data = self._run_slice()
        mutated = deepcopy(data)
        mutated["identity_continuity"]["bound_computer_id"] = "continuum-computer-unbound"
        mutated["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
        computed = self.proof.compute_acceptance(mutated)
        self.assertFalse(computed["AC-7"])
        self.assertEqual(failed_criteria(computed), ["AC-7"], computed)


class IndependentVerifierTest(unittest.TestCase):
    def test_verifier_recomputes_acceptance_instead_of_trusting_artifact_flags(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            run = subprocess.run(
                [sys.executable, str(PROOF), "run", "--workdir", str(work)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            artifact = work / "continuum-persistence-slice-2a.json"
            data = json.loads(artifact.read_text(encoding="utf-8"))
            data["acceptance"] = {f"AC-{i}": False for i in range(1, 9)}
            artifact.write_text(json.dumps(data), encoding="utf-8")
            verify = subprocess.run(
                [sys.executable, str(PROOF), "verify", "--artifact", str(artifact)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr)
            result = json.loads(verify.stdout)
            self.assertTrue(result["valid"])
            self.assertTrue(result["producer_acceptance_ignored"])
            self.assertTrue(all(result["acceptance"].values()))

    def test_verifier_rejects_independent_ac1_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            run = subprocess.run(
                [sys.executable, str(PROOF), "run", "--workdir", str(work)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            artifact = work / "continuum-persistence-slice-2a.json"
            data = json.loads(artifact.read_text(encoding="utf-8"))
            data["computer_id"] = "continuum-computer-mutated"
            data["identity_continuity"]["post_computer_id"] = "continuum-computer-mutated"
            data["acceptance"] = {f"AC-{i}": True for i in range(1, 9)}
            artifact.write_text(json.dumps(data), encoding="utf-8")
            verify = subprocess.run(
                [sys.executable, str(PROOF), "verify", "--artifact", str(artifact)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(verify.returncode, 1, verify.stdout)
            result = json.loads(verify.stdout)
            self.assertFalse(result["valid"])
            self.assertFalse(result["acceptance"]["AC-1"])
            self.assertTrue(result["acceptance"]["AC-2"])
            self.assertTrue(result["producer_acceptance_ignored"])


if __name__ == "__main__":
    unittest.main()
