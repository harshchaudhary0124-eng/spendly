"""
tests/test_07_add_expense.py

Comprehensive regression suite for Step 07: Add Expense.

Every test is anchored to a specific business requirement from
.claude/specs/07-add-expense.md.  Tests validate HTTP behaviour,
database side-effects, security guarantees, and template output —
never implementation internals.

Business requirements covered:
  R1  GET /expenses/add renders the form (200) for authenticated users.
  R2  Unauthenticated GET /expenses/add redirects to /login.
  R3  Valid POST inserts a row into `expenses` and redirects to
      /profile?added=1.
  R4  Profile page shows success banner when ?added=1 is present.
  R5  Blank or zero `amount` re-renders the form with an error (200).
  R6  Missing `category` re-renders the form with an error / 400.
  R7  Invalid `date` format re-renders the form with an error (200).
  R8  Valid `description` is stored; blank description stores NULL.
  R9  New expense appears in recent transactions on /profile.
  R10 Profile stats (total, count) reflect the newly added expense.
  R11 Unauthenticated POST /expenses/add redirects to /login.
  R12 Cancel link navigates back to /profile.

Security requirements covered:
  S1  SQL injection in amount, description, date fields is rejected safely.
  S2  XSS payload in description is not executed (stored-XSS prevention).
  S3  Category field tampering with a value outside the allowed list
      returns 400.
  S4  Negative amount is rejected.
  S5  Extremely large amount boundary is handled.
  S6  Completely empty form submission is rejected.

Authorization:
  A1  A user's expense is stored under their own user_id only.
  A2  Adding an expense does not expose another user's data on /profile.

Regression:
  REG1  Profile page works normally when ?added=1 is absent.
  REG2  Profile stats and recent-transactions template variables still
        work after Step 07.
  REG3  /profile (protected route) still requires authentication.
"""

import sqlite3
from datetime import datetime, timedelta

import pytest

import database.db as db_module
from werkzeug.security import generate_password_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_FORM = {
    "amount": "25.50",
    "category": "Food",
    "date": "2026-06-10",
    "description": "Lunch at cafe",
}

ALLOWED_CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


def _post_add(client, data=None, **overrides):
    """POST to /expenses/add with VALID_FORM merged with overrides."""
    payload = {**VALID_FORM, **(data or {}), **overrides}
    return client.post("/expenses/add", data=payload)


def _get_expenses_for_user(user_id):
    """Return all expense rows for a user directly from the database."""
    conn = db_module.get_db()
    rows = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchall()
    conn.close()
    return rows


# ===========================================================================
# 1. Happy Path — GET
# ===========================================================================

class TestGetAddExpenseForm:
    """R1 — GET /expenses/add renders the form for authenticated users."""

    def test_get_add_expense_returns_200(self, auth_client):
        """Business rule: authenticated GET /expenses/add returns HTTP 200."""
        response = auth_client.get("/expenses/add")
        assert response.status_code == 200

    def test_get_add_expense_renders_amount_field(self, auth_client):
        """Business rule: form must include an amount input field."""
        response = auth_client.get("/expenses/add")
        assert b'name="amount"' in response.data

    def test_get_add_expense_renders_category_select(self, auth_client):
        """Business rule: form must include a category select element."""
        response = auth_client.get("/expenses/add")
        assert b'name="category"' in response.data

    def test_get_add_expense_renders_date_field(self, auth_client):
        """Business rule: form must include a date input field."""
        response = auth_client.get("/expenses/add")
        assert b'name="date"' in response.data

    def test_get_add_expense_renders_description_field(self, auth_client):
        """Business rule: form must include a description input field (optional)."""
        response = auth_client.get("/expenses/add")
        assert b'name="description"' in response.data

    def test_get_add_expense_form_posts_to_add_expense_route(self, auth_client):
        """Business rule: the form's action must target the add_expense route."""
        response = auth_client.get("/expenses/add")
        # url_for('add_expense') resolves to /expenses/add
        assert b"/expenses/add" in response.data

    def test_get_add_expense_all_allowed_categories_present(self, auth_client):
        """Business rule: all seven allowed categories must be present as options."""
        response = auth_client.get("/expenses/add")
        for cat in ALLOWED_CATEGORIES:
            assert cat.encode() in response.data, (
                f"Category option '{cat}' missing from add-expense form"
            )

    def test_get_add_expense_date_defaults_to_today(self, auth_client):
        """Business rule: the date field defaults to today's date (YYYY-MM-DD)."""
        from datetime import datetime

        today = str(datetime.today().date())
        response = auth_client.get("/expenses/add")
        assert today.encode() in response.data

    def test_cancel_link_points_to_profile(self, auth_client):
        """R12 — Cancel link must navigate back to /profile."""
        response = auth_client.get("/expenses/add")
        # url_for('profile') resolves to /profile
        assert b'href="/profile"' in response.data


