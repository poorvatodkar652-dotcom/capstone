from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, Date, Text, ForeignKey, CheckConstraint
)

db = SQLAlchemy()

# ─────────────────────────────────────────────
#  LOOKUP TABLES
# ─────────────────────────────────────────────

class Branch(db.Model):
    __tablename__ = "branches"

    branch_code = Column(String(10), primary_key=True)
    branch_name = Column(String(100), nullable=False)

    # Relationships
    students = db.relationship("Student", back_populates="branch_ref")
    staff    = db.relationship("Staff",   back_populates="branch_ref")

    def __repr__(self):
        return f"<Branch {self.branch_code}: {self.branch_name}>"


class Year(db.Model):
    __tablename__ = "years"

    year_code  = Column(String(5),  primary_key=True)
    year_label = Column(String(50), nullable=False)

    # Relationships
    students = db.relationship("Student", back_populates="year_ref")
    staff    = db.relationship("Staff",   back_populates="year_ref")

    def __repr__(self):
        return f"<Year {self.year_code}: {self.year_label}>"


# ─────────────────────────────────────────────
#  USER TABLES
# ─────────────────────────────────────────────

class Student(db.Model):
    __tablename__ = "students"

    enrollment_no   = Column(String(20),  primary_key=True)
    full_name       = Column(String(100), nullable=False)
    email           = Column(String(255), nullable=True) # Added for student email notifications
    branch          = Column(String(10),  ForeignKey("branches.branch_code"), nullable=False)
    year            = Column(String(5),   ForeignKey("years.year_code"),      nullable=False)
    hostel_name     = Column(String(100), nullable=False)
    room_number     = Column(String(20),  nullable=False)
    password_hash   = Column(String(255), nullable=False)

    # Fee tracking
    total_fees      = Column(db.Float, nullable=False, default=0)
    paid_fees       = Column(db.Float, nullable=False, default=0)
    remaining_fees  = Column(db.Float, nullable=False, default=0)
    fee_status      = Column(String(10), nullable=False, default="Due")

    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint("fee_status IN ('Paid', 'Partial', 'Due')", name="chk_fee_status"),
        CheckConstraint("paid_fees >= 0",                           name="chk_paid_fees_positive"),
        CheckConstraint("paid_fees <= total_fees",                  name="chk_paid_not_exceed_total"),
    )

    # Relationships
    branch_ref        = db.relationship("Branch", back_populates="students")
    year_ref          = db.relationship("Year",   back_populates="students")
    gatepass_requests = db.relationship("GatepassRequest", back_populates="student",
                                     cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student {self.enrollment_no}: {self.full_name}>"


class Staff(db.Model):
    __tablename__ = "staff"

    staff_id      = Column(Integer,      primary_key=True, autoincrement=True)
    full_name     = Column(String(100),  nullable=False)
    email         = Column(String(255),  nullable=False, unique=True)
    mobile_no     = Column(String(15),   nullable=False, unique=True)
    password_hash = Column(String(255),  nullable=False)
    role          = Column(String(10),   nullable=False)  # Warden | HOD
    branch        = Column(String(10),   ForeignKey("branches.branch_code"), nullable=False)
    year          = Column(String(5),    ForeignKey("years.year_code"),      nullable=True) # NULL for HOD
    registered_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('Warden', 'HOD')", name="chk_staff_role"),
    )

    # Relationships
    branch_ref = db.relationship("Branch", back_populates="staff")
    year_ref   = db.relationship("Year",   back_populates="staff")
    notices    = db.relationship("Notice", back_populates="staff_sender",
                              primaryjoin="and_(Notice.sender_id == Staff.staff_id, "
                                          "Notice.sender_type == 'Staff')",
                              foreign_keys="[Notice.sender_id]", overlaps="guard_sender")

    def __repr__(self):
        return f"<Staff #{self.staff_id}: {self.full_name} ({self.role})>"


class SecurityGuard(db.Model):
    __tablename__ = "security_guards"

    guard_id      = Column(Integer,     primary_key=True, autoincrement=True)
    full_name     = Column(String(100), nullable=False)
    email         = Column(String(255), nullable=False, unique=True)
    mobile_no     = Column(String(15),  nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    gender        = Column(String(10),  nullable=False)
    date_of_birth = Column(Date,        nullable=False)
    registered_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint("gender IN ('Male', 'Female', 'Other')", name="chk_guard_gender"),
    )

    # Relationships
    gatepass_entries = db.relationship("GatepassEntry", back_populates="guard",
                                    cascade="all, delete-orphan")
    notices          = db.relationship("Notice", back_populates="guard_sender",
                                    primaryjoin="and_(Notice.sender_id == SecurityGuard.guard_id, "
                                                "Notice.sender_type == 'Security')",
                                    foreign_keys="[Notice.sender_id]",
                                    overlaps="staff_sender,notices")

    def __repr__(self):
        return f"<SecurityGuard #{self.guard_id}: {self.full_name}>"


# ─────────────────────────────────────────────
#  GATEPASS TABLES
# ─────────────────────────────────────────────

