.PHONY: gen setup test

gen:
	@if ! command -v buf > /dev/null; then \
		echo "buf is not installed. Falling back to grpcio-tools."; \
		uv run --with grpcio-tools python -m grpc_tools.protoc \
			-I protos \
			--python_out=src/ceramicraft_notification_mservice/pb \
			--grpc_python_out=src/ceramicraft_notification_mservice/pb \
			--pyi_out=src/ceramicraft_notification_mservice/pb \
			protos/notification.proto; \
	else \
		buf generate; \
	fi
	perl -pi -e 's/^import (.*_pb2.*)/from . import $$1/' src/ceramicraft_notification_mservice/pb/notification_pb2_grpc.py
	touch src/ceramicraft_notification_mservice/pb/__init__.py

setup:
	uv sync --dev

test:
	uv run pytest -v