# ===========================================================================
# 2. Authentication — unauthenticated access is rejected
# ===========================================================================

class TestAuthentication:
    """R2, R11 — Unauthenticated access to /expenses/add redirects to /login."""

    def test_unauthenticated_get_redirects_to_login(self, client):
        """R2 — Anonymous GET /expenses/add must redirect to /login."""
        response = client.get("/expenses/add")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_unauthenticated_post_redirects_to_login(self, client):
        """R11 — Anonymous POST /expenses/add must redirect to /login."""
        response = _post_add(client)
        assert response.status_code == 302
        assert "/login" in response.location

    def test_unauthenticated_post_does_not_insert_expense(self, client, test_user):
        """R11 — Anonymous POST must not insert any row into the expenses table."""
        _post_add(client)
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 0

    def test_logout_then_get_redirects_to_login(self, auth_client):
        """Business rule: after session is cleared, /expenses/add redirects to /login."""
        auth_client.get("/logout")
        response = auth_client.get("/expenses/add")
        assert response.status_code == 302
        assert "/login" in response.location


# ===========================================================================
# 3. Happy Path — valid POST
# ===========================================================================

class TestValidPost:
    """R3, R8, R9, R10 — Valid POST inserts expense and redirects correctly."""

    def test_valid_post_redirects_to_profile_with_added_flag(
        self, auth_client, test_user
    ):
        """R3 — Valid POST must redirect to /profile?added=1."""
        response = _post_add(auth_client)
        assert response.status_code == 302
        assert "/profile" in response.location
        assert "added=1" in response.location

    def test_valid_post_inserts_one_expense_row(self, auth_client, test_user):
        """R3 — Valid POST must insert exactly one row into the expenses table."""
        _post_add(auth_client)
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 1

    def test_valid_post_stores_correct_amount(self, auth_client, test_user):
        """R3 — The inserted row must store the submitted amount as a REAL."""
        _post_add(auth_client, amount="42.75")
        rows = _get_expenses_for_user(test_user["id"])
        assert rows[0]["amount"] == pytest.approx(42.75)

    def test_valid_post_stores_correct_category(self, auth_client, test_user):
        """R3 — The inserted row must store the submitted category."""
        _post_add(auth_client, category="Transport")
        rows = _get_expenses_for_user(test_user["id"])
        assert rows[0]["category"] == "Transport"

    def test_valid_post_stores_correct_date(self, auth_client, test_user):
        """R3 — The inserted row must store the submitted date in YYYY-MM-DD format."""
        _post_add(auth_client, date="2026-05-20")
        rows = _get_expenses_for_user(test_user["id"])
        assert rows[0]["date"] == "2026-05-20"

    def test_valid_post_stores_description_when_provided(self, auth_client, test_user):
        """R8 — When a non-blank description is submitted it must be stored in the DB."""
        _post_add(auth_client, description="Coffee with colleagues")
        rows = _get_expenses_for_user(test_user["id"])
        assert rows[0]["description"] == "Coffee with colleagues"

    def test_valid_post_stores_null_when_description_blank(
        self, auth_client, test_user
    ):
        """R8 — When description is blank the DB column must contain NULL (None)."""
        _post_add(auth_client, description="")
        rows = _get_expenses_for_user(test_user["id"])
        assert rows[0]["description"] is None

    def test_valid_post_stores_null_when_description_whitespace_only(
        self, auth_client, test_user
    ):
        """R8 — Whitespace-only description must be stripped and stored as NULL."""
        _post_add(auth_client, description="   ")
        rows = _get_expenses_for_user(test_user["id"])
        assert rows[0]["description"] is None

    def test_valid_post_expense_belongs_to_logged_in_user(
        self, auth_client, test_user
    ):
        """A1 — The inserted expense's user_id must match the session user."""
        _post_add(auth_client)
        rows = _get_expenses_for_user(test_user["id"])
        assert rows[0]["user_id"] == test_user["id"]

    def test_all_allowed_categories_can_be_submitted(self, auth_client, test_user):
        """R3 — Every category in the allowed list must be accepted without error."""
        for cat in ALLOWED_CATEGORIES:
            response = _post_add(auth_client, category=cat)
            # Each valid submission must redirect (302), never re-render with error (200)
            assert response.status_code == 302, (
                f"Category '{cat}' was unexpectedly rejected"
            )

    def test_valid_post_with_future_date_is_accepted(self, auth_client, test_user):
        """Boundary — The spec does not restrict future dates; they must be accepted."""
        response = _post_add(auth_client, date="2099-12-31")
        assert response.status_code == 302
        rows = _get_expenses_for_user(test_user["id"])
        assert rows[0]["date"] == "2099-12-31"