class GatepassRequest(db.Model):
    __tablename__ = "gatepass_requests"

    request_id       = Column(Integer,     primary_key=True, autoincrement=True)
    enrollment_no    = Column(String(20),  ForeignKey("students.enrollment_no"), nullable=False)
    reason           = Column(Text,        nullable=False)
    out_date         = Column(DateTime,    nullable=False)
    in_date          = Column(DateTime,    nullable=False)
    place            = Column(String(200), nullable=False)
    status           = Column(String(10),  nullable=False, default="Pending")
    auth_code        = Column(String(500), nullable=True)    # 6-character alphanumeric code
    reject_reason    = Column(Text,        nullable=True)    # set only on rejection
    request_datetime = Column(DateTime,    nullable=False, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('Pending', 'Approved', 'Rejected')",
            name="chk_gatepass_status"
        ),
        CheckConstraint("in_date > out_date", name="chk_dates_order"),
    )

    # Relationships
    student = db.relationship("Student", back_populates="gatepass_requests")
    entry   = db.relationship("GatepassEntry", back_populates="request",
                           uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GatepassRequest #{self.request_id} [{self.status}] by {self.enrollment_no}>"


class GatepassEntry(db.Model):
    __tablename__ = "gatepass_entries"

    entry_id            = Column(Integer,    primary_key=True, autoincrement=True)
    request_id          = Column(Integer,    ForeignKey("gatepass_requests.request_id"),
                                             nullable=False, unique=True)
    guard_id            = Column(Integer,    ForeignKey("security_guards.guard_id"),
                                             nullable=False)
    actual_out_datetime = Column(DateTime,   nullable=True)   # set when student exits
    actual_in_datetime  = Column(DateTime,   nullable=True)   # set when student returns
    late_days           = Column(Integer,    nullable=False, default=0)
    fine_amount         = Column(db.Float, nullable=False, default=0)  # 50 * late_days
    fine_status         = Column(String(10), nullable=False, default="No Fine")
    payment_mode        = Column(String(50), nullable=True)   # Cash / UPI / etc.

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "fine_status IN ('Paid', 'Unpaid', 'No Fine')",
            name="chk_fine_status"
        ),
        CheckConstraint("late_days >= 0",    name="chk_late_days_positive"),
        CheckConstraint("fine_amount >= 0",  name="chk_fine_amount_positive"),
    )

    # Relationships
    request = db.relationship("GatepassRequest", back_populates="entry")
    guard   = db.relationship("SecurityGuard",   back_populates="gatepass_entries")

    def __repr__(self):
        return (f"<GatepassEntry #{self.entry_id} | Request #{self.request_id} | "
                f"Fine: ₹{self.fine_amount} [{self.fine_status}]>")


# ─────────────────────────────────────────────
#  NOTICE BOARD
# ─────────────────────────────────────────────

class Notice(db.Model):
    __tablename__ = "notices"

    notice_id   = Column(Integer,    primary_key=True, autoincrement=True)
    sender_id   = Column(Integer,    nullable=False)    # staff_id OR guard_id
    sender_type = Column(String(10), nullable=False)    # 'Staff' | 'Security'
    message     = Column(Text,       nullable=False)
    sent_at     = Column(DateTime,   nullable=False, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "sender_type IN ('Staff', 'Security')",
            name="chk_sender_type"
        ),
    )

    # Relationships (polymorphic)
    staff_sender = db.relationship(
        "Staff",
        primaryjoin="and_(Notice.sender_id == Staff.staff_id, "
                    "Notice.sender_type == 'Staff')",
        foreign_keys=[sender_id],
        overlaps="guard_sender",
    )
    guard_sender = db.relationship(
        "SecurityGuard",
        primaryjoin="and_(Notice.sender_id == SecurityGuard.guard_id, "
                    "Notice.sender_type == 'Security')",
        foreign_keys=[sender_id],
        overlaps="staff_sender",
    )

    def __repr__(self):
        return f"<Notice #{self.notice_id} from {self.sender_type} #{self.sender_id}>"


# ─────────────────────────────────────────────
#  DB INITIALISATION HELPERS
# ─────────────────────────────────────────────

def seed_lookup_tables(db_session) -> None:
    """Insert default Branch and Year records if they don't already exist."""
    # Branches
    default_branches = [
        Branch(branch_code="CO",   branch_name="Computer Engineering"),
        Branch(branch_code="IT",   branch_name="Information Technology"),
        Branch(branch_code="ENTC", branch_name="Electronics & Telecommunication"),
        Branch(branch_code="EJ",   branch_name="Electronics & Jewelry"),
        Branch(branch_code="DD",   branch_name="Diploma in Design"),
        Branch(branch_code="CE",   branch_name="Civil Engineering"),
    ]
    for branch in default_branches:
        if not db_session.get(Branch, branch.branch_code):
            db_session.add(branch)

    # Years
    default_years = [
        Year(year_code="FY", year_label="First Year"),
        Year(year_code="SY", year_label="Second Year"),
        Year(year_code="TY", year_label="Third Year"),
    ]
    for year in default_years:
        if not db_session.get(Year, year.year_code):
            db_session.add(year)

    db_session.commit()
