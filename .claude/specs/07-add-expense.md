# Spec: Add Expense

## Overview

Step 7 activates the stub `GET /expenses/add` route by converting it into a full
GET+POST flow that lets authenticated users record a new expense. The user fills out
a form with amount, category, date, and an optional description; on valid submission
the expense is inserted into the `expenses` table and the user is redirected to their
profile dashboard with a success indicator. Invalid or missing fields re-render the
form with a clear inline error message. This is the first user-facing write operation
in Spendly and is a prerequisite for Edit and Delete (Steps 8–9).

## Depends on

- Step 01 — Database Setup (`expenses` table and `get_db()` must exist)
- Step 05 — Profile Dashboard Backend Integration (the profile redirect target must work)

## Routes

- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert the expense, then redirect to `/profile?added=1` — logged-in only

## Database changes

No new tables or columns. The `expenses` table already has all required columns
(`user_id`, `amount`, `category`, `date`, `description`).

Add one new helper to `database/db.py`:

```
create_expense(user_id, amount, category, date, description)
```

- Inserts a row into `expenses` using only `?` placeholders.
- `amount` is stored as `REAL`.
- `description` may be `None` or an empty string (store `None` when blank).
- Returns the new expense's `id` (`cursor.lastrowid`).

## Templates

- **Create:** `templates/add_expense.html`
  - Extends `base.html`.
  - A single-column form with fields for:
    - `amount` — `<input type="number" step="0.01" min="0.01" required>`
    - `category` — `<select required>` with options: Food, Transport, Bills, Health,
      Entertainment, Shopping, Other
    - `date` — `<input type="date" required>` defaulting to today's date
    - `description` — `<input type="text">` (optional)
  - Inline error message area shown only when an `error` variable is passed from the route.
  - Submit button posts to `{{ url_for('add_expense') }}`.
  - A "Cancel" link back to `{{ url_for('profile') }}`.

## Files to change

- `app.py`
  - Replace the stub `add_expense` route (currently returns a plain string) with a
    proper GET/POST handler:
    - `GET`: render `add_expense.html`
    - `POST`: read `amount`, `category`, `date`, `description` from `request.form`;
      validate; call `create_expense`; redirect to `url_for('profile', added='1')`.
  - Add `create_expense` to the import from `database.db`.

- `database/db.py` — add `create_expense` helper.

- `templates/profile.html` — add a success banner that appears when
  `request.args.get('added') == '1'` (e.g., "Expense added successfully!"), shown
  above the stats section and auto-hidden after a few seconds via a small inline JS
  snippet (vanilla only).

## Files to create

- `templates/add_expense.html` — the expense entry form.
- `static/css/add_expense.css` — page-specific styles for the form layout.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only.
- Parameterised queries only — `?` placeholders, never f-strings in SQL.
- Passwords not involved — `werkzeug` hashing not needed here.
- Use CSS variables — never hardcode hex values in `add_expense.css`.
- All templates extend `base.html`.
- Validate `amount` server-side: must be convertible to `float` and greater than `0`.
- Validate `category` server-side: must be one of the allowed values (Food, Transport,
  Bills, Health, Entertainment, Shopping, Other) — reject anything else with `abort(400)`.
- Validate `date` server-side: must parse as `YYYY-MM-DD`; reject malformed values
  with an inline error, not a bare `abort`.
- `description` is optional — strip whitespace and store `None` when blank.
- The route function must contain no inline SQL — all DB operations go through
  `database/db.py` helpers.
- On validation failure re-render the form with the user's previously entered values
  preserved (sticky form).

## Definition of done

- [ ] `GET /expenses/add` renders the form for a logged-in user.
- [ ] Unauthenticated `GET /expenses/add` redirects to `/login`.
- [ ] Submitting all valid fields inserts a row into `expenses` and redirects to `/profile?added=1`.
- [ ] The profile page shows a success banner when `?added=1` is present.
- [ ] Submitting with a blank or zero `amount` re-renders the form with an error message.
- [ ] Submitting with a missing `category` re-renders the form with an error message.
- [ ] Submitting with an invalid `date` format re-renders the form with an error message.
- [ ] Submitting with a valid `description` stores it; submitting with a blank description stores `NULL`.
- [ ] The new expense immediately appears in the recent transactions list on `/profile`.
- [ ] The profile stats (total, count, avg) reflect the newly added expense.
- [ ] Unauthenticated `POST /expenses/add` redirects to `/login`.
- [ ] The Cancel link on the form navigates back to `/profile`.