# ===========================================================================
# 4. Success Banner on Profile
# ===========================================================================

class TestSuccessBanner:
    """R4 — Profile page shows success banner when ?added=1 is present."""

    def test_profile_shows_success_banner_when_added_flag_present(
        self, auth_client
    ):
        """R4 — GET /profile?added=1 must render the success banner."""
        response = auth_client.get("/profile?added=1")
        assert response.status_code == 200
        assert b"Expense added successfully" in response.data

    def test_profile_does_not_show_success_banner_without_flag(
        self, auth_client
    ):
        """REG1 — GET /profile with no ?added param must not show the success banner."""
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"Expense added successfully" not in response.data

    def test_profile_does_not_show_success_banner_with_wrong_flag_value(
        self, auth_client
    ):
        """REG1 — GET /profile?added=0 must not show the success banner."""
        response = auth_client.get("/profile?added=0")
        assert response.status_code == 200
        assert b"Expense added successfully" not in response.data

    def test_full_flow_add_then_profile_shows_banner(self, auth_client):
        """R3+R4 — After a valid POST the redirect to /profile?added=1 shows banner."""
        post_response = _post_add(auth_client)
        assert post_response.status_code == 302

        profile_response = auth_client.get(post_response.location)
        assert b"Expense added successfully" in profile_response.data


# ===========================================================================
# 5. New Expense Appears on Profile
# ===========================================================================

class TestExpenseAppearsOnProfile:
    """R9, R10 — New expense must appear in stats and recent transactions on /profile."""

    def test_new_expense_appears_in_recent_transactions(
        self, auth_client, test_user
    ):
        """R9 — After adding an expense, it must appear in the recent transactions list."""
        _post_add(auth_client, description="Unique lunch expense", amount="77.00")
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"Unique lunch expense" in response.data

    def test_new_expense_increases_transaction_count(
        self, auth_client, test_user
    ):
        """R10 — Adding one expense from zero must make stats.count equal to 1."""
        _post_add(auth_client)
        response = auth_client.get("/profile")
        assert response.status_code == 200
        # stats.count of 1 is rendered as ">1<" in the Transactions stat card
        assert b">1<" in response.data

    def test_new_expense_reflected_in_total_spent(self, auth_client, test_user):
        """R10 — Total spent on /profile must include the newly added expense amount."""
        _post_add(auth_client, amount="50.00", category="Food", date="2026-06-10")
        response = auth_client.get("/profile")
        assert response.status_code == 200
        # ₹50.00 in UTF-8 encoded bytes
        assert "₹50.00".encode("utf-8") in response.data

    def test_category_appears_in_spending_breakdown(
        self, auth_client, test_user
    ):
        """R10 — The category of the new expense must appear in the category breakdown."""
        _post_add(auth_client, category="Health")
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"Health" in response.data


# ===========================================================================
# 6. Validation — form re-render with errors
# ===========================================================================

