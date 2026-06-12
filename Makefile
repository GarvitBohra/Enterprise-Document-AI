PYTHON ?= python3

.PHONY: backend frontend

backend:
	$(PYTHON) scripts/run_backend.py

frontend:
	$(PYTHON) scripts/run_frontend.py
