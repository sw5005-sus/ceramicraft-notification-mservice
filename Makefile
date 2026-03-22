.PHONY: gen setup test

gen:
	buf generate
	perl -pi -e 's/^import (.*_pb2.*)/from . import $$1/' src/ceramicraft_notification_mservice/pb/notification_pb2_grpc.py
	touch src/ceramicraft_notification_mservice/pb/__init__.py

setup:
	uv sync --dev

test:
	uv run pytest -v
