# Spec: Login and Logout

## Overview
Wire up credential-based login and session teardown for Spendly. This step
activates the `POST /login` route so users can authenticate with their email
and password, and replaces the `GET /logout` stub so users can end their
session. After this step, the full auth cycle — register → login → logout — is
complete and every subsequent step can build on a reliable session identity.

## Depends on
- Step 1 (Database Setup) — `users` table and `get_db()` must exist.
- Step 2 (Registration) — `get_user_by_email()` must exist in `database/db.py`
  and `session['user_id']` must be the agreed session key.

## Routes
- `GET /login` — already exists, renders `login.html` — public
- `POST /login` — **new** — validates credentials, starts session, redirects — public
- `GET /logout` — **implement stub** — clears session, redirects to landing — logged-in

## Database changes
No database changes. `get_user_by_email()` already exists from Step 2 and is
the only DB helper needed here.

## Templates
- **Modify:** `templates/login.html`
  - Fix hardcoded `action="/login"` → `action="{{ url_for('login') }}"`
  - The `{% if error %}` block is already present — no structural change needed
- **Modify:** `templates/working.html`
  - Add "Welcome Back" `auth-header` banner before the hero section
  - Reuse existing `.auth-section`, `.auth-container`, `.auth-title`,
    `.auth-subtitle` classes — no new CSS needed

## Files to change
- `app.py` — implement `POST /login` and `GET /logout`; add
  `check_password_hash` to the werkzeug import; redirect to `url_for('working')`
  on successful login
- `templates/login.html` — fix hardcoded action URL
- `templates/working.html` — add Welcome Back banner

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only — no f-strings in SQL
- Verify passwords with `werkzeug.security.check_password_hash` — never compare
  plain text against the stored hash
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic stays in `database/db.py`; routes only call helpers
- On wrong email or wrong password: re-render `login.html` with
  `error="Invalid email or password."` — do not reveal which field was wrong
- On success: set `session['user_id']` to the user's `id`, then
  `redirect(url_for('working'))`
- Logout must call `session.clear()` (not just `session.pop`), then
  `redirect(url_for('landing'))`
- Use `abort(400)` for missing / malformed form fields, not bare string returns
- Change `GET /login` route to also accept `POST` by updating its
  `methods` argument: `methods=["GET", "POST"]`

## Definition of done
- [ ] `GET /login` renders the login form
- [ ] Submitting correct credentials sets `session['user_id']` and redirects to `/working` and the page should say "Welcome Back" on top matching with website theme and font.
- [ ] Submitting a non-existent email re-renders the form with `"Invalid email or password."` and does not crash
- [ ] Submitting the wrong password for a valid email re-renders the form with `"Invalid email or password."` and does not crash
- [ ] `GET /logout` clears the session and redirects to `/`
- [ ] After logout, visiting `/working` does not expose user data (stub still shows string but session is gone)
- [ ] The login form `action` uses `url_for('login')`, not a hardcoded URL
- [ ] App starts without errors on `python app.py`
