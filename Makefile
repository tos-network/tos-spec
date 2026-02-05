PYTHON ?= .venv/bin/python

.PHONY: venv install test fixtures vectors consume

venv:
	python3 -m venv .venv

install:
	$(PYTHON) -m pip install -e .
	$(PYTHON) -m pip install pytest

test:
	PYTHONPATH=~/tos-spec/src:~/tos-spec $(PYTHON) -m pytest -q

fixtures:
	PYTHONPATH=~/tos-spec/src:~/tos-spec $(PYTHON) -m pytest -q --output ~/tos-spec/fixtures

vectors:
	PYTHONPATH=~/tos-spec/src:~/tos-spec $(PYTHON) tools/fixtures_to_vectors.py

consume:
	PYTHONPATH=~/tos-spec/src:~/tos-spec $(PYTHON) tools/consume.py
