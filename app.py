from flask import Flask, flash, render_template, request, redirect, url_for, session
from databases import db, User, Trek, StaffProfile

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///trekking.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "very_secret_key"

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/signup/trekker", methods=["GET", "POST"])
def signup_trekker():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "warning")
            return redirect(url_for("signup_trekker"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists. Please login.", "warning")
            return redirect(url_for("login"))

        u = User(name=name, email=email, role="TREKKER")
        u.set_password(password)
        db.session.add(u)
        db.session.commit()

        flash("Trekker signup successful. Please login.", "success")
        return redirect(url_for("login"))
    else:
        return render_template("signup_trekker.html")


@app.route("/signup/staff",methods=["GET", "POST"])
def signup_staff():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        phone = request.form.get("phone", "").strip()
        experience_years = request.form.get("experience_years", "").strip()

        if not name or not email or not password:
            flash("Name, email, and password are required.", "warning")
            return redirect(url_for("signup_staff"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists. Please login.", "warning")
            return redirect(url_for("login"))

        # Create staff user
        staff_user = User(name=name, email=email, role="STAFF")
        staff_user.set_password(password)
        db.session.add(staff_user)
        db.session.flush()  

        
        profile = StaffProfile(
            user_id=staff_user.id,
            phone=phone or None,
            experience_years=int(experience_years) if experience_years.isdigit() else None,
        )
        db.session.add(profile)

        db.session.commit()

        flash("Staff signup successful. Please login.", "success")
        return redirect(url_for("login"))
    else:
        return render_template("signup_staff.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Incorrect email or password", "danger")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user.id
        session["role"] = user.role

        if user.role == "ADMIN":
            return redirect(url_for("admin_dashboard"))
        elif user.role == "STAFF":
            return redirect(url_for("staff_dashboard"))
        else: 
            return redirect(url_for("trekker_dashboard"))
    return render_template("login.html")

@app.get("/admin/dashboard")
def admin_dashboard():
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html")

@app.get("/staff/dashboard")
def staff_dashboard():
    if session.get("role") != "STAFF":
        return redirect(url_for("login"))
    staff_id = session.get("user_id")

    assigned_treks = Trek.query.filter_by(assigned_staff_id=staff_id).all()

    return render_template("staff_dashboard.html", treks=assigned_treks)

@app.get("/trekker/dashboard")
def trekker_dashboard():
    if session.get("role") != "TREKKER":
        return redirect(url_for("login"))
    return render_template("trekker_dashboard.html")

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
if __name__ == "__main__":
    app.run(debug=True)