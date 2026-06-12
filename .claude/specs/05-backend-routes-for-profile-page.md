# Spec: Profile Dashboard Backend Integration

## Overview

Implement backend integration for the Spendly Profile Dashboard.

The profile page should display real user-specific financial data instead of placeholder values or dummy data. The dashboard must fetch and render authenticated user information, transaction history, spending statistics, category breakdowns, and profile insights.

The implementation should integrate with the existing Spendly authentication and expense tracking system while preserving the current UI and theme.

---

## Depends On

* Existing Flask authentication system
* Existing session management (`session["user_id"]`)
* Existing User database table
* Existing Expense/Transaction database table
* Existing database connection utilities (`get_db()`)
* Existing Profile Dashboard UI (`templates/profile.html`)

---

## Routes

### GET `/profile`

Displays the Profile Dashboard for the currently authenticated user.

#### Responsibilities

* Verify authentication
* Fetch user details
* Fetch user transactions
* Calculate dashboard statistics
* Build category breakdown data
* Build recent transaction data
* Render `profile.html`

#### Authentication

If the user is not authenticated:

```python
redirect(url_for("login"))
```

Do not expose profile data to unauthenticated users.

---

## Database Changes

### No Schema Changes Required

Use existing database tables and models.

### Required Database Helpers

#### get_user_by_id(user_id)

Returns authenticated user information.

#### get_expenses_by_user(user_id)

Returns all expenses belonging to the user ordered by newest first.

```sql
SELECT *
FROM expenses
WHERE user_id = ?
ORDER BY date DESC
```

---

## Templates

### Existing Template

* `templates/profile.html`

No new profile templates should be created.

### Template Data

The following variables must be passed to the template:

#### user

Authenticated user object.

#### member_since

Formatted join date.

Example:

```text
June 2026
```

#### stats

Dictionary containing:

```python
{
    "total_spent": 0,
    "transaction_count": 0,
    "avg_transaction": 0,
    "highest_expense": 0,
    "top_category": "",
    "categories_used": 0,
    "avg_daily_spend": 0
}
```

#### categories_data

Category-wise spending breakdown.

Example:

```python
[
    {
        "name": "Food",
        "amount": 4500,
        "percentage": 35
    }
]
```

#### recent_transactions

Latest transactions list.

Example:

```python
[
    {
        "date": "...",
        "category": "...",
        "description": "...",
        "amount": 250
    }
]
```

---

## Files To Change

### app.py

Implement backend logic for:

* GET `/profile`
* Authentication validation
* Statistics calculations
* Category aggregation
* Transaction aggregation
* Template rendering

### database/db.py

Add:

* `get_expenses_by_user(user_id)`

Only if it does not already exist.

### templates/profile.html

Replace any remaining dummy values with dynamic template variables.

---

## Files To Create

None.

---

## New Dependencies

None.

Use only:

* Flask
* sqlite3
* Existing project dependencies

---

## Rules For Implementation

### Security

* Profile data must be visible only to its owner.
* Use session-based authentication.
* Never expose another user's data.

### Database

* Use parameterized SQL queries only.
* No SQL string interpolation.
* No ORM additions.

### Architecture

* Database logic stays inside `database/db.py`
* Route logic stays inside `app.py`
* No inline SQL inside route handlers

### Statistics Calculations

Calculate on the backend:

* Total spent
* Total transactions
* Average transaction value
* Highest expense
* Top spending category
* Categories used
* Average daily spending

### UI Requirements

* Do not modify the Profile Dashboard design.
* Do not modify the website theme.
* Do not modify navigation.
* Do not introduce new profile features.
* Preserve the current dashboard layout.

### Empty State Handling

If a user has no transactions:

* Show ₹0.00 values
* Show empty category state
* Show empty recent transaction state
* Avoid crashes or template errors

---

## Definition Of Done

* [ ] `/profile` loads successfully for authenticated users
* [ ] Unauthenticated users are redirected to `/login`
* [ ] User name, email, and member-since date render correctly
* [ ] Total spent is calculated correctly
* [ ] Transaction count is calculated correctly
* [ ] Average transaction value is calculated correctly
* [ ] Highest expense is calculated correctly
* [ ] Top category is calculated correctly
* [ ] Category breakdown displays real user data
* [ ] Recent transactions display newest transactions first
* [ ] Empty states work correctly when no expenses exist
* [ ] No dummy profile data remains
* [ ] Existing website functionality remains unchanged
* [ ] No import, database, or runtime errors occur
* [ ] All database queries use parameterized SQL
* [ ] Application starts successfully using `python app.py`
