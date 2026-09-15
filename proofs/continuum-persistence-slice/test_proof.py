import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROOF = ROOT / "proof.py"


class ContinuumPersistenceSliceTest(unittest.TestCase):
    def test_process_restart_preserves_principal_state_authority_and_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
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

            self.assertEqual(phase1["computer_id"], phase2["computer_id"])
            self.assertEqual(phase1["vera_id"], phase2["vera_id"])
            self.assertNotEqual(phase1["process_id"], phase2["process_id"])
            self.assertEqual(phase2["state_value"], "continuum-state-survives-restart")
            self.assertEqual(phase2["effect_before_revocation"], "COMMITTED")
            self.assertEqual(phase2["effect_after_revocation"], "DENIED")
            self.assertTrue(phase2["effect_executed_after_restart"])

            data = json.loads(artifact.read_text(encoding="utf-8"))
            self.assertEqual(data["computer_id"], phase1["computer_id"])
            self.assertEqual(data["vera_id"], phase1["vera_id"])
            self.assertEqual(data["discontinuity"]["type"], "process_restart_same_host")
            self.assertGreaterEqual(len(data["evidence"]), 8)
            self.assertTrue(data["acceptance"]["AC-1"])
            self.assertTrue(data["acceptance"]["AC-8"])
            self.assertNotIn("regency", json.dumps(data).lower())
            self.assertNotIn("host migration", json.dumps(data).lower())

            verify = subprocess.run(
                [sys.executable, str(PROOF), "verify", "--artifact", str(artifact)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr)
            verified = json.loads(verify.stdout)
            self.assertTrue(verified["valid"])
            self.assertTrue(all(verified["acceptance"].values()))


if __name__ == "__main__":
    unittest.main()
