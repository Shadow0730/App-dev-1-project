from datetime import datetime
from flask import Flask, flash, render_template, request, redirect, url_for, session
from databases import db, User, Trek, StaffProfile, Booking, Place

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///trekking.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.secret_key = "very_secret_key"

db.init_app(app)

with app.app_context():
    db.create_all()
    admin = User.query.filter_by(email="admin@trek.com").first()
    if not admin:
        admin = User(
            name="Admin",
            email="admin@trek.com",
            role="ADMIN",
            password="admin123"
        )
        db.session.add(admin)
        db.session.commit()

@app.route("/")
def home():
    return render_template("login.html",show_topbar=False)

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

        u = User(name=name, email=email, role="TREKKER",password=password)
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
        staff_user = User(name=name, email=email, role="STAFF", password=password)
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
        session["name"] = user.name

        if user.role == "ADMIN":
            return redirect(url_for("admin_dashboard"))
        elif user.role == "STAFF":
            return redirect(url_for("staff_dashboard"))
        else: 
            return redirect(url_for("user_dashboard"))
    return render_template("login.html", show_topbar=False)

@app.route("/admin/dashboard", methods=["GET"])
def admin_dashboard():
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    return render_template(
        "admin_d.html",
    )


def ensure_place_from_trek_name(trek_name: str):
    trek_name = (trek_name or "").strip()
    if not trek_name:
        return

    exists = Place.query.filter(Place.name.ilike(trek_name)).first()
    if not exists:
        db.session.add(Place(name=trek_name))

# admin treck routes and form functions
@app.route("/admin/treks", methods=["GET"])
def admin_treks():
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    treks = Trek.query.all()
    return render_template("admin_t.html", treks=treks)

@app.route("/admin/trek/new", methods=["GET"])
def admin_trek_new():
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))
    return render_template("admin_tnf.html", trek=None)

@app.get("/admin/trek/<int:trek_id>")
def admin_trek_detail(trek_id):
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    trek = Trek.query.get_or_404(trek_id)
    return render_template("admin_td.html", trek=trek)

@app.get("/admin/trek/<int:trek_id>/edit")
def admin_trek_edit(trek_id):
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    trek = Trek.query.get_or_404(trek_id)
    return render_template("admin_tnf.html", trek=trek)


@app.post("/admin/trek/<int:trek_id>/edit")
def admin_trek_edit_post(trek_id):
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    trek = Trek.query.get_or_404(trek_id)

    name = request.form.get("name", "").strip()
    difficulty = request.form.get("difficulty", "").strip()
    duration_days = request.form.get("duration_days", "").strip()
    location = request.form.get("location", "").strip()
    start_date_raw = request.form.get("start_date", "").strip()
    end_date_raw = request.form.get("end_date", "").strip()
    available_slots = request.form.get("available_slots", "").strip()
    status = request.form.get("status", "DRAFT").strip()
    start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()

    if not name or not difficulty or not duration_days or not available_slots or not status:
        flash("All fields are required.", "warning")
        return redirect(url_for("admin_trek_edit", trek_id=trek.id))

    trek.name = name
    trek.difficulty = difficulty
    trek.location = location
    trek.duration_days = int(duration_days)
    trek.start_date = start_date
    trek.end_date = end_date
    trek.available_slots = int(available_slots)
    trek.status = status

    ensure_place_from_trek_name(name)

    db.session.commit()
    flash(f"Trek '{trek.name}' updated successfully.", "success")
    return redirect(url_for("admin_trek_detail", trek_id=trek.id))


