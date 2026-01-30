.PHONY: dev up down test
dev:
	docker compose up --build
up:
	docker compose up -d
down:
	docker compose down
test:
	pytest -q --disable-warnings --maxfail=1
	pytest backend/tests/test_connectors.py -v
