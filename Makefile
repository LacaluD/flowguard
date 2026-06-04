run:
	python main.py $(ARGS)

install:
	pip install -r requirements.txt

install-dev:
	pip install -r dev_requirements.txt

docker-build:
	docker build -t flowguard:latest .

docker-run:
	docker run flowguard:latest

docker-stop:
	docker stop $$(docker ps -aq --filter ancestor=flowguard:latest) || true

docker-rm:
	docker rm $$(docker ps -aq --filter ancestor=flowguard:latest) || true

docker-clean: docker-stop docker-rm
	docker rmi flowguard:latest

tests:
	python -m coverage run -m pytest -v -c configs/pytest.ini

# Will run normally only after tests run
tests-build-cov-report:
	python -m coverage report | tee docs/coverage-report.txt


sec-bandit:
	bandit -c configs/bandit.yml -r . -f txt \
          --severity-level high --confidence-level high \
          | tee docs/bandit-report.txt

lint:
	mypy src/ --ignore-missing-imports --explicit-package-bases --config-file configs/mypy.ini

lint-calls:
	mypy src/ --ignore-missing-imports --explicit-package-bases --enable-error-code call-arg --config-file configs/mypy.ini

typecheck:
	ruff check .
	black --check .

format:
	ruff check . --fix
	black .

black-diff:
	black --diff .

# Cleaning
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -f coverage.xml coverage.json .coverage

.PHONY: tests ci

ci: tests
	make sec-bandit
	make typecheck
	make lint
