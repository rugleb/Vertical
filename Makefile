VENV := .venv
export PATH := $(VENV)/bin:$(PATH)

.venv:
	poetry env use 3.8
	poetry check

clean:
	rm -rf $(COVERAGE)

install: .venv
	poetry install --no-root

all: install

.DEFAULT_GOAL = all