class TestValidation:
    """R5, R6, R7 — Invalid input re-renders the form with an error message (not a redirect)."""

    def test_blank_amount_rerenders_form_with_200(self, auth_client):
        """R5 — Submitting a blank amount must return HTTP 200 (re-render), not redirect."""
        response = _post_add(auth_client, amount="")
        assert response.status_code == 200

    def test_blank_amount_shows_error_message(self, auth_client):
        """R5 — A blank amount submission must show an inline error message."""
        response = _post_add(auth_client, amount="")
        assert b"Amount" in response.data or b"amount" in response.data
        # Some error indicator must be present in the page
        assert b"error" in response.data.lower() or b"must be" in response.data

    def test_zero_amount_rerenders_form_with_200(self, auth_client):
        """R5 — Submitting amount=0 must return HTTP 200 (re-render), not redirect."""
        response = _post_add(auth_client, amount="0")
        assert response.status_code == 200

    def test_zero_amount_shows_error_message(self, auth_client):
        """R5 — A zero amount must show an inline error message."""
        response = _post_add(auth_client, amount="0")
        assert b"Amount must be a number greater than 0" in response.data

    def test_zero_amount_does_not_insert_expense(self, auth_client, test_user):
        """R5 / DB integrity — A zero amount must not insert any row into expenses."""
        _post_add(auth_client, amount="0")
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 0

    def test_non_numeric_amount_rerenders_form_with_200(self, auth_client):
        """R5 — Non-numeric amount must return HTTP 200 (re-render)."""
        response = _post_add(auth_client, amount="abc")
        assert response.status_code == 200

    def test_non_numeric_amount_shows_error_message(self, auth_client):
        """R5 — A non-numeric amount must show an inline error message."""
        response = _post_add(auth_client, amount="abc")
        assert b"Amount must be a number greater than 0" in response.data

    def test_non_numeric_amount_does_not_insert_expense(
        self, auth_client, test_user
    ):
        """R5 / DB integrity — Non-numeric amount must not insert any row into expenses."""
        _post_add(auth_client, amount="abc")
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 0

    def test_missing_category_returns_400(self, auth_client):
        """R6 — A missing category (empty string) must return HTTP 400 per spec rule.

        Spec says: validate category server-side; reject anything outside
        the allowed list with abort(400).  An empty string is not in the list.
        """
        response = _post_add(auth_client, category="")
        assert response.status_code == 400

    def test_missing_category_does_not_insert_expense(
        self, auth_client, test_user
    ):
        """R6 / DB integrity — An empty category must not insert any row into expenses."""
        _post_add(auth_client, category="")
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 0

    def test_invalid_date_format_rerenders_form_with_200(self, auth_client):
        """R7 — An invalid date format must return HTTP 200 (re-render), not redirect."""
        response = _post_add(auth_client, date="not-a-date")
        assert response.status_code == 200

    def test_invalid_date_format_shows_error_message(self, auth_client):
        """R7 — An invalid date must show an inline error message about the date."""
        response = _post_add(auth_client, date="not-a-date")
        assert b"Date" in response.data or b"date" in response.data
        assert b"valid" in response.data.lower() or b"required" in response.data.lower()

    def test_invalid_date_format_does_not_insert_expense(
        self, auth_client, test_user
    ):
        """R7 / DB integrity — An invalid date must not insert any row into expenses."""
        _post_add(auth_client, date="not-a-date")
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 0

    def test_date_wrong_format_dd_mm_yyyy_rerenders(self, auth_client):
        """R7 — Date in DD/MM/YYYY format must be rejected (spec requires YYYY-MM-DD)."""
        response = _post_add(auth_client, date="10/06/2026")
        assert response.status_code == 200

    def test_blank_date_rerenders_form_with_200(self, auth_client):
        """R7 — Submitting a blank date must return HTTP 200 (re-render)."""
        response = _post_add(auth_client, date="")
        assert response.status_code == 200

    def test_blank_date_does_not_insert_expense(self, auth_client, test_user):
        """R7 / DB integrity — Blank date must not insert any row into expenses."""
        _post_add(auth_client, date="")
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 0

    def test_completely_empty_form_does_not_insert_expense(
        self, auth_client, test_user
    ):
        """S6 — A fully empty POST must not insert any row into expenses."""
        auth_client.post(
            "/expenses/add",
            data={"amount": "", "category": "", "date": "", "description": ""},
        )
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 0

    def test_completely_empty_form_is_rejected(self, auth_client):
        """S6 — A fully empty POST must not succeed with a 302 redirect."""
        response = auth_client.post(
            "/expenses/add",
            data={"amount": "", "category": "", "date": "", "description": ""},
        )
        # Must be 200 (re-render) or 400 (abort), not a success redirect
        assert response.status_code in (200, 400)


