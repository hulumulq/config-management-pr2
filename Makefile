PYTHON ?= python3

.PHONY: test run
test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

run:
	./run.sh $(ARGS)
