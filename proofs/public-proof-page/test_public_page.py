import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGE = ROOT / "public" / "proof" / "continuum-persistence" / "index.html"


class PublicProofPageTest(unittest.TestCase):
    def test_page_exists_and_states_verified_scope(self):
        self.assertTrue(PAGE.exists(), "public proof page must exist")
        text = PAGE.read_text(encoding="utf-8")
        required = [
            "Continuum Persistence Proof",
            "process restart on the same host",
            "AC-1 through AC-8",
            "COMMITTED",
            "DENIED",
            "Verifiable Entity with Revocable Authority",
            "What this does not prove",
            "host migration",
            "docs/evidence/continuum-persistence-slice-2a.json",
        ]
        for item in required:
            self.assertIn(item, text)


if __name__ == "__main__":
    unittest.main()