@app.route("/admin/trek/new", methods=["POST"])
def admin_trek_new_post():
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    difficulty = request.form.get("difficulty", "").strip()
    duration_days = request.form.get("duration_days", "").strip()
    start_date_raw = request.form.get("start_date", "").strip()
    location = request.form.get("location", "").strip()
    end_date_raw = request.form.get("end_date", "").strip()
    available_slots = request.form.get("available_slots", "").strip()
    status = request.form.get("status", "DRAFT").strip()
    start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()

    if not name or not difficulty or not duration_days or not available_slots or not start_date or not end_date:
        flash("All fields are required.", "warning")
        return redirect(url_for("admin_trek_new"))

    trek = Trek(
        name=name,
        difficulty=difficulty,
        duration_days=int(duration_days),
        location=location,
        available_slots=int(available_slots),
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    ensure_place_from_trek_name(name)
    db.session.add(trek)
    db.session.commit()

    flash(f"Trek '{name}' created successfully.", "success")
    return redirect(url_for("admin_treks"))

@app.post("/admin/trek/<int:trek_id>/delete")
def admin_trek_delete(trek_id):
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    trek = Trek.query.get_or_404(trek_id)
    name = trek.name

    db.session.delete(trek)
    db.session.commit()

    flash(f"Trek '{name}' deleted.", "success")
    return redirect(url_for("admin_treks"))


@app.route("/admin/staff", methods=["GET"])
def admin_staff():
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    staff = User.query.filter_by(role="STAFF").all()
    return render_template("admin_s.html", staff=staff)

@app.route("/admin/staff/<int:staff_id>/delete", methods=["POST"])
def admin_staff_delete(staff_id):
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    staff = User.query.get_or_404(staff_id)
    name = staff.name

    db.session.delete(staff)
    db.session.commit()

    flash(f"Staff '{name}' removed.", "success")
    return redirect(url_for("admin_staff"))

@app.route("/admin/staff/<int:staff_id>/accept", methods=["POST"])
def admin_staff_accept(staff_id):
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    staff = User.query.get_or_404(staff_id)

    if not staff.staff_profile:
        flash("Staff profile not found.", "danger")
        return redirect(url_for("admin_staff"))

    staff.staff_profile.accepted = True

    staff.accepted = True
    db.session.commit()

    flash(f"Staff '{staff.name}' accepted.", "success")
    return redirect(url_for("admin_staff"))

@app.get("/admin/trek/<int:trek_id>/assign-staff")
def admin_assign_staff(trek_id):
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    trek = Trek.query.get_or_404(trek_id)
    staff = User.query.filter_by(role="STAFF").all()

    return render_template("admin_assign_staff.html", trek=trek, staff=staff)


@app.post("/admin/trek/<int:trek_id>/assign-staff")
def admin_assign_staff_post(trek_id):
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    trek = Trek.query.get_or_404(trek_id)
    staff_id = request.form.get("staff_id", "").strip()

    if not staff_id:
        flash("Please select a staff member.", "warning")
        return redirect(url_for("admin_assign_staff", trek_id=trek_id))

    staff_user = User.query.get_or_404(int(staff_id))

    if not staff_user.staff_profile:
        flash("Selected staff profile not found.", "danger")
        return redirect(url_for("admin_assign_staff", trek_id=trek_id))

    trek.assigned_staff_id = staff_user.staff_profile.id
    db.session.commit()

    flash(f"Staff assigned to trek '{trek.name}'.", "success")
    return redirect(url_for("admin_treks"))

@app.route("/admin/users")
def admin_users():
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    users = User.query.filter_by(role="TREKKER").all()
    return render_template("admin_u.html", users=users)


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def admin_user_delete(user_id):
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    user = User.query.get_or_404(user_id)

    if user.role == "ADMIN":
        flash("Admin cannot be deleted.", "warning")
        return redirect(url_for("admin_users"))

    db.session.delete(user)
    db.session.commit()

    flash(f"User '{user.name}' deleted successfully.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/bookings")
def admin_bookings():
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    bookings = Booking.query.order_by(Booking.booking_date.desc()).all()
    return render_template("admin_b.html", bookings=bookings)

# --- SEARCH ---
@app.post("/admin/search")
def admin_search():
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    query = request.form.get("query", "").strip()
    search_type = request.form.get("search_type", "all")

    treks = []
    staff = []
    users = []

    if query:
        if search_type in ["all", "trek"]:
            treks = Trek.query.filter(
                Trek.name.ilike(f"%{query}%") |
                Trek.location.ilike(f"%{query}%")
            ).all()

        if search_type in ["all", "staff"]:
            staff = User.query.filter(
                User.role == "STAFF",
                User.name.ilike(f"%{query}%") |
                User.email.ilike(f"%{query}%")
            ).all()

        if search_type in ["all", "user"]:
            users = User.query.filter(
                User.role == "TREKKER",
                User.name.ilike(f"%{query}%") |
                User.email.ilike(f"%{query}%")
            ).all()

    return render_template(
        "admin_d.html",
        query=query,
        search_type=search_type,
        treks=treks,
        staff=staff,
        users=users,
        searched=True
    )


# ---------------- STAFF DASHBOARD ----------------
@app.get("/staff/dashboard")
def staff_dashboard():
    if session.get("role") != "STAFF":
        return redirect(url_for("login"))

    staff_id = session.get("user_id")
    staff = StaffProfile.query.filter_by(user_id=session.get("user_id")).first()
    if not staff or not staff.accepted:
        flash("Your dashboard access is not enabled by admin.", "danger")
        return redirect(url_for("login"))

    assigned_treks = Trek.query.filter_by(assigned_staff_id=staff.id).all()
    assigned_trek_ids = [t.id for t in assigned_treks]

    # Count trekkers registered in assigned treks
    registered_count = 0
    if assigned_trek_ids:
        registered_count = Booking.query.filter(
            Booking.trek_id.in_(assigned_trek_ids)
        ).count()

    return render_template(
        "staf_d.html",
        treks=assigned_treks,
        registered_count=registered_count
    )


# ---------------- STAFF TREK DETAIL ----------------
@app.get("/staff/trek/<int:trek_id>")
def staff_trek_detail(trek_id):
    if session.get("role") != "STAFF":
        return redirect(url_for("login"))

    staff = StaffProfile.query.filter_by(user_id=session.get("user_id")).first()
    trek = Trek.query.get_or_404(trek_id)
    booked_count = Booking.query.filter_by(trek_id=trek.id).count()
    total_slots = trek.available_slots + booked_count

    if not staff or trek.assigned_staff_id != staff.id:
        flash("You are not allowed to access this trek.", "danger")
        return redirect(url_for("staff_dashboard"))

    participants = Booking.query.filter_by(trek_id=trek.id).all()

    return render_template(
        "staf_td.html",
        trek=trek,
        participants=participants,
        total_slots=total_slots,
    )


# ---------------- UPDATE TREK SLOTS ----------------
@app.post("/staff/trek/<int:trek_id>/slots")
def staff_update_slots(trek_id):
    if session.get("role") != "STAFF":
        return redirect(url_for("login"))

    staff = StaffProfile.query.filter_by(user_id=session.get("user_id")).first()
    trek = Trek.query.get_or_404(trek_id)

    if not staff or trek.assigned_staff_id != staff.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("staff_dashboard"))

    slots = request.form.get("available_slots", "").strip()

    try:
        slots = int(slots)
        if slots < 0:
            raise ValueError

        trek.available_slots = slots
        db.session.commit()
        flash("Available slots updated.", "success")
    except ValueError:
        flash("Enter a valid non-negative number for slots.", "warning")

    return redirect(url_for("staff_trek_detail", trek_id=trek.id))


