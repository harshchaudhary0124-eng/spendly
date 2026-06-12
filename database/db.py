import os
import sqlite3

from werkzeug.security import generate_password_hash

# Resolve the DB path relative to this file (database/ -> project root)
# so the app works regardless of the current working directory.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "expense_tracker.db")


def get_db():
    """Return a SQLite connection with row access and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they do not already exist. Safe to call repeatedly."""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at    TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            amount      REAL NOT NULL,
            category    TEXT NOT NULL,
            date        TEXT NOT NULL,
            description TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()
    conn.close()


def get_user_by_id(user_id):
    """Return the users row matching id, or None if no such user exists."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row


def get_user_by_email(email):
    """Return the users row matching email, or None if no such user exists."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return row


def create_user(name, email, password_hash):
    """Insert a new user and return the new row's id. Expects an already-hashed password."""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def update_user_name(user_id, new_name):
    conn = get_db()
    conn.execute("UPDATE users SET name = ? WHERE id = ?", (new_name, user_id))
    conn.commit()
    conn.close()


def update_user_password(user_id, new_password_hash):
    conn = get_db()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user_id))
    conn.commit()
    conn.close()


def get_expenses_by_user(user_id):
    """Return all expenses for a user, newest first."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def get_expenses_by_user_in_range(user_id, from_date, to_date):
    """Return expenses for a user filtered by an optional date range, newest first.

    from_date and to_date are ISO strings (YYYY-MM-DD) or None.
    When both are None the result is identical to get_expenses_by_user.
    """
    conn = get_db()
    sql = "SELECT * FROM expenses WHERE user_id = ?"
    params = [user_id]
    if from_date is not None:
        sql += " AND date >= ?"
        params.append(from_date)
    if to_date is not None:
        sql += " AND date <= ?"
        params.append(to_date)
    sql += " ORDER BY date DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def seed_db():
    """Insert demo data once. Returns early if the users table already has rows."""
    conn = get_db()

    existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing:
        conn.close()
        return

    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cursor.lastrowid

    # 8 expenses spread across June 2026, covering every category at least once.
    expenses = [
        (user_id, 12.50, "Food", "2026-06-02", "Lunch at cafe"),
        (user_id, 30.00, "Transport", "2026-06-03", "Monthly metro pass"),
        (user_id, 75.20, "Bills", "2026-06-04", "Electricity bill"),
        (user_id, 45.00, "Health", "2026-06-05", "Pharmacy"),
        (user_id, 18.99, "Entertainment", "2026-06-06", "Movie ticket"),
        (user_id, 60.40, "Shopping", "2026-06-08", "New shoes"),
        (user_id, 9.75, "Other", "2026-06-09", "Miscellaneous"),
        (user_id, 22.30, "Food", "2026-06-10", "Groceries"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        expenses,
    )

    conn.commit()
    conn.close()
