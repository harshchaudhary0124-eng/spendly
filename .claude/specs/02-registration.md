# Spec: Registration

## Overview
Add a working registration flow to Spendly so new users can create an account with
their name, email, and password. This step wires up the `POST /register` route,
adds the necessary DB helper functions, and establishes Flask session management
so the newly registered user is logged in immediately after sign-up.

## Depends on
- Step 1 (Database Setup) — `users` table and `get_db()` must exist.

## Routes
- `GET /register` — already exists, renders `register.html` — public
- `POST /register` — **new** — validates form input, creates user, starts session, redirects — public

## Database changes
No new tables. Two new helper functions must be added to `database/db.py`:

- `create_user(name, email, password_hash)` — inserts a row into `users`, returns the new `id`
- `get_user_by_email(email)` — returns the matching `users` row or `None`

## Templates
- **Modify:** `templates/register.html`
  - Fix hardcoded `action="/register"` → `action="{{ url_for('register') }}"`
  - The `{% if error %}` block is already present — no structural change needed

## Files to change
- `app.py` — add `POST /register` handler, set `app.secret_key`, import `session` and `redirect` from Flask
- `database/db.py` — add `create_user()` and `get_user_by_email()`
- `templates/register.html` — fix hardcoded action URL

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only — no f-strings in SQL
- Hash passwords with `werkzeug.security.generate_password_hash` before storing
- `app.secret_key` must be set before any session usage; use a hard-coded dev string for now (`"dev-secret-change-me"`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic (`create_user`, `get_user_by_email`) belongs in `database/db.py`, not in the route
- On duplicate email: re-render `register.html` passing `error="An account with that email already exists."`
- On success: set `session['user_id']` to the new user's id, then `redirect(url_for('profile'))`
- Use `abort(400)` for missing / malformed form fields, not bare string returns

## Definition of done
- [ ] `GET /register` still loads the registration form
- [ ] Submitting valid details creates a new row in the `users` table with a hashed password
- [ ] Duplicate email submission re-renders the form with a visible error message and does not insert a duplicate row
- [ ] Successful registration sets `session['user_id']` to the new user's id
- [ ] Successful registration redirects to `/profile`
- [ ] Passwords are never stored in plain text (verify with a DB viewer or `sqlite3` CLI)
- [ ] The form `action` uses `url_for('register')`, not a hardcoded URL
- [ ] App starts without errors on `python app.py`
