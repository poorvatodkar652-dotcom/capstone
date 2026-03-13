from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Student(db.Model):
    __tablename__ = 'students'

    enrollment = db.Column(db.String(50), primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    hostel_name = db.Column(db.String(100), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    branch = db.Column(db.String(10), nullable=False)
    year = db.Column(db.String(5), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    total_fees = db.Column(db.Float, nullable=False, default=0)
    paid_fees = db.Column(db.Float, nullable=False, default=0)
    remaining_fees = db.Column(db.Float, nullable=False, default=0)
    fees_status = db.Column(db.String(20), nullable=False, default='Due')

    requests = db.relationship('GatepassRequest', backref='student', lazy=True)

    def __repr__(self):
        return f'<Student {self.enrollment} - {self.student_name}>'


class Staff(db.Model):
    __tablename__ = 'staff'

    mobile_number = db.Column(db.String(15), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Warden / HOD
    branch = db.Column(db.String(10), nullable=False)
    year = db.Column(db.String(5), nullable=False)

    def __repr__(self):
        return f'<Staff {self.name} - {self.role}>'


class SecurityGuard(db.Model):
    __tablename__ = 'security_guards'

    mobile_number = db.Column(db.String(15), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return f'<SecurityGuard {self.name}>'


class GatepassRequest(db.Model):
    __tablename__ = 'gatepass_requests'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    enrollment = db.Column(db.String(50), db.ForeignKey('students.enrollment'), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    branch = db.Column(db.String(10), nullable=False)
    year = db.Column(db.String(5), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    out_date = db.Column(db.String(20), nullable=False)
    in_date = db.Column(db.String(20), nullable=False)
    place = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    qr_file = db.Column(db.String(255), default='')
    actual_out_date = db.Column(db.String(20), default='')
    actual_in_date = db.Column(db.String(20), default='')
    late_days = db.Column(db.Integer, default=0)
    fine = db.Column(db.Float, default=0)
    fine_status = db.Column(db.String(20), default='No Fine')
    reject_reason = db.Column(db.Text, default='')
    payment_mode = db.Column(db.String(20), default='')
    verified_by = db.Column(db.String(100), default='')
    request_datetime = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<GatepassRequest {self.id} - {self.enrollment}>'


class Notice(db.Model):
    __tablename__ = 'notices'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    datetime_posted = db.Column(db.String(20), nullable=False)
    sender_role = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Notice {self.id} - {self.sender_role}>'
