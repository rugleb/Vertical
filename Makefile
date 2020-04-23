VENV := .venv
COVERAGE := .coverage
BUILD := .build

export PATH := $(VENV)/bin:$(PATH)

MIGRATIONS := migrations
VERTICAL := vertical
TESTS := tests

VERSION := latest
LOCAL_IMAGE_TAG := $(VERTICAL):$(VERSION)

AZURE_IMAGE_TAG := altdata.azurecr.io/vertical/$(LOCAL_IMAGE_TAG)
HARBOR_IMAGE_TAG := 172.16.5.30/vertical/$(LOCAL_IMAGE_TAG)

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
	coverage run --source $(VERTICAL) --module pytest
	coverage report
	coverage html -d $(COVERAGE)/html
	coverage xml -o $(COVERAGE)/cobertura.xml
	coverage erase

isort: .venv
	isort -rc $(VERTICAL) $(TESTS) $(MIGRATIONS)

mypy: .venv
	mypy $(VERTICAL) $(TESTS)

bandit: .venv
	bandit -r $(VERTICAL) $(TESTS) $(MIGRATIONS) --skip B101 --silent

flake: .venv
	flake8 $(VERTICAL) $(TESTS) $(MIGRATIONS)

lint: isort mypy bandit flake test

build: .build
	docker build . -t $(LOCAL_IMAGE_TAG) --pull --no-cache
	docker save -o $(BUILD)/$(LOCAL_IMAGE_TAG).tar $(LOCAL_IMAGE_TAG)

deploy: build
	docker tag $(LOCAL_IMAGE_TAG) $(AZURE_IMAGE_TAG)
	docker push $(AZURE_IMAGE_TAG)
	docker tag $(LOCAL_IMAGE_TAG) $(HARBOR_IMAGE_TAG)
	docker push $(HARBOR_IMAGE_TAG)

all: install lint cov build

.DEFAULT_GOAL = all