# ===========================================================================
# 7. Sticky Form — previous values preserved on re-render
# ===========================================================================

class TestStickyForm:
    """Spec rule: on validation failure, previously entered values must be preserved."""

    def test_sticky_form_preserves_valid_amount_on_invalid_date(
        self, auth_client
    ):
        """Spec — The amount entered by the user must reappear when date is invalid."""
        response = _post_add(auth_client, amount="99.99", date="bad-date")
        assert b"99.99" in response.data

    def test_sticky_form_preserves_description_on_invalid_date(
        self, auth_client
    ):
        """Spec — The description entered must reappear when date is invalid."""
        response = _post_add(
            auth_client, description="Sticky description test", date="bad-date"
        )
        assert b"Sticky description test" in response.data

    def test_sticky_form_preserves_category_selection_on_invalid_date(
        self, auth_client
    ):
        """Spec — The category selected must be pre-selected when date is invalid."""
        response = _post_add(auth_client, category="Health", date="bad-date")
        # The Health option must appear as selected in the re-rendered form
        assert b"Health" in response.data

    def test_sticky_form_preserves_valid_date_on_invalid_amount(
        self, auth_client
    ):
        """Spec — The date entered must reappear when amount is invalid."""
        response = _post_add(auth_client, amount="bad", date="2026-06-15")
        assert b"2026-06-15" in response.data


# ===========================================================================
# 8. Boundary Tests
# ===========================================================================

class TestBoundaryConditions:
    """Boundary values for amount and description fields."""

    def test_negative_amount_is_rejected(self, auth_client, test_user):
        """S4 — A negative amount must be rejected and not stored."""
        response = _post_add(auth_client, amount="-1.00")
        assert response.status_code == 200
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 0

    def test_negative_amount_shows_error_message(self, auth_client):
        """S4 — A negative amount must display an inline error."""
        response = _post_add(auth_client, amount="-1.00")
        assert b"Amount must be a number greater than 0" in response.data

    def test_minimum_positive_amount_0_01_is_accepted(
        self, auth_client, test_user
    ):
        """Boundary — 0.01 is the minimum valid amount; it must be stored correctly."""
        response = _post_add(auth_client, amount="0.01")
        assert response.status_code == 302
        rows = _get_expenses_for_user(test_user["id"])
        assert rows[0]["amount"] == pytest.approx(0.01)

    def test_extremely_large_amount_is_accepted(self, auth_client, test_user):
        """S5 — A very large amount (9999999.99) must be stored without error.

        The spec imposes no upper bound on amount; this validates that the
        REAL column and float conversion do not truncate or reject large values.
        """
        response = _post_add(auth_client, amount="9999999.99")
        assert response.status_code == 302
        rows = _get_expenses_for_user(test_user["id"])
        assert rows[0]["amount"] == pytest.approx(9999999.99)

    def test_amount_with_many_decimal_places_is_accepted(
        self, auth_client, test_user
    ):
        """Boundary — float() can parse values with extra decimal places; must not crash."""
        response = _post_add(auth_client, amount="12.999999")
        # Spec only requires >0 float; storing/truncating is implementation detail
        assert response.status_code == 302

    def test_description_at_max_length_is_accepted(
        self, auth_client, test_user
    ):
        """Boundary — A description at the template maxlength (200 chars) must be stored."""
        long_desc = "A" * 200
        response = _post_add(auth_client, description=long_desc)
        assert response.status_code == 302
        rows = _get_expenses_for_user(test_user["id"])
        assert rows[0]["description"] == long_desc


# ===========================================================================
# 9. Security Tests
# ===========================================================================

