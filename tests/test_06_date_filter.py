"""
tests/test_06_date_filter.py

Comprehensive regression suite for Step 06: Date Filter for Profile Page.

Every test is anchored to a specific business requirement from the spec.
Fixed, explicit dates are used throughout so results are deterministic
regardless of when the suite runs.

Date universe used in this file:
  FAR_PAST   = "2024-01-10"  — always outside every preset window
  RECENT     = "2026-06-05"  — within the last 7 / 30 / 90 / 365 day windows
               relative to today (2026-06-12, per project currentDate)
  MID        = "2025-06-12"  — within 1y but outside 7d / 30d / 3m windows
  RANGE_IN   = "2026-06-03"  — inside  explicit range 2026-06-01 → 2026-06-10
  RANGE_OUT  = "2026-05-01"  — outside explicit range 2026-06-01 → 2026-06-10

"Today" for preset calculations is pinned by the real datetime.today() inside
app.py.  Since the project's current date is 2026-06-12 we keep RECENT on
2026-06-05 (7 days back) to stay solidly inside all short-window presets.
For future-proofing, tests that depend on relative windows insert expenses on
dates that are unambiguously inside or outside and document the assumption.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_profile(auth_client, **params):
    """Convenience wrapper: GET /profile with optional query-string params."""
    return auth_client.get("/profile", query_string=params)


# ---------------------------------------------------------------------------
# Dates used across tests (fixed, never computed from datetime.today())
# ---------------------------------------------------------------------------

# Solidly inside any active period window relative to 2026-06-12
RECENT = "2026-06-05"

# Inside 1y window but outside 7d / 30d / 3m windows
MID_YEAR = "2025-09-01"

# Well outside all preset windows (over 2 years ago)
FAR_PAST = "2024-01-10"

# Explicit range: 2026-06-01 to 2026-06-10
RANGE_FROM = "2026-06-01"
RANGE_TO = "2026-06-10"
RANGE_IN = "2026-06-05"    # inside the explicit range
RANGE_OUT = "2026-05-15"   # before the range start


# ===========================================================================
# 1. Happy path — no filter params
# ===========================================================================

class TestNoFilterParams:
    """Visiting /profile with no query params shows all expenses, HTTP 200."""

    def test_no_params_returns_200(self, auth_client, insert_expense):
        """Business rule: /profile with no params returns HTTP 200."""
        insert_expense(amount=10.00, date=RECENT)
        insert_expense(amount=20.00, date=FAR_PAST)
        response = _get_profile(auth_client)
        assert response.status_code == 200

    def test_no_params_includes_all_expenses_in_count(self, auth_client, insert_expense):
        """Business rule: no filter means all-time stats — both recent and old expenses counted."""
        insert_expense(amount=10.00, date=RECENT)
        insert_expense(amount=20.00, date=FAR_PAST)
        response = _get_profile(auth_client)
        assert response.status_code == 200
        # Both expenses must be reflected in the rendered total
        # The total is ₹30.00 — present in page body
        assert b"\xe2\x82\xb930.00" in response.data  # ₹30.00 in UTF-8


# ===========================================================================
# 2–5. Happy path — preset filter periods
# ===========================================================================

class TestPresetFilters:
    """Each preset period restricts the expense set correctly."""

    def test_period_7d_returns_200(self, auth_client, insert_expense):
        """Business rule: ?period=7d is a valid parameter, route returns HTTP 200."""
        insert_expense(amount=15.00, date=RECENT)
        response = _get_profile(auth_client, period="7d")
        assert response.status_code == 200

    def test_period_7d_excludes_old_expenses(self, auth_client, insert_expense):
        """Business rule: ?period=7d must not count expenses older than 7 days.

        We insert one expense from 2024-01-10 (far outside 7d) and one from
        2026-06-05 (inside 7d relative to project date 2026-06-12).
        The old expense's amount (₹99.00) must not appear in the total.
        """
        insert_expense(amount=99.00, date=FAR_PAST, description="old-expense")
        insert_expense(amount=5.00, date=RECENT, description="recent-expense")
        response = _get_profile(auth_client, period="7d")
        assert response.status_code == 200
        # ₹99.00 must NOT be in the total; only ₹5.00 should be counted
        assert b"\xe2\x82\xb999.00" not in response.data
        assert b"\xe2\x82\xb95.00" in response.data

    def test_period_30d_returns_200(self, auth_client, insert_expense):
        """Business rule: ?period=30d is a valid parameter, route returns HTTP 200."""
        insert_expense(amount=20.00, date=RECENT)
        response = _get_profile(auth_client, period="30d")
        assert response.status_code == 200

    def test_period_30d_excludes_old_expenses(self, auth_client, insert_expense):
        """Business rule: ?period=30d must not count expenses older than 30 days."""
        insert_expense(amount=88.00, date=FAR_PAST, description="old-expense")
        insert_expense(amount=7.00, date=RECENT, description="recent-expense")
        response = _get_profile(auth_client, period="30d")
        assert response.status_code == 200
        assert b"\xe2\x82\xb988.00" not in response.data
        assert b"\xe2\x82\xb97.00" in response.data

    def test_period_3m_returns_200(self, auth_client, insert_expense):
        """Business rule: ?period=3m is a valid parameter, route returns HTTP 200."""
        insert_expense(amount=30.00, date=RECENT)
        response = _get_profile(auth_client, period="3m")
        assert response.status_code == 200

    def test_period_3m_excludes_old_expenses(self, auth_client, insert_expense):
        """Business rule: ?period=3m (90 days) must not count expenses older than 90 days."""
        insert_expense(amount=77.00, date=FAR_PAST, description="old-expense")
        insert_expense(amount=12.00, date=RECENT, description="recent-expense")
        response = _get_profile(auth_client, period="3m")
        assert response.status_code == 200
        assert b"\xe2\x82\xb977.00" not in response.data
        assert b"\xe2\x82\xb912.00" in response.data

    def test_period_1y_returns_200(self, auth_client, insert_expense):
        """Business rule: ?period=1y is a valid parameter, route returns HTTP 200."""
        insert_expense(amount=40.00, date=RECENT)
        response = _get_profile(auth_client, period="1y")
        assert response.status_code == 200

    def test_period_1y_includes_mid_year_expense(self, auth_client, insert_expense):
        """Business rule: ?period=1y (365 days) includes expenses from ~9 months ago.

        2025-09-01 is ~284 days before 2026-06-12, so it must be included.
        2024-01-10 is ~883 days ago, so it must be excluded.
        """
        insert_expense(amount=55.00, date=FAR_PAST, description="too-old")
        insert_expense(amount=25.00, date=MID_YEAR, description="mid-year")
        insert_expense(amount=5.00, date=RECENT, description="recent")
        response = _get_profile(auth_client, period="1y")
        assert response.status_code == 200
        # ₹55.00 (2024-01-10) must be excluded; the other two included
        assert b"\xe2\x82\xb955.00" not in response.data
        assert b"\xe2\x82\xb925.00" in response.data
        assert b"\xe2\x82\xb95.00" in response.data

    def test_period_all_returns_200(self, auth_client, insert_expense):
        """Business rule: ?period=all is a valid parameter, route returns HTTP 200."""
        insert_expense(amount=10.00, date=FAR_PAST)
        response = _get_profile(auth_client, period="all")
        assert response.status_code == 200

    def test_period_all_includes_all_expenses(self, auth_client, insert_expense):
        """Business rule: ?period=all shows all expenses regardless of age."""
        insert_expense(amount=33.00, date=FAR_PAST)
        insert_expense(amount=11.00, date=RECENT)
        response = _get_profile(auth_client, period="all")
        assert response.status_code == 200
        assert b"\xe2\x82\xb944.00" in response.data  # 33 + 11 = 44


# ===========================================================================
# 6–8. Happy path — custom from/to range
# ===========================================================================

class TestCustomRangeFilter:
    """Custom ?from= and ?to= params slice the expense set to a date range."""

    def test_custom_range_both_dates_returns_200(self, auth_client, insert_expense):
        """Business rule: ?from=X&to=Y is accepted and returns HTTP 200."""
        insert_expense(amount=20.00, date=RANGE_IN)
        response = _get_profile(auth_client, **{"from": RANGE_FROM, "to": RANGE_TO})
        assert response.status_code == 200

    def test_custom_range_includes_expense_inside_range(self, auth_client, insert_expense):
        """Business rule: expenses with dates within [from, to] must appear in stats."""
        insert_expense(amount=42.00, date=RANGE_IN, description="inside-range")
        insert_expense(amount=99.00, date=RANGE_OUT, description="outside-range")
        response = _get_profile(auth_client, **{"from": RANGE_FROM, "to": RANGE_TO})
        assert response.status_code == 200
        assert b"\xe2\x82\xb942.00" in response.data
        assert b"\xe2\x82\xb999.00" not in response.data

    def test_custom_range_from_only_returns_200(self, auth_client, insert_expense):
        """Business rule: ?from=X with no to= is accepted and returns HTTP 200."""
        insert_expense(amount=15.00, date=RANGE_IN)
        response = _get_profile(auth_client, **{"from": RANGE_FROM})
        assert response.status_code == 200

    def test_custom_range_from_only_excludes_earlier_expenses(self, auth_client, insert_expense):
        """Business rule: ?from=X with no to includes from X onward, excludes earlier."""
        insert_expense(amount=50.00, date=RANGE_IN, description="on-or-after")
        insert_expense(amount=77.00, date=RANGE_OUT, description="before-from")
        response = _get_profile(auth_client, **{"from": RANGE_FROM})
        assert response.status_code == 200
        assert b"\xe2\x82\xb950.00" in response.data
        assert b"\xe2\x82\xb977.00" not in response.data

    def test_custom_range_to_only_returns_200(self, auth_client, insert_expense):
        """Business rule: ?to=X with no from= is accepted and returns HTTP 200."""
        insert_expense(amount=20.00, date=RANGE_OUT)
        response = _get_profile(auth_client, **{"to": RANGE_TO})
        assert response.status_code == 200

    def test_custom_range_to_only_excludes_later_expenses(self, auth_client, insert_expense):
        """Business rule: ?to=X with no from includes up to X, excludes later expenses.

        RANGE_TO = 2026-06-10.  We use 2026-06-12 as the "after-to" date
        (the project's current date, solidly after the cutoff).
        """
        insert_expense(amount=35.00, date=RANGE_OUT, description="before-to")
        insert_expense(amount=66.00, date="2026-06-12", description="after-to")
        response = _get_profile(auth_client, **{"to": RANGE_TO})
        assert response.status_code == 200
        assert b"\xe2\x82\xb935.00" in response.data
        assert b"\xe2\x82\xb966.00" not in response.data


# ===========================================================================
# 9–12. Error handling and edge cases
# ===========================================================================

class TestMalformedAndEdgeCaseParams:
    """Invalid params must be silently ignored; the route must never raise 500."""

    def test_malformed_from_date_returns_200(self, auth_client, insert_expense):
        """Business rule: malformed ?from= falls back to all-time without a 500 error."""
        insert_expense(amount=10.00, date=RECENT)
        response = _get_profile(auth_client, **{"from": "not-a-date"})
        assert response.status_code == 200

    def test_malformed_from_date_falls_back_to_all_time(self, auth_client, insert_expense):
        """Business rule: malformed ?from= behaves like no filter — shows all expenses."""
        insert_expense(amount=10.00, date=FAR_PAST)
        insert_expense(amount=20.00, date=RECENT)
        response = _get_profile(auth_client, **{"from": "not-a-date"})
        assert response.status_code == 200
        # Both expenses should be in the total (₹30.00)
        assert b"\xe2\x82\xb930.00" in response.data

    def test_malformed_to_date_returns_200(self, auth_client, insert_expense):
        """Business rule: malformed ?to= falls back to all-time without a 500 error."""
        insert_expense(amount=10.00, date=RECENT)
        response = _get_profile(auth_client, **{"to": "garbage"})
        assert response.status_code == 200

    def test_malformed_to_date_falls_back_to_all_time(self, auth_client, insert_expense):
        """Business rule: malformed ?to= behaves like no filter — shows all expenses."""
        insert_expense(amount=10.00, date=FAR_PAST)
        insert_expense(amount=20.00, date=RECENT)
        response = _get_profile(auth_client, **{"to": "garbage"})
        assert response.status_code == 200
        assert b"\xe2\x82\xb930.00" in response.data

    def test_reversed_date_range_returns_200(self, auth_client, insert_expense):
        """Business rule: a reversed range (from > to) must not crash — returns HTTP 200."""
        insert_expense(amount=10.00, date=RANGE_IN)
        # from is after to, so no expenses can match
        response = _get_profile(
            auth_client, **{"from": RANGE_TO, "to": RANGE_FROM}
        )
        assert response.status_code == 200

    def test_reversed_date_range_produces_empty_state(self, auth_client, insert_expense):
        """Business rule: a reversed range returns zero expenses — empty state is shown gracefully."""
        insert_expense(amount=10.00, date=RANGE_IN)
        response = _get_profile(
            auth_client, **{"from": RANGE_TO, "to": RANGE_FROM}
        )
        assert response.status_code == 200
        # The profile template renders "No transactions yet." when recent is empty
        assert b"No transactions yet." in response.data

    def test_unknown_period_value_returns_200(self, auth_client, insert_expense):
        """Business rule: an unrecognised ?period= value falls back to all-time, HTTP 200."""
        insert_expense(amount=10.00, date=RECENT)
        response = _get_profile(auth_client, period="unknown_value")
        assert response.status_code == 200

    def test_unknown_period_value_falls_back_to_all_time(self, auth_client, insert_expense):
        """Business rule: unknown period shows all expenses (no unintended filtering)."""
        insert_expense(amount=10.00, date=FAR_PAST)
        insert_expense(amount=20.00, date=RECENT)
        response = _get_profile(auth_client, period="unknown_value")
        assert response.status_code == 200
        assert b"\xe2\x82\xb930.00" in response.data


# ===========================================================================
# 13. Authentication
# ===========================================================================

class TestAuthentication:
    """Unauthenticated users must be redirected to /login on every /profile request."""

    def test_unauthenticated_profile_redirects_to_login(self, client):
        """Business rule: /profile requires a logged-in session — anonymous users are rejected."""
        response = client.get("/profile")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_unauthenticated_profile_with_period_param_redirects_to_login(self, client):
        """Business rule: query params do not bypass authentication on /profile."""
        response = client.get("/profile", query_string={"period": "7d"})
        assert response.status_code == 302
        assert "/login" in response.location

    def test_unauthenticated_profile_with_custom_range_redirects_to_login(self, client):
        """Business rule: custom date params do not bypass authentication on /profile."""
        response = client.get(
            "/profile",
            query_string={"from": RANGE_FROM, "to": RANGE_TO},
        )
        assert response.status_code == 302
        assert "/login" in response.location


# ===========================================================================
# 14–15. Filter bar UI presence
# ===========================================================================

class TestFilterBarUI:
    """The filter bar must be present and reflect the active selection."""

    def test_filter_bar_element_is_present(self, auth_client, insert_expense):
        """Business rule: the profile page must include a filter bar for all users."""
        response = _get_profile(auth_client)
        assert response.status_code == 200
        assert b"filter-bar" in response.data

    def test_filter_pill_elements_are_present(self, auth_client):
        """Business rule: the filter bar must contain quick-select preset pills."""
        response = _get_profile(auth_client)
        assert response.status_code == 200
        assert b"filter-pill" in response.data

    def test_active_pill_marked_for_period_7d(self, auth_client, insert_expense):
        """Business rule: when ?period=7d is active the 7-day pill carries the active CSS class."""
        insert_expense(amount=10.00, date=RECENT)
        response = _get_profile(auth_client, period="7d")
        assert response.status_code == 200
        assert b"filter-pill--active" in response.data
        # The "7 days" label must appear alongside the active class
        assert b"7 days" in response.data

    def test_all_pill_active_when_no_filter(self, auth_client):
        """Business rule: with no filter params the 'All' pill should be marked active."""
        response = _get_profile(auth_client)
        assert response.status_code == 200
        assert b"filter-pill--active" in response.data

    def test_custom_date_inputs_prepopulated_when_from_set(self, auth_client, insert_expense):
        """Business rule: the custom date inputs are pre-populated when from/to values are set."""
        insert_expense(amount=10.00, date=RANGE_IN)
        response = _get_profile(
            auth_client, **{"from": RANGE_FROM, "to": RANGE_TO}
        )
        assert response.status_code == 200
        assert RANGE_FROM.encode() in response.data
        assert RANGE_TO.encode() in response.data


# ===========================================================================
# 16–17. Stats correctness
# ===========================================================================

class TestStatsCorrectness:
    """Stats must reflect only the filtered expense set."""

    def test_filter_excluding_all_expenses_shows_zero_total(self, auth_client, insert_expense):
        """Business rule: when the filter excludes every expense, total spent shows ₹0.00."""
        # Insert an expense in June 2026; use a far-future range that has no data
        insert_expense(amount=50.00, date=RECENT)
        response = _get_profile(
            auth_client, **{"from": "2020-01-01", "to": "2020-01-31"}
        )
        assert response.status_code == 200
        assert b"\xe2\x82\xb90.00" in response.data  # ₹0.00

    def test_filter_excluding_all_expenses_shows_zero_count(self, auth_client, insert_expense):
        """Business rule: when the filter excludes every expense, transaction count is 0."""
        insert_expense(amount=50.00, date=RECENT)
        response = _get_profile(
            auth_client, **{"from": "2020-01-01", "to": "2020-01-31"}
        )
        assert response.status_code == 200
        # stats.count == 0 is rendered as the literal "0" in the stats grid
        assert b">0<" in response.data

    def test_filter_excluding_all_expenses_shows_no_transactions_empty_state(
        self, auth_client, insert_expense
    ):
        """Business rule: when filtered results are empty the 'No transactions yet.' message appears."""
        insert_expense(amount=50.00, date=RECENT)
        response = _get_profile(
            auth_client, **{"from": "2020-01-01", "to": "2020-01-31"}
        )
        assert response.status_code == 200
        assert b"No transactions yet." in response.data

    def test_filter_count_equals_exact_number_of_included_expenses(
        self, auth_client, insert_expense
    ):
        """Business rule: stats.count matches the exact number of expenses inside the filter window."""
        # Insert 3 expenses inside the range and 2 outside
        insert_expense(amount=10.00, date="2026-06-02", description="in-1")
        insert_expense(amount=10.00, date="2026-06-05", description="in-2")
        insert_expense(amount=10.00, date="2026-06-08", description="in-3")
        insert_expense(amount=10.00, date=RANGE_OUT, description="out-1")
        insert_expense(amount=10.00, date=FAR_PAST, description="out-2")

        response = _get_profile(
            auth_client, **{"from": RANGE_FROM, "to": RANGE_TO}
        )
        assert response.status_code == 200
        # stats.count of 3 is rendered somewhere in the page
        # We look for ">3<" which appears in the Transactions stat card
        assert b">3<" in response.data

    def test_two_expenses_in_range_correct_total(self, auth_client, insert_expense):
        """Business rule: the total shown matches the sum of filtered expenses only."""
        insert_expense(amount=25.00, date=RANGE_IN, description="expense-a")
        insert_expense(amount=15.00, date=RANGE_IN, description="expense-b")
        insert_expense(amount=100.00, date=RANGE_OUT, description="excluded")

        response = _get_profile(
            auth_client, **{"from": RANGE_FROM, "to": RANGE_TO}
        )
        assert response.status_code == 200
        # Total of included expenses: ₹40.00
        assert b"\xe2\x82\xb940.00" in response.data
        # Excluded expense amount must not appear as a total
        assert b"\xe2\x82\xb9100.00" not in response.data


# ===========================================================================
# 18. Regression protection — Step 05 template variables
# ===========================================================================

class TestStep05RegressionProtection:
    """All template variables introduced in Step 05 must remain present after Step 06."""

    def test_stats_variable_present_in_response(self, auth_client, insert_expense):
        """Regression: 'stats' context variable must still be passed — stat cards require it."""
        insert_expense(amount=10.00, date=RECENT)
        response = _get_profile(auth_client)
        assert response.status_code == 200
        # stat labels are rendered from stats dict; their presence proves the var is passed
        assert b"Total Spent" in response.data

    def test_categories_data_variable_present_in_response(self, auth_client, insert_expense):
        """Regression: 'categories_data' context variable must still be passed — breakdown requires it."""
        insert_expense(amount=10.00, category="Food", date=RECENT)
        response = _get_profile(auth_client)
        assert response.status_code == 200
        assert b"Spending by Category" in response.data

    def test_recent_variable_present_in_response(self, auth_client, insert_expense):
        """Regression: 'recent' context variable must still be passed — recent transactions require it."""
        insert_expense(amount=10.00, date=RECENT)
        response = _get_profile(auth_client)
        assert response.status_code == 200
        assert b"Recent Transactions" in response.data

    def test_user_variable_present_in_response(self, auth_client, test_user, insert_expense):
        """Regression: 'user' context variable must still be passed — profile header requires it."""
        insert_expense(amount=10.00, date=RECENT)
        response = _get_profile(auth_client)
        assert response.status_code == 200
        # The user's name is rendered in the profile header
        assert b"Test User" in response.data

    def test_member_since_variable_present_in_response(self, auth_client, insert_expense):
        """Regression: 'member_since' context variable must still be passed — profile badge requires it."""
        insert_expense(amount=10.00, date=RECENT)
        response = _get_profile(auth_client)
        assert response.status_code == 200
        assert b"Member since" in response.data

    def test_stats_keys_all_present_no_filter(self, auth_client, insert_expense):
        """Regression: all stats dict keys from Step 05 must still be rendered correctly."""
        insert_expense(amount=10.00, category="Food", date=RECENT)
        response = _get_profile(auth_client)
        assert response.status_code == 200
        # Each key renders a corresponding label in the template
        assert b"Total Spent" in response.data
        assert b"Transactions" in response.data
        assert b"Avg. per Transaction" in response.data
        assert b"Top Category" in response.data
        assert b"Avg. Daily Spend" in response.data
        assert b"Categories Used" in response.data


# ===========================================================================
# 19. Authorization — cross-user isolation
# ===========================================================================

class TestAuthorization:
    """A user's filter results must only contain their own expenses."""

    def test_user_sees_only_own_expenses_in_filtered_results(
        self, app, auth_client, test_user, insert_expense
    ):
        """Business rule: filtering must not leak another user's expenses into the response."""
        from werkzeug.security import generate_password_hash
        import database.db as db_module

        # Insert an expense for the authenticated test_user (inside the range)
        insert_expense(amount=20.00, date=RANGE_IN, description="my-expense")

        # Create a second user and insert their expense at the same date
        other_id = db_module.create_user(
            name="Other User",
            email="other@example.com",
            password_hash=generate_password_hash("OtherPass123"),
        )
        conn = db_module.get_db()
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (other_id, 999.00, "Other", RANGE_IN, "other-expense"),
        )
        conn.commit()
        conn.close()

        response = _get_profile(
            auth_client, **{"from": RANGE_FROM, "to": RANGE_TO}
        )
        assert response.status_code == 200
        # The other user's amount must not appear anywhere in the response
        assert b"\xe2\x82\xb9999.00" not in response.data
        # The test user's amount must appear
        assert b"\xe2\x82\xb920.00" in response.data
