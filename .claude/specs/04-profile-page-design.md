# Spec: Profile Page Design

## Overview
Implement the `/profile` page for Spendly — replacing the stub string return
with a fully designed, login-protected page that displays the signed-in user's
details and lets them update their display name or change their password.
This step closes the auth loop: every page a logged-in user might navigate
to now renders correctly. The design should match the premium, Gen-Z fintech
aesthetic used across the rest of the app (CRED / Jupiter / Mercury style).

## Depends on
- Step 1 (Database Setup) — `users` table, `get_db()`, `get_user_by_id()` must exist.
- Step 2 (Registration) — `create_user()` and the `session['user_id']` convention.
- Step 3 (Login and Logout) — users must be able to sign in before reaching this page.

## Routes
- `GET /profile` — render profile page with current user data — logged-in only
- `POST /profile/update-name` — update display name, redirect back to `/profile` — logged-in only
- `POST /profile/update-password` — change password (verify current first), redirect back — logged-in only

Unauthenticated requests to any of these routes must `redirect(url_for('login'))` — consistent
with how `/register` and `/login` guard already-logged-in users (never use `abort(401)` here;
an unauthenticated user landing on `/profile` should be sent to the login page, not a blank 401).

## Database changes
Two new helper functions in `database/db.py` (no new tables or columns):
- `update_user_name(user_id, new_name)` — `UPDATE users SET name = ? WHERE id = ?`
- `update_user_password(user_id, new_password_hash)` — `UPDATE users SET password_hash = ? WHERE id = ?`

No schema migrations needed — the `users` table already has all required columns.

## Templates
- **Create:** `templates/profile.html`
  - Extends `base.html`
  - Displays: avatar initials (derived in Jinja2 from `current_user['name']`),
    full name, email, member-since date (format the raw ISO `created_at` string
    to a readable form, e.g. "June 2026", using Jinja2's `strptime`/slice or
    a simple Python `datetime.strptime` in the route before passing to template)
  - Inline update-name form (one field + submit)
  - Inline change-password form (current password + new password + confirm)
  - `success` and `error` variables for each section passed from the GET route
    (read from query params after POST → redirect, e.g. `?name_success=1`,
    `?name_error=blank`, `?pw_error=wrong_current`)
- **Modify:** `templates/base.html`
  - In the logged-in nav block, add a `Profile` link pointing to
    `url_for('profile')` alongside the existing "Sign out" link

## Files to change
- `app.py`
  - Import `update_user_name`, `update_user_password` from `database.db`
  - Import `datetime` from the standard library (for `created_at` formatting)
  - Replace stub `/profile` route with full `GET` implementation (reads query
    params `name_success`, `name_error`, `pw_success`, `pw_error` and passes
    them to the template)
  - Add `POST /profile/update-name` route
  - Add `POST /profile/update-password` route
- `database/db.py`
  - Add `update_user_name(user_id, new_name)`
  - Add `update_user_password(user_id, new_password_hash)`
- `templates/base.html`
  - Add `Profile` nav link in the logged-in block (alongside "Sign out")

## Files to create
- `templates/profile.html` — the profile page template
- `static/css/profile.css` — page-specific styles (avatar, card layout, form sections)

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only — no f-strings in SQL
- Current password must be verified with `check_password_hash` before updating
- New password must be hashed with `generate_password_hash` before storing
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic stays in `database/db.py`; routes only call helpers
- Unauthenticated access: `abort(401)` — never silently serve the page
- Name updates: strip whitespace; reject blank names with an inline error
- Password updates: confirm field must match new password; min 8 chars enforced
- Redirect back to `url_for('profile')` after every POST (PRG pattern) —
  pass `success=` or `error=` as query params, read them in the GET handler
- Avatar initials derived in Jinja2 — take first char of first word and first
  char of last word: `{{ user.name.split()[0][0] }}{{ user.name.split()[-1][0] if user.name.split()|length > 1 else '' }}`
  (uppercase both in template with `| upper`) — no JS or CSS counter tricks needed
- `created_at` formatted in the route via `datetime.strptime(user['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%B %Y')`
  and passed to template as `member_since`
- Link `profile.css` only in `profile.html` via `{% block head %}`, not in `base.html`

## Definition of done
- [ ] `GET /profile` renders the profile page for a logged-in user showing their name, email, and member-since date
- [ ] Visiting `/profile` while logged out returns a 401 (not a crash, not a blank page)
- [ ] Updating the name with a valid non-blank value saves and reflects immediately on reload
- [ ] Submitting a blank name shows an inline error and does not update the DB
- [ ] Changing password with the correct current password and matching new passwords (≥ 8 chars) succeeds
- [ ] Changing password with an incorrect current password shows an error and does not update the DB
- [ ] Changing password where new and confirm fields differ shows an error
- [ ] After a successful name update, the nav/header reflects the new name (via `current_user` context processor)
- [ ] Avatar initials display correctly (e.g. "Harsh Chaudhary" → "HC")
- [ ] The nav bar shows a "Profile" link for logged-in users that navigates to `/profile`
- [ ] Visiting `/profile` while logged out redirects to `/login` (not a 401 error)
- [ ] App starts without errors on `python app.py`
