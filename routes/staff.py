import re
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, Staff, GatepassRequest, Notice

staff_bp = Blueprint('staff', __name__)

BRANCHES = ["CO", "IT", "ENTC", "EJ", "DD", "CE"]
YEARS = ["FY", "SY", "TY"]


# ===================== LOGIN =====================
@staff_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mobile = request.form.get('mobile', '').strip()
        password = request.form.get('password', '').strip()

        errors = []
        if not mobile:
            errors.append('Mobile number is required.')
        elif not re.match(r'^\d{10}$', mobile):
            errors.append('Mobile number must be exactly 10 digits.')
        if not password:
            errors.append('Password is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('staff/login_register.html', mode='login')

        try:
            staff = Staff.query.filter_by(
                mobile_number=mobile
            ).first()
        except Exception:
            db.session.rollback()
            flash('Something went wrong. Please try again.', 'error')
            return render_template('staff/login_register.html', mode='login')

        if not staff or not check_password_hash(staff.password, password):
            flash('Invalid mobile number or password.', 'error')
            return render_template('staff/login_register.html', mode='login')

        session.permanent = True
        session['staff_mobile'] = staff.mobile_number
        session['staff_name'] = staff.name
        session['staff_role'] = staff.role
        session['staff_branch'] = staff.branch
        session['staff_year'] = staff.year
        flash(f'Welcome, {staff.name} ({staff.role})!', 'success')
        return redirect(url_for('staff.dashboard'))

    return render_template('staff/login_register.html', mode='login')


# ===================== REGISTER =====================
@staff_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        dob = request.form.get('dob', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        role = request.form.get('role', '').strip()
        branch = request.form.get('branch', '').strip()
        year = request.form.get('year', '').strip()

        errors = []
        if not name:
            errors.append('Name is required.')
        elif len(name) < 2:
            errors.append('Name must be at least 2 characters.')
        if not mobile:
            errors.append('Mobile number is required.')
        elif not re.match(r'^\d{10}$', mobile):
            errors.append('Mobile number must be exactly 10 digits.')
        if not dob:
            errors.append('Date of Birth is required.')
        elif not re.match(r'^\d{4}-\d{2}-\d{2}$', dob):
            errors.append('DOB must be in YYYY-MM-DD format.')
        if not password:
            errors.append('Password is required.')
        elif len(password) < 4:
            errors.append('Password must be at least 4 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if not role:
            errors.append('Role is required.')
        if not branch:
            errors.append('Branch is required.')
        if not year:
            errors.append('Year is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('staff/login_register.html',
                                   branches=BRANCHES, years=YEARS, mode='register')

        try:
            existing = Staff.query.get(mobile)
            if existing:
                flash('This mobile number is already registered. Please use a different number or login.', 'error')
                return render_template('staff/login_register.html',
                                       branches=BRANCHES, years=YEARS, mode='register')

            new_staff = Staff(
                mobile_number=mobile,
                name=name,
                dob=dob,
                password=generate_password_hash(password),
                role=role,
                branch=branch,
                year=year
            )
            db.session.add(new_staff)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('Something went wrong during registration. Please try again.', 'error')
            return render_template('staff/login_register.html',
                                   branches=BRANCHES, years=YEARS, mode='register')

        flash('Staff registered successfully! You can now login.', 'success')
        return redirect(url_for('staff.login'))

    return render_template('staff/login_register.html',
                           branches=BRANCHES, years=YEARS, mode='register')


# ===================== DASHBOARD =====================
@staff_bp.route('/dashboard')
def dashboard():
    if 'staff_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('staff.login'))
    return render_template('staff/dashboard.html',
                           staff_name=session['staff_name'],
                           staff_role=session['staff_role'])


# ===================== VIEW / APPROVE REQUESTS (Warden) =====================
@staff_bp.route('/requests')
def view_requests():
    if 'staff_mobile' not in session or session.get('staff_role') != 'Warden':
        flash('Access denied.', 'error')
        return redirect(url_for('staff.login'))

    branch = session['staff_branch']
    year = session['staff_year']
    requests_list = GatepassRequest.query.filter_by(
        branch=branch, year=year
    ).order_by(GatepassRequest.id.desc()).all()

    return render_template('staff/view_requests.html', requests=requests_list)


@staff_bp.route('/approve/<int:req_id>', methods=['POST'])
def approve_request(req_id):
    if 'staff_mobile' not in session or session.get('staff_role') != 'Warden':
        flash('Access denied.', 'error')
        return redirect(url_for('staff.login'))

    gatepass = GatepassRequest.query.get(req_id)
    if not gatepass:
        flash('Request not found.', 'error')
        return redirect(url_for('staff.view_requests'))

    gatepass.status = 'Approved'
    db.session.commit()
    flash('Request approved successfully!', 'success')
    return redirect(url_for('staff.view_requests'))


@staff_bp.route('/reject/<int:req_id>', methods=['POST'])
def reject_request(req_id):
    if 'staff_mobile' not in session or session.get('staff_role') != 'Warden':
        flash('Access denied.', 'error')
        return redirect(url_for('staff.login'))

    gatepass = GatepassRequest.query.get(req_id)
    if not gatepass:
        flash('Request not found.', 'error')
        return redirect(url_for('staff.view_requests'))

    reject_reason = request.form.get('reject_reason', '').strip()
    gatepass.status = 'Rejected'
    gatepass.reject_reason = reject_reason
    db.session.commit()
    flash('Request rejected.', 'success')
    return redirect(url_for('staff.view_requests'))


# ===================== GATEPASS REGISTER (Warden) =====================
@staff_bp.route('/gatepass-register')
def gatepass_register():
    if 'staff_mobile' not in session or session.get('staff_role') != 'Warden':
        flash('Access denied.', 'error')
        return redirect(url_for('staff.login'))

    branch = session['staff_branch']
    year = session['staff_year']
    requests_list = GatepassRequest.query.filter_by(
        branch=branch, year=year
    ).order_by(GatepassRequest.id.desc()).all()

    return render_template('staff/gatepass_register.html', requests=requests_list)


# ===================== VIEW ALL STAFF (HOD) =====================
@staff_bp.route('/all-staff')
def view_all_staff():
    if 'staff_mobile' not in session or session.get('staff_role') != 'HOD':
        flash('Access denied.', 'error')
        return redirect(url_for('staff.login'))

    staff_list = Staff.query.all()
    return render_template('staff/view_staff.html', staff_list=staff_list)


# ===================== ALL BRANCH REQUESTS (HOD) =====================
@staff_bp.route('/all-requests')
def all_branch_requests():
    if 'staff_mobile' not in session or session.get('staff_role') != 'HOD':
        flash('Access denied.', 'error')
        return redirect(url_for('staff.login'))

    requests_list = GatepassRequest.query.order_by(GatepassRequest.id.desc()).all()
    return render_template('staff/all_branch_requests.html', requests=requests_list)


# ===================== SEND NOTICE =====================
@staff_bp.route('/send-notice', methods=['GET', 'POST'])
def send_notice():
    if 'staff_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('staff.login'))

    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        if not message:
            flash('Notice message is required.', 'error')
            return render_template('staff/send_notice.html')

        notice = Notice(
            datetime_posted=datetime.now().strftime('%Y-%m-%d %H:%M'),
            sender_role=f"Staff ({session['staff_role']})",
            message=message
        )
        db.session.add(notice)
        db.session.commit()
        flash('Notice sent successfully!', 'success')
        return redirect(url_for('staff.dashboard'))

    return render_template('staff/send_notice.html')


# ===================== VIEW NOTICES =====================
@staff_bp.route('/notices')
def view_notices():
    if 'staff_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('staff.login'))

    notices_list = Notice.query.order_by(Notice.id.desc()).all()
    return render_template('staff/notices.html', notices=notices_list)


# ===================== LOGOUT =====================
@staff_bp.route('/logout')
def logout():
    for key in ['staff_mobile', 'staff_name', 'staff_role', 'staff_branch', 'staff_year']:
        session.pop(key, None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home.index'))
