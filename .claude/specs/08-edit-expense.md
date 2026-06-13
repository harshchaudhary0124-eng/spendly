# Spec: Edit Expense

## Overview

Step 8 activates the stub `GET /expenses/<id>/edit` route by converting it into a full
GET+POST flow that lets authenticated users update an existing expense. The user is
shown a pre-filled form with the expense's current values; on valid submission the row
is updated in the `expenses` table and the user is redirected to their profile dashboard
with a success indicator. If the expense does not exist or belongs to a different user,
the route aborts with 404 or 403 respectively. Invalid or missing fields re-render the
form with a clear inline error message. This is a natural companion to Add Expense
(Step 7) and is a prerequisite for Delete (Step 9).

## Depends on

- Step 01 — Database Setup (`expenses` table and `get_db()` must exist)
- Step 05 — Profile Dashboard Backend (the profile redirect target must work)
- Step 07 — Add Expense (`create_expense`, `_ALLOWED_CATEGORIES`, CSRF pattern already established)

## Routes

- `GET /expenses/<int:id>/edit` — render the pre-filled edit form — logged-in only
- `POST /expenses/<int:id>/edit` — validate and update the expense, then redirect to `/profile?edited=1` — logged-in only

## Database changes

No new tables or columns. The existing `expenses` schema covers all required fields.

Add two new helpers to `database/db.py`:

```
get_expense_by_id(expense_id)
```
- Selects a single row from `expenses` WHERE `id = ?`.
- Returns the row (as `sqlite3.Row`) or `None` if not found.

```
update_expense(expense_id, amount, category, date, description)
```
- Updates `amount`, `category`, `date`, and `description` WHERE `id = ?`.
- `description` may be `None` — store `None` when blank.
- Returns nothing.

## Templates

- **Create:** `templates/edit_expense.html`
  - Extends `base.html`.
  - Identical field set to `add_expense.html`: amount, category (select), date, description.
  - All fields pre-populated with the current expense values passed from the route.
  - Inline error message area shown only when an `error` variable is present.
  - Hidden `<input type="hidden" name="csrf_token">` field.
  - Submit button posts to `{{ url_for('edit_expense', id=expense.id) }}`.
  - A "Cancel" link back to `{{ url_for('profile') }}`.

- **Modify:** `templates/profile.html`
  - Add an "Edit" link on each row of the recent transactions list that points to
    `{{ url_for('edit_expense', id=expense_id) }}` — requires the route to expose the
    expense `id` in the `recent` list.
  - Add a success banner shown when `request.args.get('edited') == '1'`
    (e.g., "Expense updated successfully!"), mirroring the existing `?added=1` banner.

## Files to change

- `app.py`
  - Replace the stub `edit_expense` route (currently returns a plain string) with a
    proper GET+POST handler:
    - `GET`: fetch the expense via `get_expense_by_id(id)`, abort 404 if not found,
      abort 403 if `expense['user_id'] != session['user_id']`, then render
      `edit_expense.html` with the expense data and a CSRF token.
    - `POST`: validate CSRF token (abort 403 on mismatch); read `amount`, `category`,
      `date`, `description` from `request.form`; apply the same validation rules as
      add_expense; call `update_expense`; redirect to `url_for('profile', edited='1')`.
  - Add `get_expense_by_id` and `update_expense` to the import from `database.db`.
  - Extend the `recent` list in the `profile` route to include each expense's `id` so
    the template can generate edit links.

- `database/db.py` — add `get_expense_by_id` and `update_expense` helpers.

- `templates/profile.html`
  - Add the `?edited=1` success banner (mirrors the existing `?added=1` banner).
  - Add "Edit" links to the recent transactions list using each expense's `id`.

## Files to create

- `templates/edit_expense.html` — the pre-filled expense edit form.
- `static/css/edit_expense.css` — page-specific styles (mirrors `add_expense.css` layout).

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only.
- Parameterised queries only — `?` placeholders, never f-strings in SQL.
- Passwords not involved — `werkzeug` hashing not needed here.
- Use CSS variables — never hardcode hex values in `edit_expense.css`.
- All templates extend `base.html`.
- Authorization check is mandatory: verify `expense['user_id'] == session['user_id']`
  before rendering or updating; abort 403 if they do not match.
- Validate `amount` server-side: must be convertible to `float` and greater than `0`.
- Validate `category` server-side: must be one of `_ALLOWED_CATEGORIES`; reject with `abort(400)`.
- Validate `date` server-side: must parse as `YYYY-MM-DD`; reject with an inline error.
- `description` is optional — strip whitespace and store `None` when blank.
- On validation failure re-render the form with the user's submitted values preserved
  (sticky form), not the original DB values.
- No inline SQL in route functions — all DB operations go through `database/db.py`.
- CSRF token must be present in `session` before rendering (generate if missing, same
  pattern as `add_expense`).

## Definition of done

- [ ] `GET /expenses/<id>/edit` renders the form pre-filled with the expense's current values for a logged-in owner.
- [ ] Unauthenticated `GET /expenses/<id>/edit` redirects to `/login`.
- [ ] Requesting a non-existent expense id returns 404.
- [ ] Requesting another user's expense id returns 403.
- [ ] Submitting all valid fields updates the `expenses` row and redirects to `/profile?edited=1`.
- [ ] The profile page shows a success banner when `?edited=1` is present.
- [ ] Submitting with a blank or zero `amount` re-renders the form with an error and the submitted values preserved.
- [ ] Submitting with an invalid `category` returns 400.
- [ ] Submitting with an invalid `date` format re-renders the form with an error.
- [ ] Submitting with a blank `description` stores `NULL` in the database.
- [ ] Unauthenticated `POST /expenses/<id>/edit` redirects to `/login`.
- [ ] An invalid CSRF token on POST returns 403.
- [ ] The profile's recent transactions list shows an "Edit" link for each expense.
- [ ] Clicking "Edit" on a recent transaction navigates to the correct edit form.
- [ ] The Cancel link on the edit form navigates back to `/profile`.
