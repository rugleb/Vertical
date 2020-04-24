PROJECT := vertical
VERSION := $(shell git describe --tags `git rev-list --tags --max-count=1`)

VENV := .venv
COVERAGE := .coverage
BUILD := .build

export PATH := $(VENV)/bin:$(PATH)

MIGRATIONS := migrations
TESTS := tests

IMAGE_NAME := $(PROJECT)_app

AZURE_IMAGE_TAG := altdata.azurecr.io/vertical/$(IMAGE_NAME):$(VERSION)
HARBOR_IMAGE_TAG := 172.16.5.30/vertical/$(IMAGE_NAME):$(VERSION)

.venv:
	poetry env use 3.8
	poetry check

.coverage:
	mkdir -p $(COVERAGE)

.build:
	mkdir -p $(BUILD)

clean:
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	rm -rf $(COVERAGE)
	rm -rf $(VENV)
	rm -rf $(BUILD)

install: .venv
	poetry install

test: .venv
	pytest

cov: .coverage
	coverage run --source $(PROJECT) --module pytest
	coverage report
	coverage html -d $(COVERAGE)/html
	coverage xml -o $(COVERAGE)/cobertura.xml
	coverage erase

isort: .venv
	isort -rc $(PROJECT) $(TESTS) $(MIGRATIONS)

mypy: .venv
	mypy $(PROJECT) $(TESTS)

bandit: .venv
	bandit -r $(PROJECT) $(TESTS) $(MIGRATIONS) --skip B101 --silent

flake: .venv
	flake8 $(PROJECT) $(TESTS) $(MIGRATIONS)

lint: isort mypy bandit flake test

build: .build
	docker build . -t $(IMAGE_NAME) --pull --no-cache
	docker save -o $(BUILD)/$(IMAGE_NAME).tar $(IMAGE_NAME)

deploy: build
	docker tag $(IMAGE_NAME) $(AZURE_IMAGE_TAG)
	docker push $(AZURE_IMAGE_TAG)
	docker tag $(IMAGE_NAME) $(HARBOR_IMAGE_TAG)
	docker push $(HARBOR_IMAGE_TAG)

all: install lint cov build

.DEFAULT_GOAL = all
