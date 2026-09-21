"""
Tests run against real Postgres and Redis, not mocks or SQLite — per project
decision, since this project has already hit Postgres-specific bugs
(enum type handling) that an in-memory DB would never surface.

Requires a SEPARATE database from your dev DB so tests never touch real
data: create it once with
    docker compose exec db psql -U tracker -d job_tracker -c "CREATE DATABASE job_tracker_test;"

Each test runs inside its own transaction that is rolled back afterward —
so tests never leave data behind, and tests can't see each other's writes.
Redis uses a separate logical DB index (15) from your dev cache (0), and is
flushed before every test.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import redis

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://tracker:tracker_dev_pw@localhost:5433/job_tracker_test",
)
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")

# Set these BEFORE importing app modules, since app.config.Settings() reads
# them once at import time.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["REDIS_URL"] = TEST_REDIS_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use")

from app.database import Base, get_db  # noqa: E402
import app.models  # noqa: F401,E402  (registers all models on Base.metadata)
from app.main import app as fastapi_app  # noqa: E402
import app.cache as cache_module  # noqa: E402

test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def _create_test_schema():
    """Creates all tables once for the whole test session, drops them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """
    One connection + one outer transaction per test, rolled back at the end.
    Any commit() inside the app code during the test becomes a savepoint
    release, not a real commit — so nothing persists past the test.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    # point the cache module's already-constructed client at the test Redis DB
    original_redis_client = cache_module.redis_client
    cache_module.redis_client = redis.from_url(TEST_REDIS_URL, decode_responses=True)
    cache_module.redis_client.flushdb()

    with TestClient(fastapi_app) as test_client:
        yield test_client

    cache_module.redis_client = original_redis_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    """Registers a user and returns (email, password) for login in tests."""
    email = "testuser@example.com"
    password = "testpassword123"
    resp = client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201
    return {"email": email, "password": password}


@pytest.fixture
def auth_headers(client, registered_user):
    """Logs in registered_user and returns headers with a valid access token."""
    resp = client.post("/auth/login", json=registered_user)
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}