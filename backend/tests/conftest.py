import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Test databases and files never touch the developer's receipt data.
test_workspace = tempfile.TemporaryDirectory(prefix="receiptai-tests-")
test_path = Path(test_workspace.name)
os.environ["DATABASE_URL"] = f"sqlite:///{(test_path / 'tests.db').as_posix()}"
os.environ["STORAGE_PATH"] = str(test_path / "files")
os.environ["SEED_DEMO"] = "false"
os.environ["APP_ENV"] = "development"
os.environ["OPENAI_API_KEY"] = ""
os.environ["JOB_MODE"] = "inline"

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def close_test_database():
    yield
    engine.dispose()
    test_workspace.cleanup()


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def customer(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Test Customer",
            "email": "customer@example.com",
            "password": "a-test-password-2026",
        },
    )
    assert response.status_code == 201
    return client