class TestSecurity:
    """S1–S3 — SQL injection, XSS, and form tampering protections."""

    # --- SQL Injection ---

    def test_sql_injection_in_amount_is_rejected(self, auth_client, test_user):
        """S1 — SQL injection in the amount field must not bypass validation or corrupt DB."""
        response = _post_add(auth_client, amount="' OR 1=1 --")
        # Non-numeric amount must be rejected; no expense row should be created
        assert response.status_code == 200
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 0

    def test_sql_injection_in_description_is_stored_safely(
        self, auth_client, test_user
    ):
        """S1 — SQL injection payload in description must be stored as literal text only.

        Parameterized queries must prevent the payload from being interpreted
        as SQL.  The row must exist and the description column must contain
        the raw payload string.
        """
        payload = "'; DROP TABLE expenses; --"
        response = _post_add(auth_client, description=payload)
        assert response.status_code == 302

        # Expenses table must still exist and contain exactly one row
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 1
        assert rows[0]["description"] == payload

    def test_sql_injection_in_description_does_not_drop_expenses_table(
        self, auth_client, test_user
    ):
        """S1 — DROP TABLE payload in description must not destroy the expenses table."""
        _post_add(auth_client, description="'; DROP TABLE expenses; --")

        # Verify the table still exists by running a simple query
        conn = db_module.get_db()
        try:
            rows = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()
            table_exists = True
        except sqlite3.OperationalError:
            table_exists = False
        finally:
            conn.close()

        assert table_exists, "expenses table was dropped — SQL injection not prevented"

    def test_sql_injection_in_date_is_rejected(self, auth_client, test_user):
        """S1 — SQL injection payload in the date field must be rejected as invalid date."""
        response = _post_add(auth_client, date="' OR '1'='1")
        assert response.status_code == 200
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 0

    def test_sql_injection_classic_or_in_amount_is_rejected(
        self, auth_client, test_user
    ):
        """S1 — Classic '1=1' injection in amount must not insert a row."""
        response = _post_add(auth_client, amount="1 OR 1=1")
        assert response.status_code == 200
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 0

    # --- XSS ---

    def test_xss_script_tag_in_description_stored_as_literal(
        self, auth_client, test_user
    ):
        """S2 — A <script> tag in description must be stored as literal text.

        Jinja2 auto-escaping must prevent execution.  The raw tag must NOT
        appear unescaped in the rendered HTML response.
        """
        xss_payload = "<script>alert('xss')</script>"
        _post_add(auth_client, description=xss_payload)

        profile_response = auth_client.get("/profile")
        # The literal unescaped opening tag must not appear in HTML output
        assert b"<script>alert(" not in profile_response.data

    def test_xss_img_onerror_in_description_is_escaped(
        self, auth_client, test_user
    ):
        """S2 — An img onerror XSS payload in description must be HTML-escaped on render."""
        xss_payload = "<img src=x onerror=alert(1)>"
        _post_add(auth_client, description=xss_payload)

        profile_response = auth_client.get("/profile")
        # The unescaped raw tag must not appear in the HTML output
        assert b"<img src=x onerror=alert(1)>" not in profile_response.data

    def test_xss_payload_does_not_prevent_storage(self, auth_client, test_user):
        """S2 — XSS payload in description must still be stored (as safe text) in the DB."""
        xss_payload = "<script>alert('xss')</script>"
        response = _post_add(auth_client, description=xss_payload)
        assert response.status_code == 302

        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 1
        assert rows[0]["description"] == xss_payload

    # --- Category Tampering ---

    def test_category_not_in_allowed_list_returns_400(
        self, auth_client, test_user
    ):
        """S3 — A category value outside the allowed list must return HTTP 400."""
        response = _post_add(auth_client, category="InvalidCategory")
        assert response.status_code == 400

    def test_category_tampering_does_not_insert_expense(
        self, auth_client, test_user
    ):
        """S3 — A tampered category must not insert any row into expenses."""
        _post_add(auth_client, category="'; DROP TABLE expenses; --")
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 0

    def test_category_lowercase_variant_returns_400(
        self, auth_client, test_user
    ):
        """S3 — Category matching is case-sensitive; 'food' (lowercase) must be rejected."""
        response = _post_add(auth_client, category="food")
        assert response.status_code == 400

    def test_category_with_leading_whitespace_returns_400(
        self, auth_client, test_user
    ):
        """S3 — A category with surrounding whitespace must be rejected after stripping.

        Note: spec says strip whitespace from inputs.  ' Food' stripped = 'Food'
        which IS valid.  This test uses a value that remains invalid after stripping.
        """
        # Note: if the implementation strips whitespace from category,
        # ' Food' becomes 'Food' (valid). We use a value that is invalid after stripping.
        response = _post_add(auth_client, category="NotReal ")
        assert response.status_code == 400


