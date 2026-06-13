from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    abort,
)
import math
import os
import secrets
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

from database.db import (
    get_db,
    init_db,
    seed_db,
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user_name,
    update_user_password,
    get_expenses_by_user_in_range,
    create_expense,
    get_expense_by_id,
    update_expense,
)

app = Flask(__name__)
# Dev-only secret key for session signing. Move to an environment variable
# before any non-local deployment.
app.secret_key = "dev-secret-change-me"

# Ensure the database schema exists and demo data is present before serving.
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Date filter helpers                                                 #
# ------------------------------------------------------------------ #

_PERIOD_PRESETS = {"7d": 7, "30d": 30, "3m": 90, "1y": 365}
_ALLOWED_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def _safe_parse_date(value):
    if not value:
        return None
    try:
        return str(datetime.strptime(value, "%Y-%m-%d").date())
    except ValueError:
        return None


def resolve_date_filter(period, from_param, to_param):
    """Return (from_date, to_date, active_period) from raw query-string values."""
    if period in _PERIOD_PRESETS:
        from_date = str((datetime.today() - timedelta(days=_PERIOD_PRESETS[period])).date())
        return from_date, None, period
    if period == "all":
        return None, None, "all"
    from_date = _safe_parse_date(from_param)
    to_date = _safe_parse_date(to_param)
    active_period = "custom" if (from_date or to_date) else "all"
    return from_date, to_date, active_period


# ------------------------------------------------------------------ #
# Template context                                                    #
# ------------------------------------------------------------------ #

@app.context_processor
def inject_current_user():
    user_id = session.get("user_id")
    if user_id:
        return {"current_user": get_user_by_id(user_id)}
    return {"current_user": None}


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")

    # Treat absent or blank required fields as a malformed request.
    if not name or not name.strip() or not email or not email.strip() or not password:
        abort(400)

    name = name.strip()
    email = email.strip().lower()

    if len(password) < 8:
        return render_template(
            "register.html", error="Password must be at least 8 characters."
        )

    if get_user_by_email(email) is not None:
        return render_template(
            "register.html", error="An account with that email already exists."
        )

    user_id = create_user(name, email, generate_password_hash(password))
    session["user_id"] = user_id
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not email.strip() or not password:
        abort(400)

    email = email.strip().lower()

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/policy")
def policy():
    return render_template("privacy.html")


