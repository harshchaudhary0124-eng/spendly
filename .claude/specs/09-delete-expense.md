# Spec: Delete Expense

## Overview
Step 09 completes the expense lifecycle by letting a logged-in user permanently
delete one of their own expenses. A GET request to the delete route renders a
confirmation page so the user cannot accidentally delete an expense by clicking
a link. A POST submission (with CSRF validation) performs the deletion and
redirects back to the profile dashboard with a success flash flag. The stub at
`GET /expenses/<id>/delete` is replaced with a full GET + POST handler.

## Depends on
- Step 01 — database setup (`expenses` table, `get_db()`)
- Step 03 — login/logout (session-based auth)
- Step 07 — add expense (`get_expense_by_id` helper in `db.py`)
- Step 08 — edit expense (CSRF token pattern already in session)

## Routes
- `GET  /expenses/<int:id>/delete` — renders a confirmation page for the expense — logged-in only
- `POST /expenses/<int:id>/delete` — validates CSRF, deletes the expense, redirects to profile — logged-in only

## Database changes
No new tables or columns. A new helper function `delete_expense(expense_id)` must
be added to `database/db.py` that runs a parameterised `DELETE FROM expenses WHERE id = ?`.

## Templates
- **Create:** `templates/delete_expense.html` — confirmation page that shows the
  expense amount, category, and date, then offers "Delete" (POST form) and
  "Cancel" (link back to profile) buttons.
- **Modify:** `templates/profile.html` — add a Delete button/link next to each
  recent expense row (alongside the existing Edit link) if not already present.
- **Modify:** `templates/edit_expense.html` — optionally add a Delete button so
  the user can delete from the edit form page as well.

## Files to change
- `app.py` — replace the stub `delete_expense` route with a GET + POST handler
  that: checks auth, loads the expense, verifies ownership, validates CSRF on
  POST, calls `delete_expense()`, and redirects to `profile` with `?deleted=1`.
- `database/db.py` — add `delete_expense(expense_id)` helper.
- `templates/profile.html` — add Delete button next to each expense in the
  Recent Expenses list.

## Files to create
- `templates/delete_expense.html` — confirmation page.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` with `get_db()` only.
- Parameterised queries only — never f-strings in SQL.
- Passwords hashed with werkzeug (not relevant here, but stated for completeness).
- Use CSS variables — never hardcode hex values in any template or stylesheet.
- All templates extend `base.html`.
- CSRF: reuse the existing `session["csrf_token"]` pattern from Step 07/08 —
  embed the token in the confirmation form and verify it on POST with `abort(403)`
  if it doesn't match.
- Ownership check: after loading the expense with `get_expense_by_id`, confirm
  `expense["user_id"] == session["user_id"]`; call `abort(403)` if not.
- Non-existent expense: call `abort(404)` if `get_expense_by_id` returns `None`.
- The DELETE must only happen on POST — the GET route must never modify data.
- Import `delete_expense` in `app.py` alongside the existing db imports.

## Definition of done
- [ ] Visiting `/expenses/<id>/delete` while logged out redirects to `/login`.
- [ ] Visiting `/expenses/<id>/delete` for a non-existent expense returns 404.
- [ ] Visiting `/expenses/<id>/delete` for another user's expense returns 403.
- [ ] A GET request to `/expenses/<id>/delete` renders the confirmation page
      showing the expense's amount, category, and date without deleting it.
- [ ] The confirmation page has a Cancel link that returns to the profile page
      without making any changes.
- [ ] Submitting the confirmation form (POST) with a valid CSRF token deletes
      the expense from the database and redirects to `/profile?deleted=1`.
- [ ] Submitting the confirmation form with a tampered or missing CSRF token
      returns 403 and does not delete the expense.
- [ ] After deletion the expense no longer appears in the profile dashboard or
      any expense query.
- [ ] The profile page Recent Expenses list shows a Delete button for each row.
- [ ] No raw SQL strings are interpolated with f-strings anywhere in the new code.