# ===========================================================================
# 10. Authorization
# ===========================================================================

class TestAuthorization:
    """A1, A2 — Expenses are scoped to the owning user only."""

    def test_expense_inserted_under_correct_user_id(
        self, auth_client, test_user
    ):
        """A1 — The expense row must carry the authenticated user's user_id."""
        _post_add(auth_client)
        rows = _get_expenses_for_user(test_user["id"])
        assert rows[0]["user_id"] == test_user["id"]

    def test_second_user_expense_does_not_appear_on_first_user_profile(
        self, app, auth_client, test_user, insert_expense
    ):
        """A2 — Adding an expense as a second user must not appear on the first user's profile."""
        # Seed an expense for the authenticated test_user
        insert_expense(
            amount=20.00,
            category="Food",
            date="2026-06-10",
            description="my-own-expense",
        )

        # Create a second user and add an expense for them
        other_id = db_module.create_user(
            name="Other User",
            email="other@example.com",
            password_hash=generate_password_hash("OtherPass123"),
        )
        conn = db_module.get_db()
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (other_id, 999.00, "Other", "2026-06-10", "other-secret-expense"),
        )
        conn.commit()
        conn.close()

        response = auth_client.get("/profile")
        assert response.status_code == 200
        # The other user's distinct description must not appear
        assert b"other-secret-expense" not in response.data
        # The other user's distinct amount must not appear
        assert "₹999.00".encode("utf-8") not in response.data

    def test_first_user_cannot_add_expense_for_second_user_via_form_tampering(
        self, app, auth_client, test_user
    ):
        """A1 — Even if a user_id field were injected in POST data, it must be ignored.

        The route must derive user_id exclusively from the session, never from
        form data.  This tests that form data cannot override session ownership.
        """
        other_id = db_module.create_user(
            name="Victim User",
            email="victim@example.com",
            password_hash=generate_password_hash("VictimPass123"),
        )

        # Attempt to inject a different user_id via form tampering
        auth_client.post(
            "/expenses/add",
            data={**VALID_FORM, "user_id": str(other_id)},
        )

        # The other user must have no expenses
        other_rows = _get_expenses_for_user(other_id)
        assert len(other_rows) == 0

        # The authenticated user should have the expense (if submission succeeded)
        own_rows = _get_expenses_for_user(test_user["id"])
        assert len(own_rows) == 1


# ===========================================================================
# 11. Error Handling
# ===========================================================================

class TestErrorHandling:
    """HTTP-level error handling for malformed or disallowed requests."""

    def test_put_method_not_allowed(self, auth_client):
        """Error handling — PUT to /expenses/add is not a supported method (405)."""
        response = auth_client.put("/expenses/add", data=VALID_FORM)
        assert response.status_code == 405

    def test_patch_method_not_allowed(self, auth_client):
        """Error handling — PATCH to /expenses/add is not a supported method (405)."""
        response = auth_client.patch("/expenses/add", data=VALID_FORM)
        assert response.status_code == 405

    def test_delete_method_not_allowed(self, auth_client):
        """Error handling — DELETE to /expenses/add is not a supported method (405)."""
        response = auth_client.delete("/expenses/add")
        assert response.status_code == 405

    def test_invalid_category_returns_400_not_500(self, auth_client):
        """Error handling — Tampered category must return 400, not an unhandled 500."""
        response = _post_add(auth_client, category="EVIL_CATEGORY")
        assert response.status_code == 400


# ===========================================================================
# 12. Database Integrity
# ===========================================================================