@app.route("/working")
def working():
    return render_template("working.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])
    member_since = datetime.strptime(
        user["created_at"], "%Y-%m-%d %H:%M:%S"
    ).strftime("%B %Y")

    from_date, to_date, active_period = resolve_date_filter(
        request.args.get("period", "").strip().lower(),
        request.args.get("from", "").strip(),
        request.args.get("to", "").strip(),
    )

    expenses = get_expenses_by_user_in_range(session["user_id"], from_date, to_date)

    total     = sum(e["amount"] for e in expenses)
    count     = len(expenses)
    avg_per_tx = round(total / count, 2) if count else 0.0

    by_category = {}
    for e in expenses:
        by_category[e["category"]] = round(
            by_category.get(e["category"], 0) + e["amount"], 2
        )
    categories_sorted = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    top_category = categories_sorted[0][0] if categories_sorted else "—"

    categories_data = [
        {
            "name": name,
            "amount": f"₹{amount:,.2f}",
            "pct": round(amount / total * 100) if total else 0,
        }
        for name, amount in categories_sorted
    ]

    highest_tx = None
    if expenses:
        h = max(expenses, key=lambda e: e["amount"])
        highest_tx = {
            "amount": f"₹{h['amount']:,.2f}",
            "description": h["description"] if h["description"] else h["category"],
        }

    unique_days = len(set(e["date"] for e in expenses))
    avg_daily   = round(total / unique_days, 2) if unique_days else 0.0

    recent = [
        {
            "id": e["id"],
            "date": datetime.strptime(e["date"], "%Y-%m-%d").strftime("%b %d"),
            "description": e["description"] if e["description"] else e["category"],
            "category": e["category"],
            "amount": f"₹{e['amount']:,.2f}",
        }
        for e in expenses[:5]
    ]

    stats = {
        "total":       f"₹{total:,.2f}",
        "count":       count,
        "avg_per_tx":  f"₹{avg_per_tx:,.2f}",
        "top_category": top_category,
        "highest":     highest_tx,
        "unique_days": unique_days,
        "avg_daily":   f"₹{avg_daily:,.2f}",
        "num_categories": len(categories_sorted),
    }

    return render_template(
        "profile.html",
        user=user,
        member_since=member_since,
        stats=stats,
        categories_data=categories_data,
        recent=recent,
        active_period=active_period,
        filter_from=from_date or "",
        filter_to=to_date or "",
    )


@app.route("/profile/update-name", methods=["POST"])
def profile_update_name():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    name = request.form.get("name")
    if not name or not name.strip():
        abort(400)

    update_user_name(session["user_id"], name.strip())
    return redirect(url_for("profile", name_success="1"))


@app.route("/profile/update-password", methods=["POST"])
def profile_update_password():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    current_pw = request.form.get("current_password")
    new_pw     = request.form.get("new_password")
    confirm_pw = request.form.get("confirm_password")

    if not current_pw or not new_pw or not confirm_pw:
        abort(400)

    user = get_user_by_id(session["user_id"])

    if not check_password_hash(user["password_hash"], current_pw):
        return redirect(url_for("profile", pw_error="Current password is incorrect."))

    if new_pw != confirm_pw:
        return redirect(url_for("profile", pw_error="New passwords do not match."))

    if len(new_pw) < 8:
        return redirect(url_for("profile", pw_error="Password must be at least 8 characters."))

    update_user_password(session["user_id"], generate_password_hash(new_pw))
    return redirect(url_for("profile", pw_success="1"))


def _render_add_expense_form(error, amount_raw, category, date_raw, description, csrf_token):
    return render_template(
        "add_expense.html",
        error=error,
        amount=amount_raw,
        category=category,
        date=date_raw,
        description=description or "",
        categories=_ALLOWED_CATEGORIES,
        csrf_token=csrf_token,
    )


def _render_edit_expense_form(error, expense_id, amount_raw, category, date_raw, description, csrf_token):
    return render_template(
        "edit_expense.html",
        error=error,
        expense_id=expense_id,
        amount=amount_raw,
        category=category,
        date=date_raw,
        description=description or "",
        categories=_ALLOWED_CATEGORIES,
        csrf_token=csrf_token,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    csrf_token = session["csrf_token"]

    if request.method == "GET":
        today = str(datetime.today().date())
        return render_template(
            "add_expense.html",
            today=today,
            categories=_ALLOWED_CATEGORIES,
            csrf_token=csrf_token,
        )

    if request.form.get("csrf_token") != csrf_token:
        abort(403)

    amount_raw  = request.form.get("amount", "").strip()
    category    = request.form.get("category", "").strip()
    date_raw    = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip() or None

    try:
        amount = float(amount_raw)
        if amount <= 0 or not math.isfinite(amount):
            raise ValueError
    except (ValueError, TypeError):
        return _render_add_expense_form(
            "Amount must be a number greater than 0.",
            amount_raw, category, date_raw, description, csrf_token,
        )

    if category not in _ALLOWED_CATEGORIES:
        abort(400)

    parsed_date = _safe_parse_date(date_raw)
    if not parsed_date:
        return _render_add_expense_form(
            "Date is required and must be a valid date.",
            amount_raw, category, date_raw, description, csrf_token,
        )

    create_expense(session["user_id"], amount, category, parsed_date, description)
    return redirect(url_for("profile", added="1"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    csrf_token = session["csrf_token"]

    expense = get_expense_by_id(id)
    if expense is None:
        abort(404)
    if expense["user_id"] != session["user_id"]:
        abort(403)

    if request.method == "GET":
        return _render_edit_expense_form(
            None,
            expense["id"],
            expense["amount"],
            expense["category"],
            expense["date"],
            expense["description"] or "",
            csrf_token,
        )

    if request.form.get("csrf_token") != csrf_token:
        abort(403)

    amount_raw  = request.form.get("amount", "").strip()
    category    = request.form.get("category", "").strip()
    date_raw    = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip() or None

    try:
        amount = float(amount_raw)
        if amount <= 0 or not math.isfinite(amount):
            raise ValueError
    except (ValueError, TypeError):
        return _render_edit_expense_form(
            "Amount must be a number greater than 0.",
            id, amount_raw, category, date_raw, description, csrf_token,
        )

    if category not in _ALLOWED_CATEGORIES:
        abort(400)

    parsed_date = _safe_parse_date(date_raw)
    if not parsed_date:
        return _render_edit_expense_form(
            "Date is required and must be a valid date.",
            id, amount_raw, category, date_raw, description, csrf_token,
        )

    update_expense(id, amount, category, parsed_date, description)
    return redirect(url_for("profile", edited="1"))


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