# ---------------- UPDATE TREK STATUS (OPEN/CLOSED/STARTED/ONGOING/COMPLETED) ----------------
@app.post("/staff/trek/<int:trek_id>/status")
def staff_update_status(trek_id):
    if session.get("role") != "STAFF":
        return redirect(url_for("login"))

    staff = StaffProfile.query.filter_by(user_id=session.get("user_id")).first()
    trek = Trek.query.get_or_404(trek_id)

    if not staff or trek.assigned_staff_id != staff.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("staff_dashboard"))

    new_status = request.form.get("status", "").strip().upper()
    trek.status = new_status
    db.session.commit()

    flash(f"Trek status updated to {new_status}.", "success")
    return redirect(url_for("staff_trek_detail", trek_id=trek.id))


# ---------------- REMOVE PARTICIPANT (optional manage participant list) ----------------
@app.post("/staff/trek/<int:trek_id>/participant/<int:booking_id>/remove")
def staff_remove_participant(trek_id, booking_id):
    if session.get("role") != "STAFF":
        return redirect(url_for("login"))

    staff = StaffProfile.query.filter_by(user_id=session.get("user_id")).first()
    trek = Trek.query.get_or_404(trek_id)

    if not staff or trek.assigned_staff_id != staff.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("staff_dashboard"))

    booking = Booking.query.get_or_404(booking_id)
    trek.available_slots += 1
    db.session.delete(booking)
    db.session.commit()

    flash("Participant removed from trek.", "success")
    return redirect(url_for("staff_trek_detail", trek_id=trek.id))


