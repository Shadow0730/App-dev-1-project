from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # ADMIN / STAFF / TREKKER
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    staff_profile = db.relationship("StaffProfile", back_populates="user", uselist=False)
    bookings = db.relationship("Booking", back_populates="user")
    def check_password(self, password: str):
        return self.password == password
        


class StaffProfile(db.Model):
    __tablename__ = "staff_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    phone = db.Column(db.String(10))
    experience_years = db.Column(db.Integer)
    assigned_treks = db.relationship("Trek", back_populates="assigned_staff", foreign_keys="Trek.assigned_staff_id")

    user = db.relationship("User", back_populates="staff_profile")


class Trek(db.Model):
    __tablename__ = "treks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)  # EASY/MEDIUM/HARD
    duration_days = db.Column(db.Integer, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="DRAFT")  # DRAFT/PUBLISHED/CANCELLED

    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("staff_profiles.id"), nullable=True)
    assigned_staff = db.relationship("StaffProfile", back_populates="assigned_treks", foreign_keys=[assigned_staff_id])
    bookings = db.relationship("Booking", back_populates="trek", cascade="all, delete-orphan")


class Booking(db.Model):
    __tablename__ = "bookings"
    __table_args__ = (
        db.UniqueConstraint("user_id", "trek_id", name="uq_user_trek"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey("treks.id"), nullable=False)
    booking_status = db.Column(db.String(10), nullable=False, default="PENDING")
    payment_status = db.Column(db.String(10), nullable=False, default="UNPAID")
    booking_date = db.Column(db.Date, nullable=False, default=date.today)

    user = db.relationship("User", back_populates="bookings")
    trek = db.relationship("Trek", back_populates="bookings")