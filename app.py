from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    abort,
)
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import (
    get_db,
    init_db,
    seed_db,
    create_user,
    get_user_by_email,
    get_user_by_id,
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
        return redirect(url_for("working"))
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
    return redirect(url_for("working"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("working"))
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
    return redirect(url_for("working"))


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


@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
