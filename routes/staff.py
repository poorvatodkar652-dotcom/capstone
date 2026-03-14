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
                mobile_no=mobile
            ).first()
        except Exception:
            db.session.rollback()
            flash('Something went wrong. Please try again.', 'error')
            return render_template('staff/login_register.html', mode='login')

        if not staff or not check_password_hash(staff.password_hash, password):
            flash('Invalid mobile number or password.', 'error')
            return render_template('staff/login_register.html', mode='login')

        session.permanent = True
        session['staff_id'] = staff.staff_id
        session['staff_mobile'] = staff.mobile_no
        session['staff_name'] = staff.full_name
        session['staff_role'] = staff.role
        session['staff_branch'] = staff.branch
        session['staff_year'] = staff.year
        flash(f'Welcome, {staff.full_name} ({staff.role})!', 'success')
        return redirect(url_for('staff.dashboard'))

    return render_template('staff/login_register.html', mode='login')


# ===================== REGISTER =====================
@staff_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
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
        if not email:
            errors.append('Email is required.')
        elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            errors.append('Invalid email format.')
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
            existing = Staff.query.filter_by(mobile_no=mobile).first()
            if existing:
                flash('This mobile number is already registered. Please use a different number or login.', 'error')
                return render_template('staff/login_register.html',
                                       branches=BRANCHES, years=YEARS, mode='register')

            new_staff = Staff(
                full_name=name,
                email=email,
                mobile_no=mobile,
                password_hash=generate_password_hash(password),
                role=role,
                branch=branch,
                year=year if role != 'HOD' else None
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
        
    staff_role = session['staff_role']
    metrics = {
        'total': 0,
        'approved': 0,
        'pending': 0,
        'rejected': 0
    }
    pending_requests = []
    
    if staff_role == 'Warden':
        branch = session['staff_branch']
        year = session['staff_year']
        from models import Student
        
        # Query requests for the warden's branch/year
        all_reqs = db.session.query(GatepassRequest).join(Student).filter(
            Student.branch == branch, Student.year == year
        ).all()
        
        metrics['total'] = len(all_reqs)
        for r in all_reqs:
            if r.status.lower() == 'approved':
                metrics['approved'] += 1
            elif r.status.lower() == 'pending':
                metrics['pending'] += 1
            elif r.status.lower() == 'rejected':
                metrics['rejected'] += 1
                
        # Fetch pending requests separately for the table (ordered by date)
        pending_requests = db.session.query(GatepassRequest).join(Student).filter(
            Student.branch == branch, Student.year == year, GatepassRequest.status == 'Pending'
        ).order_by(GatepassRequest.request_id.desc()).all()
        
    return render_template('staff/dashboard.html',
                           staff_name=session['staff_name'],
                           staff_role=staff_role,
                           metrics=metrics,
                           pending_requests=pending_requests)


# ===================== VIEW / APPROVE REQUESTS (Warden) =====================
@staff_bp.route('/requests')
def view_requests():
    if 'staff_id' not in session or session.get('staff_role') != 'Warden':
        flash('Access denied.', 'error')
        return redirect(url_for('staff.login'))

    branch = session['staff_branch']
    year = session['staff_year']
    
    # Needs a join since branch and year are not in GatepassRequest anymore
    from models import Student
    requests_list = db.session.query(GatepassRequest).join(Student).filter(
        Student.branch == branch, Student.year == year
    ).order_by(GatepassRequest.request_id.desc()).all()

    return render_template('staff/view_requests.html', requests=requests_list)


@staff_bp.route('/approve/<int:req_id>', methods=['POST'])
def approve_request(req_id):
    if 'staff_id' not in session or session.get('staff_role') != 'Warden':
        flash('Access denied.', 'error')
        return redirect(url_for('staff.login'))

    gatepass = GatepassRequest.query.get(req_id)
    if not gatepass:
        flash('Request not found.', 'error')
        return redirect(url_for('staff.view_requests'))

    gatepass.status = 'Approved'
    db.session.commit()

    # --- Email Notification to Student ---
    try:
        from utils.email import send_email
        if gatepass.student and gatepass.student.email:
            subject = "Gatepass Request Approved"
            body = f"""
            <h3>Gatepass Request Approved</h3>
            <p>Hello {gatepass.student.full_name},</p>
            <p>Your gatepass request to <strong>{gatepass.place}</strong> has been <strong>approved</strong>.</p>
            <p>You can now download your QR code from the portal.</p>
            """
            send_email(gatepass.student.email, subject, body)
    except Exception as e:
        print(f"Error sending email to Student: {e}")
    # ---------------------------------------

    flash('Request approved successfully!', 'success')
    return redirect(url_for('staff.view_requests'))


@staff_bp.route('/reject/<int:req_id>', methods=['POST'])
def reject_request(req_id):
    if 'staff_id' not in session or session.get('staff_role') != 'Warden':
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

    # --- Email Notification to Student ---
    try:
        from utils.email import send_email
        if gatepass.student and gatepass.student.email:
            subject = "Gatepass Request Rejected"
            body = f"""
            <h3>Gatepass Request Rejected</h3>
            <p>Hello {gatepass.student.full_name},</p>
            <p>Unfortunately, your gatepass request to <strong>{gatepass.place}</strong> has been <strong>rejected</strong>.</p>
            <p>Reason: {reject_reason if reject_reason else 'No reason provided.'}</p>
            """
            send_email(gatepass.student.email, subject, body)
    except Exception as e:
        print(f"Error sending email to Student: {e}")
    # ---------------------------------------

    flash('Request rejected.', 'success')
    return redirect(url_for('staff.view_requests'))


# ===================== GATEPASS REGISTER (Warden) =====================
@staff_bp.route('/gatepass-register')
def gatepass_register():
    if 'staff_id' not in session or session.get('staff_role') != 'Warden':
        flash('Access denied.', 'error')
        return redirect(url_for('staff.login'))

    branch = session['staff_branch']
    year = session['staff_year']
    
    from models import Student
    requests_list = db.session.query(GatepassRequest).join(Student).filter(
        Student.branch == branch, Student.year == year
    ).order_by(GatepassRequest.request_id.desc()).all()

    return render_template('staff/gatepass_register.html', requests=requests_list)


# ===================== VIEW ALL STAFF (HOD) =====================
@staff_bp.route('/all-staff')
def view_all_staff():
    if 'staff_id' not in session or session.get('staff_role') != 'HOD':
        flash('Access denied.', 'error')
        return redirect(url_for('staff.login'))

    staff_list = Staff.query.all()
    return render_template('staff/view_staff.html', staff_list=staff_list)


# ===================== ALL BRANCH REQUESTS (HOD) =====================
@staff_bp.route('/all-requests')
def all_branch_requests():
    if 'staff_id' not in session or session.get('staff_role') != 'HOD':
        flash('Access denied.', 'error')
        return redirect(url_for('staff.login'))

    requests_list = GatepassRequest.query.order_by(GatepassRequest.request_id.desc()).all()
    return render_template('staff/all_branch_requests.html', requests=requests_list)


# ===================== SEND NOTICE =====================
@staff_bp.route('/send-notice', methods=['GET', 'POST'])
def send_notice():
    if 'staff_id' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('staff.login'))

    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        if not message:
            flash('Notice message is required.', 'error')
            return render_template('staff/send_notice.html')

        notice = Notice(
            sender_id=session['staff_id'],
            sender_type='Staff',
            message=message,
            sent_at=datetime.utcnow()
        )
        db.session.add(notice)
        db.session.commit()
        
        # --- Email Notification to Students ---
        try:
            from models import Student
            from utils.email import send_email
            
            staff_role = session.get('staff_role')
            staff_name = session.get('staff_name')
            
            # User requested all notices go to ALL students
            target_students = Student.query.all()
                
            receivers = [s.email for s in target_students if s.email]
            if receivers:
                subject = f"New Notice from {staff_name} ({staff_role})"
                body = f"""
                <h3>New Hostel Notice</h3>
                <p><strong>From:</strong> {staff_name} ({staff_role})</p>
                <p><strong>Message:</strong></p>
                <blockquote style="border-left: 4px solid #ccc; padding-left: 10px; color: #555;">
                    {message}
                </blockquote>
                <br>
                <p>Please log in to your student portal for more details.</p>
                """
                # Send to all relevant students
                for email in receivers:
                    send_email(email, subject, body)
        except Exception as e:
            print(f"Error sending notice emails: {e}")
        # ----------------------------------------
        
        flash('Notice sent successfully!', 'success')
        return redirect(url_for('staff.dashboard'))

    return render_template('staff/send_notice.html')


# ===================== VIEW NOTICES =====================
@staff_bp.route('/notices')
def view_notices():
    if 'staff_id' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('staff.login'))

    notices_list = Notice.query.order_by(Notice.notice_id.desc()).all()
    return render_template('staff/notices.html', notices=notices_list)


# ===================== LOGOUT =====================
@staff_bp.route('/logout')
def logout():
    for key in ['staff_id', 'staff_mobile', 'staff_name', 'staff_role', 'staff_branch', 'staff_year']:
        session.pop(key, None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home.index'))
