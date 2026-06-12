"""
conftest.py — shared fixtures for the Spendly test suite.

Design decisions:
- Every test gets a fresh in-memory SQLite database.  The module-level
  DB_PATH in database/db.py is patched via monkeypatch so no disk file is
  ever touched.
- The `client` fixture returns an already-authenticated test client so
  feature tests don't need to repeat login boilerplate.
- `insert_expense` is a factory fixture that lets individual tests seed
  expenses at explicit, fixed dates without relying on seed_db().
"""

import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module
from app import app as flask_app


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app(monkeypatch, tmp_path):
    """
    Yield a configured Flask application backed by a fresh in-memory SQLite
    database.  monkeypatch resets DB_PATH after each test so no test bleeds
    state into the next.
    """
    # Point every get_db() call at a unique temporary file that acts as an
    # isolated database.  We use a temp file (not ":memory:") so that all
    # helper functions that open their own connections share the same data.
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        WTF_CSRF_ENABLED=False,
    )

    with flask_app.app_context():
        db_module.init_db()

    yield flask_app


@pytest.fixture
def client(app):
    """
    Return a Flask test client with NO session (unauthenticated).
    Use this for authentication tests and the unauthenticated redirect check.
    """
    return app.test_client()


@pytest.fixture
def test_user(app):
    """
    Insert a single test user and return a dict with id, email, and password.
    Password is stored in plain text here only so fixtures can log in.
    """
    plain_password = "TestPass123"
    user_id = db_module.create_user(
        name="Test User",
        email="testuser@example.com",
        password_hash=generate_password_hash(plain_password),
    )
    return {"id": user_id, "email": "testuser@example.com", "password": plain_password}


@pytest.fixture
def auth_client(app, test_user):
    """
    Return a Flask test client whose session already contains the test user's
    user_id.  This is the standard client for all authenticated-route tests.
    """
    test_client = app.test_client()
    with test_client.session_transaction() as sess:
        sess["user_id"] = test_user["id"]
    return test_client


@pytest.fixture
def insert_expense(app, test_user):
    """
    Factory fixture.  Call it to insert one expense row for the test user.

    Usage:
        insert_expense(amount=50.0, category="Food", date="2026-01-15",
                       description="Lunch")

    All parameters except `date` have sensible defaults so callers only need
    to supply what matters for the test.

    Returns the inserted expense's rowid.
    """
    def _insert(
        amount=10.00,
        category="Other",
        date="2026-01-01",
        description="Test expense",
        user_id=None,
    ):
        uid = user_id if user_id is not None else test_user["id"]
        conn = db_module.get_db()
        cursor = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (uid, amount, category, date, description),
        )
        conn.commit()
        rowid = cursor.lastrowid
        conn.close()
        return rowid

    return _insert