@app.get("/user/dashboard")
def user_dashboard():
    if session.get("role") != "TREKKER":
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    total_bookings = Booking.query.filter_by(user_id=user_id).count()
    active_bookings = Booking.query.filter(
        Booking.user_id == user_id,
        Booking.booking_status.in_(["CONFIRMED", "ACTIVE"])
    ).count()

    return render_template(
        "user_d.html",
        total_bookings=total_bookings,
        active_bookings=active_bookings
    )


# ---------------- PROFILE UPDATE ----------------
@app.get("/user/profile")
def user_profile():
    if session.get("role") != "TREKKER":
        return redirect(url_for("login"))

    user = User.query.get_or_404(session["user_id"])
    return render_template("user_p.html", user=user)


@app.post("/user/profile")
def user_profile_update():
    if session.get("role") != "TREKKER":
        return redirect(url_for("login"))

    user = User.query.get_or_404(session["user_id"])
    name = request.form.get("name", "").strip()

    if not name:
        flash("Name is required.", "warning")
        return redirect(url_for("user_profile"))

    user.name = name
    db.session.commit()
    flash("Profile updated successfully.", "success")
    return redirect(url_for("user_profile"))


# ---------------- VIEW / SEARCH / FILTER OPEN TREKS ----------------
@app.get("/user/treks")
def user_treks():
    if session.get("role") != "TREKKER":
        return redirect(url_for("login"))

    treks = Trek.query.filter(
        Trek.status == "OPEN",
        Trek.available_slots > 0
    ).order_by(Trek.id.desc()).all()

    return render_template("user_t.html", treks=treks)

# ---------------- BOOK TREK ----------------
@app.post("/user/trek/<int:trek_id>/book")
def user_book_trek(trek_id):
    if session.get("role") != "TREKKER":
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    trek = Trek.query.get_or_404(trek_id)

    # prevent booking if trek is closed/full
    if trek.status != "OPEN":
        flash("Booking not allowed. Trek is not open.", "warning")
        return redirect(url_for("user_treks"))

    if trek.available_slots <= 0:
        flash("Booking not allowed. Trek slots are full.", "warning")
        return redirect(url_for("user_treks"))

    # prevent duplicate booking
    existing = Booking.query.filter_by(user_id=user_id, trek_id=trek.id).first()
    if existing:
        flash("You already booked this trek.", "info")
        return redirect(url_for("user_my_bookings"))

    booking = Booking(
        user_id=user_id,
        trek_id=trek.id,
        booking_status="CONFIRMED",
        payment_status="PENDING"
    )

    trek.available_slots -= 1
    db.session.add(booking)
    db.session.commit()

    flash("Trek booked successfully!", "success")
    return redirect(url_for("user_my_bookings"))


# ---------------- VIEW BOOKED TREKS + STATUS ----------------
@app.get("/user/bookings")
def user_my_bookings():
    if session.get("role") != "TREKKER":
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    bookings = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).all()

    return render_template("user_b.html", bookings=bookings)


# ---------------- TREKKING HISTORY ----------------
@app.get("/user/history")
def user_trek_history():
    if session.get("role") != "TREKKER":
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    history = Booking.query.join(Trek).filter(
        Booking.user_id == user_id,
        Trek.status.in_(["COMPLETED"])
    ).order_by(Booking.id.desc()).all()

    return render_template("user_h.html", history=history)
@app.get("/trekker/dashboard")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
if __name__ == "__main__":
    app.run(debug=True)
