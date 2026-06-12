# Spec: Date Filter for Profile Page

## Overview

Add a date-range filter to the Spendly profile dashboard so users can slice their
spending data by time period. Currently the `/profile` route loads all expenses for
the authenticated user regardless of when they occurred. Step 6 adds a filter bar
with quick-select presets ("7 days", "30 days", "3 months", "This year", "All time")
and a custom from/to date input, passed as query params. All dashboard statistics
(total, count, averages, category breakdown, recent transactions) recalculate against
only the filtered expense set. The existing route signature and template variable
names stay unchanged — the filter is purely additive.

## Depends on

- Step 05 — Profile Dashboard Backend Integration (profile route + all stats logic
  + `get_expenses_by_user` must already exist)

## Routes

- `GET /profile` — extend to accept optional `?from=YYYY-MM-DD&to=YYYY-MM-DD` query
  params — logged-in only. No new route is created; the existing route is widened.

## Database changes

Add one new helper to `database/db.py`:

```
get_expenses_by_user_in_range(user_id, from_date, to_date)
```

- `from_date` and `to_date` are `str | None` in `YYYY-MM-DD` format.
- When both are `None` it returns all expenses (identical behaviour to the existing
  `get_expenses_by_user`).
- When only `from_date` is set, filter `date >= from_date`.
- When only `to_date` is set, filter `date <= to_date`.
- When both are set, filter `date BETWEEN from_date AND to_date`.
- Always ordered `date DESC`.
- Uses `?` placeholders only — no f-string SQL.

No table or column changes are required.

## Templates

- **Modify:** `templates/profile.html`
  - Add a filter bar section above the stats cards.
  - Quick-preset buttons rendered as anchor tags with pre-built query strings:
    `?period=7d`, `?period=30d`, `?period=3m`, `?period=1y`, and `?period=all`.
  - A custom date range form (`<form method="GET" action="{{ url_for('profile') }}">`)
    with two `<input type="date">` fields named `from` and `to` and a submit button.
  - The active preset or current from/to values must be visually highlighted using a
    CSS class so the user can see which filter is active.
  - Filter bar uses existing CSS variables — no hardcoded hex values.

## Files to change

- `app.py` — extend the `/profile` route to:
  1. Read `request.args.get("period")` and `request.args.get("from")` /
     `request.args.get("to")`.
  2. Resolve a `period` shortcut to concrete `from_date` / `to_date` strings using
     `datetime` (already imported).
  3. Call `get_expenses_by_user_in_range` instead of `get_expenses_by_user`.
  4. Pass `active_period`, `filter_from`, and `filter_to` to the template so the
     filter bar can reflect the current selection.
  5. Import `get_expenses_by_user_in_range` from `database.db`.

- `database/db.py` — add `get_expenses_by_user_in_range` helper.

- `templates/profile.html` — add the filter bar UI (see Templates section).

## Files to create

None.

## New dependencies

No new dependencies. Uses only `datetime` from the Python standard library (already
imported in `app.py`) and existing SQLite helpers.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only.
- Parameterised queries only — `?` placeholders, never f-strings in SQL.
- Passwords are not touched — `werkzeug` hashing irrelevant here.
- Use CSS variables — never hardcode hex values in the filter bar.
- All templates extend `base.html`.
- The `period` shortcut resolution happens in `app.py`, not in `database/db.py`.
- Invalid or malformed `from`/`to` values (non-date strings) must be silently ignored
  (fall back to "all time") rather than raising an unhandled exception.
- Do not break the existing route signature or remove any template variables already
  passed to `profile.html`.
- The filter bar must submit via `GET` so the filtered URL is bookmarkable.

## Definition of done

- [ ] Visiting `/profile` with no query params still shows all-time stats (unchanged
      existing behaviour).
- [ ] `?period=7d` filters expenses to the last 7 days and all stats update correctly.
- [ ] `?period=30d` filters to last 30 days.
- [ ] `?period=3m` filters to last 3 months (90 days).
- [ ] `?period=1y` filters to last 365 days.
- [ ] `?period=all` shows all expenses (same as no filter).
- [ ] `?from=2026-06-01&to=2026-06-10` returns only expenses in that range.
- [ ] `?from=2026-06-01` with no `to` returns all expenses from that date onward.
- [ ] `?to=2026-06-10` with no `from` returns all expenses up to that date.
- [ ] A malformed date param (e.g. `?from=not-a-date`) falls back gracefully to
      all-time without a 500 error.
- [ ] The active preset button is visually distinguished from inactive ones.
- [ ] The custom date inputs are pre-populated with the current `from`/`to` values when
      set.
- [ ] Unauthenticated users are still redirected to `/login`.
- [ ] All existing profile stats and layout are unaffected when no filter is active.

