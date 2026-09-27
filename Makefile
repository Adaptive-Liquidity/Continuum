.PHONY: reproduce-p00 reproduce-p00-harness verify-evidence test-p00

PYTHON ?= python3
PROOF := proofs/continuum-persistence-slice/proof.py
TEST := proofs/continuum-persistence-slice/test_proof.py
WORKDIR := proofs/continuum-persistence-slice/.run
ARCHIVED := docs/evidence/continuum-persistence-slice-2a.json

# Appendix A entry point. P00 LaTeX is not in this repository, so this is the
# proof + verify + test path only (alias of reproduce-p00-harness).
reproduce-p00: reproduce-p00-harness

# Decision #2A harness: unit suite, fresh two-process proof, independent recompute.
reproduce-p00-harness: test-p00
	$(PYTHON) $(PROOF) run --workdir $(WORKDIR)
	$(PYTHON) $(PROOF) verify --artifact $(WORKDIR)/continuum-persistence-slice-2a.json

# Evidence-only path against the archived artifact.
verify-evidence:
	$(PYTHON) $(PROOF) verify --artifact $(ARCHIVED)

test-p00:
	$(PYTHON) -m unittest -v $(TEST)