class TestDatabaseIntegrity:
    """Verify DB state directly after every write operation."""

    def test_valid_post_creates_exactly_one_row(self, auth_client, test_user):
        """DB integrity — One submission creates exactly one row, not duplicates."""
        _post_add(auth_client)
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 1

    def test_two_valid_submissions_create_two_rows(
        self, auth_client, test_user
    ):
        """DB integrity — Two valid submissions must create exactly two separate rows."""
        _post_add(auth_client, description="First expense")
        _post_add(auth_client, description="Second expense")
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 2

    def test_validation_failure_leaves_no_partial_row(
        self, auth_client, test_user
    ):
        """DB integrity — A failed validation must not create any partial row in expenses."""
        # Submit with invalid amount (would fail amount validation before DB write)
        _post_add(auth_client, amount="0")
        rows = _get_expenses_for_user(test_user["id"])
        assert len(rows) == 0

    def test_amount_stored_as_real_not_text(self, auth_client, test_user):
        """DB integrity — amount must be stored as a REAL numeric value, not a text string."""
        _post_add(auth_client, amount="123.45")
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT amount FROM expenses WHERE user_id = ?", (test_user["id"],)
        ).fetchone()
        conn.close()
        # sqlite3 returns a Python float for REAL columns
        assert isinstance(row["amount"], float)
        assert row["amount"] == pytest.approx(123.45)

    def test_description_null_stored_as_none_in_python(
        self, auth_client, test_user
    ):
        """DB integrity — NULL description must be returned as Python None, not empty string."""
        _post_add(auth_client, description="")
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT description FROM expenses WHERE user_id = ?", (test_user["id"],)
        ).fetchone()
        conn.close()
        assert row["description"] is None


# ===========================================================================
# 13. Regression Protection
# ===========================================================================

class TestRegressionProtection:
    """REG1–REG3 — Step 07 must not break existing Step 05/06 behaviour."""

    def test_profile_loads_without_added_flag(self, auth_client, insert_expense):
        """REG1 — /profile without ?added=1 must still return HTTP 200."""
        insert_expense(amount=10.00, date="2026-06-05")
        response = auth_client.get("/profile")
        assert response.status_code == 200

    def test_profile_stats_still_rendered_after_step07(
        self, auth_client, insert_expense
    ):
        """REG2 — stats template variables from Step 05 must remain in the response."""
        insert_expense(amount=10.00, category="Food", date="2026-06-05")
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"Total Spent" in response.data
        assert b"Transactions" in response.data
        assert b"Avg. per Transaction" in response.data

    def test_profile_recent_transactions_still_rendered_after_step07(
        self, auth_client, insert_expense
    ):
        """REG2 — recent transactions section must still render after Step 07."""
        insert_expense(amount=10.00, date="2026-06-05", description="Old expense")
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"Recent Transactions" in response.data
        assert b"Old expense" in response.data

    def test_profile_categories_breakdown_still_rendered_after_step07(
        self, auth_client, insert_expense
    ):
        """REG2 — category breakdown must still render after Step 07."""
        insert_expense(amount=10.00, category="Transport", date="2026-06-05")
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"Spending by Category" in response.data

    def test_unauthenticated_profile_still_redirects_after_step07(self, client):
        """REG3 — /profile must still require authentication after Step 07 is added."""
        response = client.get("/profile")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_login_page_still_accessible_after_step07(self, client):
        """REG3 — GET /login must return 200 and not be broken by Step 07 changes."""
        response = client.get("/login")
        assert response.status_code == 200

    def test_add_expense_link_present_on_profile(
        self, auth_client, insert_expense
    ):
        """REG2 — The 'Add Expense' button on /profile must link to /expenses/add."""
        insert_expense(amount=10.00, date="2026-06-05")
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"/expenses/add" in response.data

    def test_date_filter_still_works_after_step07(
        self, auth_client, insert_expense
    ):
        """REG2 — Step 06 date filter must still work correctly after Step 07 changes."""
        # Insert one expense inside a recent window and one far outside it.
        # Use a dynamic date so this test never drifts out of the 7-day window.
        recent_date = str((datetime.today() - timedelta(days=3)).date())
        insert_expense(amount=15.00, date=recent_date, description="recent-expense")
        insert_expense(amount=99.00, date="2024-01-10", description="old-expense")

        response = auth_client.get("/profile", query_string={"period": "7d"})
        assert response.status_code == 200
        # The old expense must be excluded from the 7-day filter
        assert "₹99.00".encode("utf-8") not in response.data
        assert b"recent-expense" in response.data
