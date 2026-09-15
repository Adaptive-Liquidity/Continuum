.PHONY: reproduce-p00 verify-evidence test-p00

PYTHON ?= python3
PROOF := proofs/continuum-persistence-slice/proof.py
TEST := proofs/continuum-persistence-slice/test_proof.py
WORKDIR := proofs/continuum-persistence-slice/.run
ARCHIVED := docs/evidence/continuum-persistence-slice-2a.json

# Appendix A entry point. Runs the unit suite, a fresh two-process proof,
# and an independent recompute of AC-1 through AC-8.
reproduce-p00: test-p00
	$(PYTHON) $(PROOF) run --workdir $(WORKDIR)
	$(PYTHON) $(PROOF) verify --artifact $(WORKDIR)/continuum-persistence-slice-2a.json

# Evidence-only path against the archived artifact.
verify-evidence:
	$(PYTHON) $(PROOF) verify --artifact $(ARCHIVED)

test-p00:
	$(PYTHON) -m unittest -v $(TEST)
